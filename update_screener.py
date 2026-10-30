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
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
    close, pe, pb, roe, roa, eps, debt_equity, dividend_yield = 0, 0, 0, 0, 0, 0, 0, 0

    # 1. Lấy giá đóng cửa thực tế từ DChart API
    try:
        end = int(time.time())
        start = end - (10 * 86400)
        url_price = f"https://dchart-api.vndirect.com.vn/dchart/history?resolution=D&symbol={symbol}&from={start}&to={end}"
        res = requests.get(url_price, headers=headers, timeout=5).json()
        if res.get("s") == "ok" and res.get("c"):
            close = res["c"][-1]
    except Exception as e:
        print(f"Lỗi giá {symbol}: {e}")

    # 2. Lấy trọn bộ chỉ số PTCB từ Finfo API
    try:
        url_ratio = f"https://api-finfo.vndirect.com.vn/v4/ratios?q=code:{symbol}&size=50&sort=reportDate:desc"
        res = requests.get(url_ratio, headers=headers, timeout=5).json()
        if res.get("data"):
            for item in res["data"]:
                code = str(item.get("ratioCode", "")).upper()
                val = float(item.value or 0)
                if val == 0:
                    continue

                if code == "PRICE_TO_EARNINGS" and pe == 0: pe = val
                if code == "PRICE_TO_BOOK" and pb == 0: pb = val
                if ("ROE" in code or "ROAE" in code) and roe == 0:
                    roe = val * 100 if 0 < val < 1 else val
                if ("ROA" in code or "ROAA" in code) and roa == 0:
                    roa = val * 100 if 0 < val < 1 else val
                if code == "EPS" and eps == 0: eps = val
                if ("DEBT" in code or "DEBT_TO_EQUITY" in code) and debt_equity == 0: debt_equity = val
                if ("DIVIDEND" in code or "DIVIDEND_YIELD" in code) and dividend_yield == 0:
                    dividend_yield = val * 100 if 0 < val < 1 else val
    except Exception as e:
        print(f"Lỗi chỉ số {symbol}: {e}")

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
    # Đọc file data.json cũ để giữ lại phần phân tích AI
    old_data = {}
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, "r", encoding="utf-8") as f:
                old_data = json.load(f)
        except:
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
        time.sleep(0.2) # Nghỉ ngắn giữa các request để tránh bị nghẽn

    # Ghi đè vào data.json
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(new_data, f, ensure_ascii=False, indent=4)

    print("✅ Đã cập nhật thành công trọn bộ thông số vào file data.json!")

if __name__ == "__main__":
    main()
