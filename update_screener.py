import json
import os
import datetime
import numpy as np

# Thư viện lotusmarket - cài đặt: pip install lotusmarket[fetchers]
from lotusmarket import fetchers

DATA_FILE = "data.json"

VN100_SYMBOLS = [
    "ACB", "BID", "CTG", "TCB", "MBB", "STB", "VPB", "HDB", "VIB", "TPB",
    "SHB", "SSB", "LPB", "MSB", "OCB", "EIB", "SSI", "VCI", "HCM", "VIX",
    "MBS", "FTS", "BSI", "CTS", "ORS", "VHM", "VIC", "VRE", "NVL", "PDR",
    "DIG", "NLG", "KDH", "CEO", "DXG", "TCH", "HDG", "KBC", "IDC", "SZC",
    "BCM", "PHR", "HPG", "HSG", "NKG", "CTD", "VCG", "HHV", "FPT", "MWG",
    "PNJ", "FRT", "VNM", "MSN", "SAB", "GAS", "PVD", "PVS", "BSR", "POW",
    "REE", "PC1", "NT2", "GMD", "HAH", "PVT", "VJC", "HVN", "VHC", "ANV"
]

def fetch_lotusmarket_data(symbol):
    close_price, volume, pe, pb = 0, 0, 0, 0
    closes, volumes = [], []

    try:
        # 1. Lấy lịch sử OHLCV từ Entrade (tối đa 1000 ngày, không cần key)
        history = fetchers.entrade_history(symbol, days=60)
        if history:
            closes = [float(h.close) for h in history if h.close is not None]
            volumes = [float(h.volume) for h in history if h.volume is not None]
            if closes:
                close_price = closes[-1]
            if volumes:
                volume = volumes[-1]

        # 2. Lấy chỉ số cơ bản P/E, P/B từ KBS (không cần key)
        fundamentals = fetchers.kbs(symbol)
        if fundamentals:
            pe = float(fundamentals.pe) if fundamentals.pe else 0
            pb = float(fundamentals.pb) if fundamentals.pb else 0

    except Exception as e:
        print(f"⚠️ Lỗi lấy dữ liệu mã {symbol}: {e}")

    # 3. Thuật toán Price Action D1 (giữ nguyên logic cũ)
    status = "ĐANG TÍCH LŨY NỀN"
    detail = "Đang siết nền tích lũy biên độ hẹp."

    if len(closes) >= 20 and len(volumes) >= 20:
        recent_vols = volumes[-20:]
        ma_vol_20 = np.mean(recent_vols)
        vol_ratio = volume / ma_vol_20 if ma_vol_20 > 0 else 1.0
        price_change_pct = ((closes[-1] - closes[-2]) / closes[-2]) * 100 if closes[-2] > 0 else 0

        if vol_ratio < 0.7 and abs(price_change_pct) < 1.5:
            status = "ĐANG TÍCH LŨY NỀN (CẠN CUNG)"
            detail = f"Khối lượng cạn kiệt ở mức {vol_ratio:.2f}x so với trung bình 20 phiên. Biên độ giá siết chặt."
        elif vol_ratio > 1.5 and price_change_pct > 1.5:
            status = "SẴN SÀNG BREAKOUT (NỔ VOL)"
            detail = f"Khối lượng bùng nổ đạt {vol_ratio:.2f}x MA20 kèm giá tăng +{price_change_pct:.1f}%."
        elif closes[-1] > np.mean(closes[-20:]):
            status = "ĐANG GOM HÀNG"
            detail = "Dòng tiền duy trì ổn định trên mức trung bình 20 phiên."

    return {
        "symbol": symbol,
        "close": close_price,
        "volume": volume,
        "pe": pe,
        "pb": pb,
        "recommendation": status,
        "price_zone": detail,
        "updated_at": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }

def main():
    print("🚀 Bắt đầu cập nhật dữ liệu VN100 qua lotusmarket...")
    stock_db = {}
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, "r", encoding="utf-8") as f:
                stock_db = json.load(f)
        except Exception:
            pass

    for symbol in VN100_SYMBOLS:
        print(f"Đang xử lý: {symbol}...")
        data = fetch_lotusmarket_data(symbol)
        if symbol not in stock_db:
            stock_db[symbol] = {}
        stock_db[symbol].update(data)

    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(stock_db, f, ensure_ascii=False, indent=4)

    print("✅ Đã cập nhật xong data.json với đầy đủ thông số!")

if __name__ == "__main__":
    main()
