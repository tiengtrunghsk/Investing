import json
import os
import datetime
import time
import numpy as np
import requests
from vnstock import Quote

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

# Danh sách tất cả các chỉ số cần lấy từ VNDirect
VNDIRECT_RATIOS = {
    "pe": "PRICE_TO_EARNINGS",
    "pb": "PRICE_TO_BOOK",
    "eps": "EPS_TR",
    "roe": "ROAE_TR_AVG5Q",
    "roa": "ROAA_TR_AVG5Q",
    "dividend_yield": "DIVIDEND_YIELD"
}

def get_vndirect_ratio(symbol, ratio_code):
    """Gọi API VNDirect để lấy một chỉ số cụ thể"""
    url = "https://api-finfo.vndirect.com.vn/v4/ratios"
    params = {
        "q": f"code:{symbol}~ratioCode:{ratio_code}",
        "size": 1,
        "sort": "reportDate:desc"
    }
    headers = {"User-Agent": "Mozilla/5.0"}
    try:
        r = requests.get(url, params=params, headers=headers, timeout=10)
        if r.status_code == 200:
            data = r.json().get("data", [])
            if data:
                return float(data[0].get("value", 0))
    except Exception as e:
        print(f"  ⚠️ Lỗi lấy {ratio_code} của {symbol}: {e}")
    return 0

def fetch_data(symbol):
    closes, volumes = [], []
    close_price, volume = 0, 0
    
    try:
        # 1. Lấy giá và khối lượng từ VCI (vnstock)
        end_date = datetime.datetime.now().strftime("%Y-%m-%d")
        start_date = (datetime.datetime.now() - datetime.timedelta(days=60)).strftime("%Y-%m-%d")
        quote = Quote(source='VCI', symbol=symbol)
        df = quote.history(start=start_date, end=end_date)
        
        if not df.empty:
            closes = df['close'].tolist()
            volumes = df['volume'].tolist()
            close_price = closes[-1]
            volume = volumes[-1]
            
        # 2. Lấy TẤT CẢ các chỉ số từ VNDirect
        ratios = {}
        for key, code in VNDIRECT_RATIOS.items():
            ratios[key] = get_vndirect_ratio(symbol, code)
            time.sleep(0.4) # Nghỉ giữa các request để tránh bị chặn
            
    except Exception as e:
        print(f"  ⚠️ Lỗi tổng hợp {symbol}: {e}")
        ratios = {k: 0 for k in VNDIRECT_RATIOS}

    # 3. Thuật toán Price Action
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
        "close": int(close_price * 1000),
        "volume": int(volume),
        "pe": round(ratios.get("pe", 0), 2),
        "pb": round(ratios.get("pb", 0), 2),
        "eps": int(ratios.get("eps", 0)),
        "roe": round(ratios.get("roe", 0) * 100, 1),  # Đổi sang %
        "roa": round(ratios.get("roa", 0) * 100, 1),  # Đổi sang %
        "dividend_yield": round(ratios.get("dividend_yield", 0) * 100, 2), # Đổi sang %
        "recommendation": status,
        "price_zone": detail,
        "updated_at": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }

def main():
    print("🚀 Bắt đầu cập nhật dữ liệu VN100 (Giá từ VCI, TẤT CẢ chỉ số từ VNDirect)...")
    
    API_KEY = os.getenv("VNSTOCK_API_KEY")
    if API_KEY:
        try:
            import vnstock
            vnstock.login(API_KEY)
            print("✅ Đăng nhập Vnstock thành công!")
        except Exception as e:
            print(f"⚠️ Lỗi đăng nhập Vnstock: {e}")

    stock_db = {}
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
            print(f"  ❌ Bỏ qua {symbol} do không có dữ liệu giá.")
            
        time.sleep(1.5) # Nghỉ lâu hơn vì gọi nhiều request

    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(stock_db, f, ensure_ascii=False, indent=4)
        
    print(f"\n✅ Đã cập nhật xong! File data.json chứa {len(stock_db)} mã.")

if __name__ == "__main__":
    main()
