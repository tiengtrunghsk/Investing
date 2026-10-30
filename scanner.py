import json
import os
import requests
import datetime
import numpy as np

# Lấy thông tin từ GitHub Secrets
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")
DATA_FILE = "data.json"

# Danh sách mã VN100
VN100_SYMBOLS = [
    "ACB", "BID", "CTG", "TCB", "MBB", "STB", "VPB", "HDB", "VIB", "TPB",
    "SHB", "SSB", "LPB", "MSB", "OCB", "EIB", "SSI", "VCI", "HCM", "VIX",
    "MBS", "FTS", "BSI", "CTS", "ORS", "VHM", "VIC", "VRE", "NVL", "PDR",
    "DIG", "NLG", "KDH", "CEO", "DXG", "TCH", "HDG", "KBC", "IDC", "SZC",
    "BCM", "PHR", "HPG", "HSG", "NKG", "CTD", "VCG", "HHV", "FPT", "MWG",
    "PNJ", "FRT", "VNM", "MSN", "SAB", "GAS", "PVD", "PVS", "BSR", "POW",
    "REE", "PC1", "NT2", "GMD", "HAH", "PVT", "VJC", "HVN", "VHC", "ANV"
]

def fetch_historical_data_d1(symbol):
    """Lấy dữ liệu lịch sử D1 từ TCBS (giá và khối lượng 30 phiên gần nhất)"""
    end_time = int(datetime.datetime.now().timestamp())
    start_time = end_time - (45 * 86400)
    url = f"https://apipubaws.tcbs.com.vn/stock-insight/v1/stock/history-price?ticker={symbol}&from={start_time}&to={end_time}&resolution=D"
    
    headers = {"User-Agent": "Mozilla/5.0"}
    try:
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code == 200:
            data = response.json().get("data", [])
            if data and len(data) >= 20:
                closes = [item.get("close", 0) for item in data]
                volumes = [item.get("volume", 0) for item in data]
                return closes, volumes
    except Exception as e:
        print(f"⚠️ Lỗi lấy dữ liệu D1 mã {symbol}: {e}")
    return [], []

def evaluate_price_volume_signals(closes, volumes):
    """
    Thuật toán Price Action & Volume thuần túy (Khung D1):
    - Cạn cung (Tích lũy nền): Khối lượng hiện tại thấp hơn trung bình 20 phiên (< 0.7 * MA_Vol_20) và biên độ hẹp.
    - Sẵn sàng Breakout (Nổ Vol): Khối lượng bùng nổ (> 1.5 * MA_Vol_20) kèm giá tăng.
    """
    if len(closes) < 20 or len(volumes) < 20:
        return "ĐANG TÍCH LŨY NỀN", "Chưa đủ dữ liệu lịch sử"

    curr_close = closes[-1]
    prev_close = closes[-2]
    curr_vol = volumes[-1]
    
    ma_vol_20 = np.mean(volumes[-20:])
    vol_ratio = curr_vol / ma_vol_20 if ma_vol_20 > 0 else 1.0
    price_change_pct = ((curr_close - prev_close) / prev_close) * 100

    # 1. Tín hiệu Cạn cung (Tích lũy nền kiệt thanh khoản)
    if vol_ratio < 0.7 and abs(price_change_pct) < 1.5:
        return "ĐANG TÍCH LŨY NỀN", f"Vol cạn kiệt ({vol_ratio:.2f}x MA20), biên độ siết chặt."
    
    # 2. Tín hiệu Nổ Vol Breakout
    elif vol_ratio > 1.5 and price_change_pct > 1.5:
        return "SẴN SÀNG BREAKOUT", f"Vol bùng nổ ({vol_ratio:.2f}x MA20), giá tăng +{price_change_pct:.1f}%."
    
    # 3. Trạng thái tích lũy thông thường
    elif curr_close > np.mean(closes[-20:]):
        return "ĐANG TÍCH LŨY NỀN", f"Dòng tiền duy trì ổn định trên trung bình 20 phiên."
    else:
        return "CHỜ TEST LẠI", f"Vận động giằng co quanh hỗ trợ."

def send_telegram_alert(message):
    """Gửi báo cáo định dạng HTML về Telegram"""
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        print("❌ Chưa cấu hình Telegram Token hoặc Chat ID.")
        return False

    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message,
        "parse_mode": "HTML"
    }
    
    try:
        response = requests.post(url, json=payload, timeout=15)
        if response.status_code == 200:
            print("✅ Đã gửi báo cáo tín hiệu về Telegram thành công!")
            return True
        else:
            print(f"❌ Lỗi Telegram API: {response.text}")
    except Exception as e:
        print(f"❌ Ngoại lệ khi kết nối Telegram: {e}")
    return False

def main():
    print("🚀 Bắt đầu quét cấu trúc nền & dòng tiền D1 cho danh mục VN100...")
    
    stock_db = {}
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, "r", encoding="utf-8") as f:
                stock_db = json.load(f)
        except Exception:
            pass

    signals_report = []

    for symbol in VN100_SYMBOLS:
        closes, volumes = fetch_historical_data_d1(symbol)
        if not closes:
            continue
            
        status, detail = evaluate_price_volume_signals(closes, volumes)
        
        if symbol not in stock_db:
            stock_db[symbol] = {"symbol": symbol}
            
        stock_db[symbol]["recommendation"] = status
        stock_db[symbol]["price_zone"] = detail
        stock_db[symbol]["close"] = closes[-1]

        # Lọc các mã đạt trạng thái "BREAKOUT" hoặc "TÍCH LŨY" nổi bật để đưa vào bản tin Telegram
        if "BREAKOUT" in status or "CẠN CUNG" in status or "TÍCH LŨY" in status:
            signals_report.append({
                "symbol": symbol,
                "close": closes[-1],
                "status": status,
                "detail": detail
            })

    # Cập nhật file data.json
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(stock_db, f, ensure_ascii=False, indent=4)

    # Gửi bản tin Telegram
    if signals_report:
        msg = "📊 <b>[PRICE ACTION D1] BÁO CÁO TÍN HIỆU DÒNG TIỀN</b>\n"
        msg += "------------------------------------\n\n"
        for i, item in enumerate(signals_report[:8], 1):
            msg += f"<b>{i}. Mã {item['symbol']}</b>\n"
            msg += f"• Giá D1: <b>{item['close']:,.0f} VNĐ</b>\n"
            msg += f"• Trạng thái: <b>{item['status']}</b>\n"
            msg += f"• Cấu trúc: <i>{item['detail']}</i>\n\n"
        msg += f"⏰ <i>Thời gian quét: {datetime.datetime.now().strftime('%d/%m/%Y %H:%M:%S')}</i>"
        
        send_telegram_alert(msg)
    else:
        print("ℹ️ Không có mã nào đạt tiêu chí trong phiên này.")

if __name__ == "__main__":
    main()
