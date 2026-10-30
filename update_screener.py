import os
import json
import time
import requests
from urllib.parse import quote

DATA_FILE = "data.json"
PROXY_PREFIX = "https://corsproxy.io/?url="
RAW_DCHART_URL = "https://dchart-api.vndirect.com.vn/dchart/history"
RAW_FUNDAMENTAL_URL = "https://api-finfo.vndirect.com.vn/v4/ratios"

# Danh sách mã VN100
VN100_SYMBOLS = [
    "ACB", "BID", "CTG", "TCB", "MBB", "ACB", "STB", "VPB", "HDB", "VIB",
    "TPB", "SHB", "SSB", "LPB", "MSB", "OCB", "EIB", "SSI", "VCI", "HCM",
    "VIX", "MBS", "FTS", "BSI", "CTS", "ORS", "VHM", "VIC", "VRE", "NVL",
    "PDR", "DIG", "NLG", "KDH", "CEO", "DXG", "TCH", "SJS", "HDG", "KBC",
    "IDC", "SZC", "BCM", "PHR", "HPG", "HSG", "NKG", "VLB", "CTD", "VCG",
    "HHV", "C4G", "FPT", "MWG", "PNJ", "FRT", "VNM", "MSN", "SAB", "GAS",
    "PVD", "PVS", "BSR", "POW", "REE", "PC1", "NT2", "DGC", "DCM", "DPM",
    "GMD", "HAH", "PVT", "VJC", "HVN", "VHC", "ANV", "DAB", "PAN", "BAF"
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

def fetch_via_proxy(url, params):
    req = requests.Request('GET', url, params=params).prepare()
    proxy_url = PROXY_PREFIX + quote(req.url, safe='')
    try:
        r = requests.get(proxy_url, headers={"User-Agent": "Mozilla/5.0"}, timeout=15)
        if r.status_code == 200:
            return r.json()
    except Exception:
        pass
    return None

def main():
    # Đọc dữ liệu cũ nếu có để giữ lại phần AI đã phân tích trước đó
    data = {}
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception:
            data = {}

    symbols = sorted(set(VN100_SYMBOLS))
    now = int(time.time())
    now_iso = time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime())

    print(f"🔄 Bắt đầu cập nhật dữ liệu giá & chỉ số cho {len(symbols)} mã từ API...")

    for symbol in symbols:
        industry = INDUSTRY_MAP.get(symbol, "VN100")
        
        # 1. Lấy giá (close)
        params_price = {"resolution": "D", "symbol": symbol, "from": now - 30 * 86400, "to": now}
        price_data = fetch_via_proxy(RAW_DCHART_URL, params_price)
        close = 0
        try:
            if price_data and price_data.get("s") == "ok" and price_data.get("c"):
                close = price_data["c"][-1]
        except Exception:
            pass

        # 2. Lấy P/E, P/B, ROE
        def get_ratio(code):
            params = {"q": f"code:{symbol}~ratioCode:{code}", "size": 1, "sort": "reportDate:desc"}
            res = fetch_via_proxy(RAW_FUNDAMENTAL_URL, params)
            try:
                if res and res.get("data") and len(res["data"]) > 0:
                    val = res["data"][0].get("value")
                    return float(val) if val is not None else 0.0
            except Exception:
                pass
            return 0.0

        pe = get_ratio("PRICE_TO_EARNINGS")
        pb = get_ratio("PRICE_TO_BOOK")
        roe = get_ratio("ROAE_TR_AVG5Q")
        if roe > 0 and roe < 1: 
            roe = roe * 100 # Đổi sang % nếu trả về dạng thập phân

        # Giữ lại các trường AI cũ nếu đã có, chỉ cập nhật giá và chỉ số mới
        existing_info = data.get(symbol, {})
        data[symbol] = {
            "symbol": symbol,
            "industry": industry,
            "close": close,
            "pe": round(pe, 2),
            "pb": round(pb, 2),
            "roe": round(roe, 2),
            "bctc": existing_info.get("bctc", "Đang chờ AI phân tích..."),
            "outlook": existing_info.get("outlook", "Đang chờ AI phân tích..."),
            "recommendation": existing_info.get("recommendation", "Chưa có"),
            "price_zone": existing_info.get("price_zone", "Chưa có"),
            "macro_view": existing_info.get("macro_view", "Chưa có"),
            "ai_updated_at": existing_info.get("ai_updated_at", None)
        }
        print(f"  ✔ {symbol} -> Giá: {close}, P/E: {pe}, P/B: {pb}, ROE: {roe}%")
        time.sleep(1)

    # Ghi đè file data.json
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)
        
    print(f"\n✨ Đã cập nhật xong dữ liệu vào {DATA_FILE} lúc {now_iso}!")

if __name__ == "__main__":
    main()
