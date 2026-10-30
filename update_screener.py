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

# Endpoint API công khai của TCBS
TCBS_PRICE_URL = "https://apipubaws.tcbs.com.vn/stock-insight/v1/stock/price-board?ticker={symbol}"
TCBS_RATIO_URL = "https://apipubaws.tcbs.com.vn/tcanalysis/v1/finance/ratio?ticker={symbol}"

def fetch_stock_data(symbol):
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
    close, pe, pb, roe, dividend_yield = 0, 0, 0, 0, 0

    # 1. Lấy giá từ TCBS Price Board
    try:
        r_price = requests.get(TCBS_PRICE_URL.format(symbol=symbol), headers=headers, timeout=8)
        if r_price.status_code == 200:
            data = r_price.json().get("data", [])
            if data:
                close = data[0].get("matchPrice", 0) or data[0].get("refPrice", 0)
    except Exception as e:
        print(f"⚠️ Lỗi lấy giá {symbol}: {e}")

    # 2. Lấy P/E, P/B, ROE từ TCBS Financial Ratio
    try:
        r_ratio = requests.get(TCBS_RATIO_URL.format(symbol=symbol), headers=headers, timeout=8)
        if r_ratio.status_code == 200:
            data = r_ratio.json().get("data", [])
            if data:
                ratio_data = data[0]
                pe = ratio_data.get("priceToEarning", 0) or 0
                pb = ratio_data.get("priceToBook", 0) or 0
                roe = ratio_data.get("roe", 0) or 0
                
                # Chuẩn hóa đơn vị ROE nếu trả về dạng thập phân (0.2 -> 20%)
                if 0 < roe < 1:
                    roe *= 100
    except Exception as e:
        print(f"⚠️ Lỗi lấy chỉ số tài chính {symbol}: {e}")

    return {
        "close": close,
        "pe": round(pe, 2),
        "pb": round(pb, 2),
        "roe": round(roe, 2),
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

    print("🚀 Bắt đầu quá trình cào thông số từ TCBS cho VN100...")
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
            "roa": prev.get("roa", 0),
            "eps": prev.get("eps", 0),
            "debtEquity": prev.get("debtEquity", 0),
            "dividendYield": live["dividendYield"] or prev.get("dividendYield", 0),
            "bctc": prev.get("bctc", "Đang chờ phân tích AI..."),
            "outlook": prev.get("outlook", "Đang cập nhật triển vọng..."),
            "recommendation": prev.get("recommendation", "CHỜ ĐỢI"),
            "price_zone": prev.get("price_zone", "Chưa có vùng giá"),
            "macro_view": prev.get("macro_view", "Chưa có vĩ mô")
        }
        time.sleep(0.3)

    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(new_data, f, ensure_ascii=False, indent=4)

    print("✅ Đã cập nhật thành công dữ liệu từ TCBS vào file data.json!")

if __name__ == "__main__":
    main()
