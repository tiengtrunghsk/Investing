import json
import os
import datetime
import time
import numpy as np
from vnstock import Quote
import vnstock

# Tên file output
DATA_FILE = "data.json"

# Danh sách 70 mã VN100
VN100_SYMBOLS = [
    "ACB", "BID", "CTG", "TCB", "MBB", "STB", "VPB", "HDB", "VIB", "TPB",
    "SHB", "SSB", "LPB", "MSB", "OCB", "EIB", "SSI", "VCI", "HCM", "VIX",
    "MBS", "FTS", "BSI", "CTS", "ORS", "VHM", "VIC", "VRE", "NVL", "PDR",
    "DIG", "NLG", "KDH", "CEO", "DXG", "TCH", "HDG", "KBC", "IDC", "SZC",
    "BCM", "PHR", "HPG", "HSG", "NKG", "CTD", "VCG", "HHV", "FPT", "MWG",
    "PNJ", "FRT", "VNM", "MSN", "SAB", "GAS", "PVD", "PVS", "BSR", "POW",
    "REE", "PC1", "NT2", "GMD", "HAH", "PVT", "VJC", "HVN", "VHC", "ANV"
]

def fetch_data(symbol):
    closes, volumes = [], []
    close_price, volume = 0, 0
    
    try:
        # Lấy dữ liệu 60 ngày gần nhất từ nguồn VCI
        end_date = datetime.datetime.now().strftime("%Y-%m-%d")
        start_date = (datetime.datetime.now() - datetime.timedelta(days=60)).strftime("%Y-%m-%d")
        
        quote = Quote(source='VCI', symbol=symbol)
        df = quote.history(start=start_date, end=end_date)
        
        if not df.empty:
            closes = df['close'].tolist()
            volumes = df['volume'].tolist()
            close_price = closes[-1]
            volume = volumes[-1]
            
    except Exception as e:
        print(f"  ⚠️ Lỗi lấy dữ liệu {symbol}: {e}")

    # Thuật toán Price Action D1
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
        "close": int(close_price * 1000),  # Đổi sang VNĐ và bỏ thập phân
        "volume": int(volume),             # Khối lượng luôn là số nguyên
        "pe": 0,
        "pb": 0,
        "recommendation": status,
        "price_zone": detail,
        "updated_at": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }

def main():
    print("🚀 Bắt đầu cập nhật dữ liệu VN100 qua Vnstock (VCI)...")
    
    # Đăng nhập tự động bằng biến môi trường
    API_KEY = os.getenv("VNSTOCK_API_KEY")
    if API_KEY:
        try:
            print("🔑 Đang đăng nhập Vnstock...")
            vnstock.login(API_KEY)
            print("✅ Đăng nhập thành công!")
        except Exception as e:
            print(f"⚠️ Lỗi đăng nhập Vnstock: {e}")
            # Thử logout thiết bị cũ nếu bị giới hạn
            try:
                vnstock.logout()
                vnstock.login(API_KEY)
                print("✅ Đã xoay vòng thiết bị và đăng nhập lại thành công!")
            except Exception as ex:
                print(f"❌ Vẫn lỗi sau khi xoay vòng: {ex}")
    else:
        print("⚠️ Không tìm thấy VNSTOCK_API_KEY trong môi trường.")

    stock_db = {}
    
    # Đọc dữ liệu cũ nếu có
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, "r", encoding="utf-8") as f:
                stock_db = json.load(f)
        except Exception:
            pass

    total = len(VN100_SYMBOLS)
    for i, symbol in enumerate(VN100_SYMBOLS):
        print(f"[{i+1}/{total}] Đang xử lý: {symbol}...")
        
        data = fetch_data(symbol)
        
        if data.get("close", 0) > 0:
            stock_db[symbol] = data
        else:
            print(f"  ❌ Bỏ qua {symbol} do không có dữ liệu.")
            
        # Nghỉ 1.2s để tránh rate limit
        time.sleep(1.2)

    # Ghi ra file data.json
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(stock_db, f, ensure_ascii=False, indent=4)
        
    print(f"\n✅ Đã cập nhật xong! File data.json chứa {len(stock_db)} mã.")

if __name__ == "__main__":
    main()
