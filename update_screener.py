import os
import json
import time
import requests

# ==================== CẤU HÌNH ====================
DATA_FILE = "data.json"

VND_DCHART_URL = "https://dchart-api.vndirect.com.vn/dchart/history"
VND_FUNDAMENTAL_URL = "https://api-finfo.vndirect.com.vn/v4/ratios"

RATIO_PE = "PRICE_TO_EARNINGS"
RATIO_PB = "PRICE_TO_BOOK"
RATIO_ROE = "ROAE_TR_AVG5Q"

# ==================== DANH SÁCH VN100 ====================
VN100_SYMBOLS = [
    "VCB", "BID", "CTG", "TCB", "MBB", "ACB", "STB", "VPB", "HDB", "VIB", "TPB", "SHB", "SSB", "LPB", "MSB", "OCB", "EIB",
    "SSI", "VCI", "HCM", "VIX", "MBS", "FTS", "BSI", "CTS", "ORS",
    "VHM", "VIC", "VRE", "NVL", "PDR", "DIG", "NLG", "KDH", "CEO", "DXG", "TCH", "SJS", "HDG", "KBC", "IDC", "SZC", "BCM", "PHR",
    "HPG", "HSG", "NKG", "VLB", "CTD", "HBC", "VCG", "HHV", "C4G",
    "FPT", "MWG", "PNJ", "FRT", "VNM", "MSN", "DGW", "SAB", "BHN", "KDC", "PET",
    "GAS", "POW", "BSR", "PVD", "PVS", "DGC", "DCM", "DPM", "GEG", "REE", "PC1", "NT2",
    "GMD", "HAH", "VJC", "HVN", "PVT", "VSC",
    "VHC", "ANV", "DAB", "PAN", "BAF"
]

INDUSTRY_MAP = {
    "VCB": "Ngân hàng", "BID": "Ngân hàng", "CTG": "Ngân hàng", "TCB": "Ngân hàng", "MBB": "Ngân hàng",
    "ACB": "Ngân hàng", "STB": "Ngân hàng", "VPB": "Ngân hàng", "HDB": "Ngân hàng", "VIB": "Ngân hàng",
    "TPB": "Ngân hàng", "SHB": "Ngân hàng", "SSB": "Ngân hàng", "LPB": "Ngân hàng", "MSB": "Ngân hàng",
    "OCB": "Ngân hàng", "EIB": "Ngân hàng", "SSI": "Chứng khoán", "VCI": "Chứng khoán", "HCM": "Chứng khoán",
    "VIX": "Chứng khoán", "MBS": "Chứng khoán", "FTS": "Chứng khoán", "BSI": "Chứng khoán", "CTS": "Chứng khoán", "ORS": "Chứng khoán",
    "VHM": "Bất động sản", "VIC": "Bất động sản", "VRE": "Bất động sản", "NVL": "Bất động sản",
    "PDR": "Bất động sản", "DIG": "Bất động sản", "NLG": "Bất động sản", "KDH": "Bất động sản",
    "CEO": "Bất động sản", "DXG": "Bất động sản", "TCH": "Bất động sản", "HDG": "Bất động sản",
    "KBC": "BĐS Khu công nghiệp", "IDC": "BĐS Khu công nghiệp", "SZC": "BĐS Khu công nghiệp",
    "BCM": "BĐS Khu công nghiệp", "PHR": "BĐS Khu công nghiệp", "HPG": "Thép & VLXD", "HSG": "Thép & VLXD",
    "NKG": "Thép & VLXD", "VLB": "Thép & VLXD", "CTD": "Xây dựng", "VCG": "Xây dựng", "HHV": "Xây dựng", "C4G": "Xây dựng",
    "FPT": "Công nghệ", "MWG": "Bán lẻ", "PNJ": "Bán lẻ", "FRT": "Bán lẻ", "DGW": "Bán lẻ",
    "VNM": "Tiêu dùng", "MSN": "Tiêu dùng", "SAB": "Tiêu dùng", "GAS": "Dầu khí", "PVD": "Dầu khí",
    "PVS": "Dầu khí", "BSR": "Dầu khí", "POW": "Năng lượng", "REE": "Năng lượng", "PC1": "Năng lượng",
    "NT2": "Năng lượng", "DGC": "Hóa chất", "DCM": "Phân bón", "DPM": "Phân bón",
    "GMD": "Cảng biển & Logistics", "HAH": "Cảng biển & Logistics", "PVT": "Vận tải biển",
    "VJC": "Hàng không", "HVN": "Hàng không", "VHC": "Thủy sản", "ANV": "Thủy sản", "DAB": "Nông nghiệp"
}


