import os
import json
import time
from vnstock import stock_historical_data

DATA_FILE = "data.json"

VN100_SYMBOLS = [
    "ACB", "BID", "CTG", "TCB", "MBB", "STB", "VPB", "HDB", "VIB", "TPB", 
    "SHB", "SSB", "LPB", "MSB", "OCB", "EIB", "SSI", "VCI", "HCM", "VIX", 
    "MBS", "FTS", "BSI", "CTS", "ORS", "VHM", "VIC", "VRE", "NVL", "PDR", 
    "DIG", "NLG", "KDH", "CEO", "DXG", "TCH", "SJS", "HDG", "KBC", "IDC", 
    "SZC", "BCM", "PHR", "HPG", "HSG", "NKG", "VLB", "CTD", "VCG", "HHV", 
    "C4G", "FPT", "MWG", "PNJ", "FRT", "VNM", "MSN", "SAB", "GAS", "PVD", 
    "PVS", "BSR", "POW", "REE", "PC1", "NT2", "DGC", "DCM", "DPM", "GMD", 
    "HAH", "PVT", "VJC", "HVN", "VHC", "ANV", "PAN", "BAF"
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

def main():
    # Đọc dữ liệu cũ để giữ lại phần AI đã phân tích trước đó
    data = {}
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception:
            data = {}

    symbols = sorted(set(VN100_SYMBOLS))
    now_iso = time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime())

    print(f"🔄 Bắt đầu lấy dữ liệu giá qua vnstock cho {len(symbols)} mã...")

    for symbol in symbols:
        industry = INDUSTRY_MAP.get(symbol, "VN100")
        close = 0

        try:
            # Lấy giá đóng cửa gần nhất bằng vnstock
            df = stock_historical_data(symbol=symbol, start_date="2026-01-01", end_date="", resolution="1D", type="stock")
            if df is not None and not df.empty:
                close = float(df.iloc[-1]["close"])
        except Exception as e:
            print(f"  ⚠️ Lỗi lấy giá {symbol}: {e}")

        # Giữ lại các chỉ số và nhận xét AI cũ, chỉ cập nhật giá mới
        existing_info = data.get(symbol, {})
        data[symbol] = {
            "symbol": symbol,
            "industry": industry,
            "close": close,
            "pe": existing_info.get("pe", 0),
            "pb": existing_info.get("pb", 0),
            "roe": existing_info.get("roe", 0),
            "bctc": existing_info.get("bctc", "Đang chờ AI phân tích..."),
            "outlook": existing_info.get("outlook", "Đang chờ AI phân tích..."),
            "recommendation": existing_info.get("recommendation", "Chưa có"),
            "price_zone": existing_info.get("price_zone", "Chưa có"),
            "macro_view": existing_info.get("macro_view", "Chưa có"),
            "ai_updated_at": existing_info.get("ai_updated_at", None)
        }
        print(f"  ✔ {symbol} -> Giá: {close}")
        time.sleep(0.3)

    # Ghi đè file data.json để website hiển thị
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)
        
    print(f"\n✨ Đã cập nhật xong dữ liệu vào {DATA_FILE} lúc {now_iso}!")

if __name__ == "__main__":
    main()
