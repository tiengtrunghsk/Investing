import os
import time
import datetime
import json
import subprocess
import requests

DATA_FILE = "data.json"

def update_realtime_prices():
    if not os.path.exists(DATA_FILE):
        print("❌ Không tìm thấy file data.json!")
        return

    with open(DATA_FILE, "r", encoding="utf-8") as f:
        stock_db = json.load(f)

    print(f"\n⚡ [Realtime] Bắt đầu quét giá mới nhất cho {len(stock_db)} mã lúc {datetime.datetime.now().strftime('%H:%M:%S')}...")
    
    updated_count = 0
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}

    for symbol, data in stock_db.items():
        if data.get('close', 0) <= 0:
            continue
        try:
            # Gọi trực tiếp API công khai của TCBS lấy dữ liệu giá biểu đồ theo ngày (resolution=D)
            url = f"https://apipubaws.tcbs.com.vn/stock-insight/v1/stock/s-chart?ticker={symbol}&resolution=D&from=0&to=9999999999"
            r = requests.get(url, headers=headers, timeout=5)
            if r.status_code == 200:
                json_data = r.json()
                if 'data' in json_data and json_data['data']:
                    latest = json_data['data'][-1]
                    data['close'] = float(latest.get('close', data['close']))
                    data['volume'] = int(latest.get('volume', data['volume']))
                    data['updated_at'] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    updated_count += 1
        except Exception:
            pass
        time.sleep(0.1) # Nghỉ cực ngắn giữa các mã để quét siêu tốc và an toàn

    # Ghi đè lại file data.json
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(stock_db, f, ensure_ascii=False, indent=4)
        
    print(f"✅ Đã cập nhật xong giá cho {updated_count} mã vào data.json.")
    
    # Tự động đẩy (push) lên GitHub để trang web ngoài GitHub Pages nhận giá mới
    git_commit_and_push()

def git_commit_and_push():
    try:
        subprocess.run(["git", "add", "data.json"], check=True)
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
                print("💤 Đang trong giờ giao dịch. Chờ 30 phút để quét nhịp tiếp theo...")
                time.sleep(1800) # Chờ 30 phút
            else:
                print(f"🌙 Ngoài giờ giao dịch ({datetime.datetime.now().strftime('%H:%M %d-%m-%Y')}). Tạm nghỉ và kiểm tra lại sau 5 phút...")
                time.sleep(300) # Ngoài giờ thì kiểm tra thưa hơn (5 phút/lần)
        except Exception as e:
            print(f"⚠️ Lỗi vòng lặp chính: {e}")
            time.sleep(60)