# ==================== HÀM ====================
def fetch_stock_price(symbol):
    now = int(time.time())
    params = {"resolution": "D", "symbol": symbol, "from": now - 365 * 86400, "to": now}
    try:
        r = requests.get(VND_DCHART_URL, params=params, timeout=10)
        r.raise_for_status()
        data = r.json()
        if data.get("s") == "ok" and data.get("c") and len(data["c"]) >= 20:
            return data["c"][-1]
    except requests.RequestException as e:
        print(f"  ⚠️ Lỗi giá {symbol}: {e}")
    except ValueError as e:
        print(f"  ⚠️ JSON lỗi giá {symbol}: {e}")
    return None


def fetch_single_ratio(symbol, ratio_code):
    params = {
        "q": f"code:{symbol}~ratioCode:{ratio_code}",
        "size": 1,
        "sort": "reportDate:desc"
    }
    try:
        r = requests.get(VND_FUNDAMENTAL_URL, params=params, timeout=10)
        r.raise_for_status()
        data = r.json()
        if data.get("data") and len(data["data"]) > 0:
            val = data["data"][0].get("value")
            return float(val) if val is not None else None
    except requests.RequestException as e:
        print(f"  ⚠️ Lỗi ratio {symbol}/{ratio_code}: {e}")
    except (ValueError, TypeError) as e:
        print(f"  ⚠️ Parse lỗi {symbol}/{ratio_code}: {e}")
    return None


def fetch_fundamentals(symbol):
    pe = fetch_single_ratio(symbol, RATIO_PE); time.sleep(0.15)
    pb = fetch_single_ratio(symbol, RATIO_PB); time.sleep(0.15)
    roe = fetch_single_ratio(symbol, RATIO_ROE); time.sleep(0.15)
    return {
        "pe": round(pe, 1) if pe is not None else None,
        "pb": round(pb, 1) if pb is not None else None,
        "roe": round(roe, 1) if roe is not None else None
    }


def load_existing_data():
    """Đọc data.json cũ để giữ nguyên bctc/outlook do workflow AI ghi."""
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError) as e:
            print(f"⚠️ Không đọc được data.json cũ: {e}")
    return {}


# ==================== MAIN ====================
def main():
    existing = load_existing_data()
    processed = {}
    symbols = sorted(set(VN100_SYMBOLS))
    total = len(symbols)

    print(f"🚀 Cập nhật giá + chỉ số cho {total} mã (KHÔNG gọi AI)...\n")

    for idx, symbol in enumerate(symbols, 1):
        industry = INDUSTRY_MAP.get(symbol, "Cổ phiếu VN100")
        print(f"[{idx}/{total}] {symbol} ({industry})")

        close_price = fetch_stock_price(symbol)
        fundamentals = fetch_fundamentals(symbol)
        print(f"  → Giá: {close_price}, P/E: {fundamentals['pe']}, P/B: {fundamentals['pb']}, ROE: {fundamentals['roe']}%")

        # Giữ nguyên bctc/outlook cũ (do workflow AI ghi) nếu có
        old = existing.get(symbol, {})
        processed[symbol] = {
            "symbol": symbol,
            "industry": industry,
            "close": close_price if close_price else 0,
            "pe": fundamentals["pe"],
            "pb": fundamentals["pb"],
            "roe": fundamentals["roe"],
            "bctc": old.get("bctc", ""),
            "outlook": old.get("outlook", ""),
            "ai_updated_at": old.get("ai_updated_at", None)
        }

        time.sleep(0.3)

    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(processed, f, ensure_ascii=False, indent=4)

    print(f"\n✅ Xong! Đã ghi {len(processed)} mã vào {DATA_FILE}")


if __name__ == "__main__":
    main()
