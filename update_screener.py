import json
import os
import requests
import datetime
import numpy as np

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

def fetch_vndirect_data(symbol):
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "application/json, text/plain, */*"
    }
    close_price, volume, pe, pb = 0, 0, 0, 0
    closes, volumes = [], []

    try:
        # 1. Lấy dữ liệu lịch sử giá & khối lượng từ VNDirect API
        end_date = datetime.datetime.now().strftime("%Y-%m-%d")
        start_date = (datetime.datetime.now() - datetime.timedelta(days=60)).strftime("%Y-%m-%d")
        
        url_hist = f"https://finfo-api.vndirect.com.vn/v4/stock_prices?sort=date&q=code:{symbol}~date:gte:{start_date}~date:lte:{end_date}&size=50"
        rHist = requests.get(url_hist, headers=headers, timeout=15)
        
        if rHist.status_code == 200:
            items = rHist.json().get("data", [])
            if items:
                closes = [float(i.get("close", 0) or 0) for i in items]
                volumes = [float(i.get("nmVolume", 0) or 0) for i in items]
                close_price = closes[-1] if closes else 0
                volume = volumes[-1] if volumes else 0

        # 2. Lấy chỉ số P/E, P/B từ VNDirect API
        url_ratio = f"https://finfo-api.vndirect.com.vn/v4/ratios?q=code:{symbol}"
        rRatio = requests.get(url_ratio, headers=headers, timeout=15)
        if rRatio.status_code == 200:
            rData = rRatio.json().get("data", [])
            if rData:
                latest_ratio = rData[-1]
                pe = float(latest_ratio.get("priceEarning", 0) or 0)
                pb = float(latest_ratio.get("priceBook", 0) or 0)

    except Exception as e:
        print(f"⚠️ Lỗi lấy dữ liệu mã {symbol}: {e}")

    # 3. Thuật toán Price Action D1
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
    print("🚀 Bắt đầu cập nhật dữ liệu VN100 & Volume từ VNDirect API...")
    stock_db = {}
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, "r", encoding="utf-8") as f:
                stock_db = json.load(f)
        except Exception:
            pass

    for symbol in VN100_SYMBOLS:
        print(f"Đang xử lý: {symbol}...")
        data = fetch_vndirect_data(symbol)
        if symbol not in stock_db:
            stock_db[symbol] = {}
        stock_db[symbol].update(data)

    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(stock_db, f, ensure_ascii=False, indent=4)
        
    print("✅ Đã cập nhật xong data.json với đầy đủ thông số!")

if __name__ == "__main__":
    main()
