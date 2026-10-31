import os
import time
import datetime
import json
import subprocess
from vnstock3 import Vnstock

DATA_FILE = "data.json"

def update_realtime_prices():
    if not os.path.exists(DATA_FILE):
        print("❌ Không tìm thấy file data.json!")
        return

    with open(DATA_FILE, "r", encoding="utf-8") as f:
        stock_db = json.load(f)

    print(f"\n⚡ [Realtime] Bắt đầu quét giá mới nhất cho {len(stock_db)} mã cổ phiếu lúc {datetime.datetime.now().strftime('%H:%M:%S')}...")
    
    updated_count = 0
    for symbol, data in stock_db.items():
        if data.get('close', 0) <= 0:
            continue
        try:
            # Lấy dữ liệu giá mới nhất từ TCBS qua vnstock3
            stock = Vnstock().stock(symbol=symbol, source='TCBS')
            today_str = datetime.date.today().strftime('%Y-%m-%d')
            df = stock.quote.history(start='2026-10-01', end=today_str, interval='1D')
            
            if df is not None and not df.empty:
                latest_row = df.iloc[-1]
                new_close = float(latest_row['close'])
                new_volume = int(latest_row['volume'])
                
                # Cập nhật giá, khối lượng và thời gian
                data['close'] = new_close
                data['volume'] = new_volume
                data['updated_at'] = time.strftime("%Y-%m-%d %H:%M:%S")
                updated_count += 1
        except Exception as e:
            # Bỏ qua lỗi kết nối tạm thời ở một mã bất kỳ
            pass
        
        time.sleep(0.2) # Nghỉ ngắn giữa các mã tránh bị chặn

    # Ghi đè lại file data.json
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(stock_db, f, ensure_ascii=False, indent=4)
        
    print(f"✅ Đã cập nhật xong giá cho {updated_count} mã vào data.json.")
    
    # Tự động đẩy (push) lên GitHub để trang web ngoài GitHub Pages nhận giá mới
    git_commit_and_push()

def git_commit_and_push():
    try:
        subprocess.run(["git", "add", "data.json"], check=True)
        # Commit với mốc thời gian tự động
        commit_msg = f"Auto-update realtime stock data at {datetime.datetime.now().strftime('%H:%M %d-%m-%Y')}"
        subprocess.run(["git", "commit", "-m", commit_msg], check=True)
        subprocess.run(["git", "push", "origin", "main"], check=True)
        print("🚀 Đã tự động đồng bộ (push) dữ liệu mới lên GitHub Pages thành công!\n")
    except Exception as e:
        print(f"ℹ️ Không có thay đổi mới để push hoặc lỗi git: {e}\n")

def is_trading_time():
    """Kiểm tra xem có đang trong giờ giao dịch chứng khoán không (Thứ 2 - Thứ 6, từ 9:00 đến 15:00)"""
    now = datetime.datetime.now()
    weekday = now.weekday() # 0-4 là Thứ 2 đến Thứ 6
    hour = now.hour
    minute = now.minute
    
    if weekday >= 5: # Cuối tuần (Thứ 7, Chủ Nhật)
        return False
        
    current_time_val = hour * 60 + minute
    start_market = 9 * 60       # 09:00
    end_market = 15 * 60        # 15:00
    
    return start_market <= current_time_val <= end_market

if __name__ == "__main__":
    print("🤖 Hệ thống tự động cập nhật giá Realtime (30 phút/lần) đã khởi động!")
    
    while True:
        try:
            if is_trading_time():
                update_realtime_prices()
                # Chờ đúng 30 phút (1800 giây) cho chu kỳ tiếp theo trong giờ giao dịch
                print("💤 Đang trong giờ giao dịch. Chờ 30 phút để quét nhịp tiếp theo...")
                time.sleep(1800)
            else:
                print(f"🌙 Ngoài giờ giao dịch ({datetime.datetime.now().strftime('%H:%M %d-%m-%Y')}). Tạm nghỉ và kiểm tra lại sau 5 phút...")
                time.sleep(300) # Ngoài giờ thì kiểm tra thưa hơn (5 phút/lần) để chờ đến giờ mở cửa
        except Exception as e:
            print(f"⚠️ Lỗi vòng lặp chính: {e}")
            time.sleep(60)
