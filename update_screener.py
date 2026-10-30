import json
import os
import time
import requests

DATA_FILE = "data.json"

VN100_SYMBOLS = [
    "ACB", "BID", "CTG", "TCB", "MBB", "STB", "VPB", "HDB", "VIB", "TPB", 
    "SHB", "SSB", "LPB", "MSB", "OCB", "EIB", "SSI", "VCI", "HCM", "VIX", 
    "MBS", "FTS", "BSI", "CTS", "ORS", "VHM", "VIC", "VRE", "NVL", "PDR", 
    "DIG", "NLG", "KDH", "CEO", "DXG", "TCH", "SJS", "HDG", "KBC", "IDC", 
    "SZC", "BCM", "PHR", "HPG", "HSG", "NKG", "VLB", "CTD", "VCG", "HHV", 
    "C4G", "FPT", "MWG", "PNJ", "FRT", "VNM", "MSN", "SAB", "GAS", "PVD", 
    "PVS", "BSR", "POW", "REE", "PC1", "NT2", "GMD", "HAH", "PVT", "VJC", 
    "HVN", "VHC", "ANV", "PAN", "BAF"
]

INDUSTRY_MAP = {
    "VCB": "Ngân hàng", "BID": "Ngân hàng", "CTG": "Ngân hàng", "TCB": "Ngân hàng", "MBB": "Ngân hàng",
    "ACB": "Ngân hàng", "STB": "Ngân hàng", "VPB": "Ngân hàng", "HDB": "Ngân hàng", "VIB": "Ngân hàng",
    "TPB": "Ngân hàng", "SHB": "Ngân hàng", "SSB": "Ngân hàng", "LPB": "Ngân hàng", "MSB": "Ngân hàng",
    "OCB": "Ngân hàng", "EIB": "Ngân hàng", "SSI": "Chứng khoán", "VCI": "Chứng khoán", "HCM": "Chứng khoán",
    "VIX": "Chứng khoán", "MBS": "Chứng khoán", "FTS": "Chứng khoán", "BSI": "Chứng khoán", "CTS": "Chứng khoán",
    "VHM": "Bất động sản", "VIC": "Bất động sản", "VRE": "Bất động sản", "NVL": "Bất động sản", "PDR": "Bất động sản",
    "DIG": "Bất động sản", "NLG": "Bất động sản", "KDH": "Bất động sản", "DXG": "Bất động sản", "HPG": "Thép & VLXD",
    "HSG": "Thép & VLXD", "NKG": "Thép & VLXD", "FPT": "Công nghệ", "MWG": "Bán lẻ", "PNJ": "Bán lẻ",
    "FRT": "Bán lẻ", "VNM": "Tiêu dùng", "MSN": "Tiêu dùng", "GAS": "Dầu khí", "PVD": "Dầu khí",
    "POW": "Năng lượng", "DGC": "Hóa chất", "DCM": "Phân bón", "DPM": "Phân bón", "GMD": "Cảng biển & Logistics"
}

def fetch_stock_data(symbol):
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    close, pe, pb, roe, roa, eps, debt_equity, dividend_yield = 0, 0, 0, 0, 0, 0, 0, 0

    # 1. Lấy giá đóng cửa thực tế từ DChart API
    try:
        end = int(time.time())
        start = end - (10 * 86400)
        url_price = f"https://dchart-api.vndirect.com.vn/dchart/history?resolution=D&symbol={symbol}&from={start}&to={end}"
        res = requests.get(url_price, headers=headers, timeout=8).json()
        if res.get("s") == "ok" and res.get("c"):
            close = res["c"][-1]
    except Exception as e:
        print(f"Lỗi giá {symbol}: {e}")

    # 2. Lấy trọn bộ chỉ số PTCB bằng cách truy vấn trực tiếp các mã chỉ số cốt lõi
    try:
        ratio_codes = "PRICE_TO_EARNINGS,PRICE_TO_BOOK,ROE,ROAE,ROA,ROAA,EPS,DEBT_TO_EQUITY,DIVIDEND_YIELD"
        url_ratio = f"https://api-finfo.vndirect.com.vn/v4/ratios?q=code:{symbol}~ratioCode:{ratio_codes}&size=20&sort=reportDate:desc"
        res = requests.get(url_ratio, headers=headers, timeout=8).json()
        if res.get("data"):
            for item in res["data"]:
                code = str(item.get("ratioCode", "")).upper()
                val_raw = item.get("value")
                if val_raw is None:
                    continue
                
                try:
                    val = float(val_raw)
                except ValueError:
                    continue

                if val == 0:
                    continue

                if ("PRICE_TO_EARNINGS" in code or code == "PE") and pe == 0:
                    pe = val
                elif ("PRICE_TO_BOOK" in code or code == "PB") and pb == 0:
                    pb = val
                elif ("ROE" in code or "ROAE" in code) and roe == 0:
                    roe = val * 100 if 0 < val < 1 else val
                elif ("ROA" in code or "ROAA" in code) and roa == 0:
                    roa = val * 100 if 0 < val < 1 else val
                elif code == "EPS" and eps == 0:
                    eps = val
                elif ("DEBT" in code or "LIABILITIES" in code) and debt_equity == 0:
                    debt_equity = val
                elif "DIVIDEND" in code and dividend_yield == 0:
                    dividend_yield = val * 100 if 0 < val < 1 else val
    except Exception as e:
        print(f"Lỗi chỉ số {symbol}: {e}")

    # 3. Fallback dự phòng qua financial_models nếu ROE/ROA/EPS vẫn trống
    if roe == 0 or roa == 0 or eps == 0:
        try:
            url_fb = f"https://api-finfo.vndirect.com.vn/v4/financial_models?q=code:{symbol}~reportType:QUARTER&size=15&sort=reportDate:desc"
            res_fb = requests.get(url_fb, headers=headers, timeout=8).json()
            if res_fb.get("data"):
                for item in res_fb["data"]:
                    m_code = str(item.get("modelCode", "")).upper()
                    val_raw = item.get("value")
                    if val_raw is None:
                        continue
                    val = float(val_raw)
                    if ("ROE" in m_code or "ROAE" in m_code) and roe == 0:
                        roe = val * 100 if 0 < val < 1 else val
                    if ("ROA" in m_code or "ROAA" in m_code) and roa == 0:
                        roa = val * 100 if 0 < val < 1 else val
                    if "EPS" in m_code and eps == 0:
                        eps = val
        except Exception:
            pass

    return {
        "close": close,
        "pe": round(pe, 2),
        "pb": round(pb, 2),
        "roe": round(roe, 2),
        "roa": round(roa, 2),
        "eps": round(eps, 2),
        "debtEquity": round(debt_equity, 2),
        "dividendYield": round(dividend_yield, 2)
    }

def main():
    old_data = {}
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, "r", encoding="utf-8") as f:
                old_data = json.load(f)
        except Exception:
            pass

    print("🚀 Bắt đầu quá trình cào thông số PTCB cho VN100...")
    new_data = {}

    for symbol in VN100_SYMBOLS:
        print(f"Đang xử lý: {symbol}...")
        live = fetch_stock_data(symbol)
        prev = old_data.get(symbol, {})

        new_data[symbol] = {
            "symbol": symbol,
            "industry": INDUSTRY_MAP.get(symbol, prev.get("industry", "VN100")),
            "close": live["close"] or prev.get("close", 0),
            "pe": live["pe"] or prev.get("pe", 0),
            "pb": live["pb"] or prev.get("pb", 0),
            "roe": live["roe"] or prev.get("roe", 0),
            "roa": live["roa"] or prev.get("roa", 0),
            "eps": live["eps"] or prev.get("eps", 0),
            "debtEquity": live["debtEquity"] or prev.get("debtEquity", 0),
            "dividendYield": live["dividendYield"] or prev.get("dividendYield", 0),
            "bctc": prev.get("bctc", "Đang chờ phân tích AI..."),
            "outlook": prev.get("outlook", "Đang cập nhật triển vọng..."),
            "recommendation": prev.get("recommendation", "CHỜ ĐỢI"),
            "price_zone": prev.get("price_zone", "Chưa có vùng giá"),
            "macro_view": prev.get("macro_view", "Chưa có vĩ mô")
        }
        time.sleep(0.15)

    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(new_data, f, ensure_ascii=False, indent=4)

    print("✅ Đã cập nhật thành công trọn bộ thông số vào file data.json!")

if __name__ == "__main__":
    main()
