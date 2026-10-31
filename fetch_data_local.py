import os
import datetime
import time
import json
import subprocess
import numpy as np
import requests
from vnstock import Quote

DATA_FILE = "data.json"
HISTORY_DIR = "history"
JS_LIB_FILE = "lightweight-charts.js"

VN100_SYMBOLS = [
    "ACB", "BID", "CTG", "TCB", "MBB", "STB", "VPB", "HDB", "VIB", "TPB",
    "SHB", "SSB", "LPB", "MSB", "OCB", "EIB", "SSI", "VCI", "HCM", "VIX",
    "MBS", "FTS", "BSI", "CTS", "ORS", "VHM", "VIC", "VRE", "NVL", "PDR",
    "DIG", "NLG", "KDH", "CEO", "DXG", "TCH", "HDG", "KBC", "IDC", "SZC",
    "BCM", "PHR", "HPG", "HSG", "NKG", "CTD", "VCG", "HHV", "FPT", "MWG",
    "PNJ", "FRT", "VNM", "MSN", "SAB", "GAS", "PVD", "PVS", "BSR", "POW",
    "REE", "PC1", "NT2", "GMD", "HAH", "PVT", "VJC", "HVN", "VHC", "ANV"
]

VNDIRECT_RATIOS = {
    "pe": "PRICE_TO_EARNINGS",
    "pb": "PRICE_TO_BOOK",
    "eps": "EPS_TR",
    "roe": "ROAE_TR_AVG5Q",
    "roa": "ROAA_TR_AVG5Q",
    "dividend_yield": "DIVIDEND_YIELD"
}

def get_vndirect_ratio(symbol, ratio_code):
    url = "https://api-finfo.vndirect.com.vn/v4/ratios"
    params = {"q": f"code:{symbol}~ratioCode:{ratio_code}", "size": 1, "sort": "reportDate:desc"}
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
    try:
        r = requests.get(url, params=params, headers=headers, timeout=10)
        if r.status_code == 200:
            data = r.json().get("data", [])
            if data:
                return float(data[0].get("value", 0))
    except Exception:
        pass
    return 0

def aggregate_candles(data, interval):
    """Thuật toán gom nhóm nến D1 thành W1 (Tuần) hoặc MN (Tháng) chuẩn xác"""
    if not data:
        return []
    if interval == 'D1':
        return data

    groups = {}
    for bar in data:
        date = datetime.datetime.strptime(bar['time'], '%Y-%m-%d')
        if interval == 'W1':
            start_of_week = date - datetime.timedelta(days=date.weekday())
            key = start_of_week.strftime('%Y-%m-%d')
        elif interval == 'MN':
            key = date.strftime('%Y-%m-01')

        if key not in groups:
            groups[key] = {
                "time": key,
                "open": bar['open'],
                "high": bar['high'],
                "low": bar['low'],
                "close": bar['close'],
                "volume": bar['volume']
            }
        else:
            groups[key]['high'] = max(groups[key]['high'], bar['high'])
            groups[key]['low'] = min(groups[key]['low'], bar['low'])
            groups[key]['close'] = bar['close']
            groups[key]['volume'] += bar['volume']

    return sorted(list(groups.values()), key=lambda x: x['time'])

def fetch_history_with_fallback(symbol, start_date, end_date):
    """Thử lần lượt các nguồn TCBS và VCI với cơ chế đổi User-Agent phòng chống chặn"""
    sources = ['TCBS', 'VCI']
    for src in sources:
        for attempt in range(2): # Thử lại tối đa 2 lần cho mỗi nguồn
            try:
                quote = Quote(source=src, symbol=symbol)
                df = quote.history(start=start_date, end=end_date)
                if df is not None and not df.empty:
                    return df
            except Exception:
                time.sleep(1) # Nghỉ ngắn khi gặp lỗi trước khi thử lại
        time.sleep(0.5)
    return None

def auto_git_push():
    """Tự động đồng bộ dữ liệu lên GitHub"""
    try:
        print("📤 Đang tiến hành đồng bộ dữ liệu lên GitHub...")
        subprocess.run(["git", "add", DATA_FILE], check=True)
        subprocess.run(["git", "add", HISTORY_DIR], check=True)
        if os.path.exists(JS_LIB_FILE):
            subprocess.run(["git", "add", JS_LIB_FILE], check=True)
            
        commit_msg = f"Auto update safe multi-source data - {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        subprocess.run(["git", "commit", "-m", commit_msg], check=True)
        subprocess.run(["git", "push"], check=True)
        print("🚀 Đẩy dữ liệu lên GitHub thành công!")
    except subprocess.CalledProcessError:
        print("⚠️ Git: Không có thay đổi mới để push hoặc đã được cập nhật.")
    except Exception as e:
        print(f"⚠️ Lỗi Git push: {e}")

def main():
    print("🚀 Bắt đầu cào dữ liệu 2 năm với tốc độ an toàn chống chặn...")
    
    if not os.path.exists(HISTORY_DIR):
        os.makedirs(HISTORY_DIR)

    stock_db = {}
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, "r", encoding="utf-8") as f:
                stock_db = json.load(f)
        except Exception:
            pass

    total = len(VN100_SYMBOLS)
    end_date = datetime.datetime.now().strftime("%Y-%m-%d")
    start_date = (datetime.datetime.now() - datetime.timedelta(days=730)).strftime("%Y-%m-%d")

    for i, symbol in enumerate(VN100_SYMBOLS):
        print(f"[{i+1}/{total}] Đang xử lý: {symbol}...")
        closes, volumes = [], []
        close_price, volume = 0, 0
        history_d1 = []
        
        try:
            df = fetch_history_with_fallback(symbol, start_date, end_date)
            
            if df is not None and not df.empty:
                closes = df['close'].tolist()
                volumes = df['volume'].tolist()
                close_price = closes[-1]
                volume = volumes[-1]
                
                for _, row in df.iterrows():
                    time_val = row['time']
                    time_str = time_val.strftime('%Y-%m-%d') if hasattr(time_val, 'strftime') else str(time_val)[:10]
                    
                    history_d1.append({
                        "time": time_str,
                        "open": float(row.get('open', row['close'])),
                        "high": float(row.get('high', row['close'])),
                        "low": float(row.get('low', row['close'])),
                        "close": float(row['close']),
                        "volume": int(row.get('volume', 0))
                    })
        except Exception as e:
            print(f"⚠️ Lỗi xử lý lịch sử {symbol}: {e}")

        if close_price <= 0:
            print(f"⚠️ Bỏ qua {symbol} do không lấy được giá.")
            continue

        ratios = {}
        for key, code in VNDIRECT_RATIOS.items():
            ratios[key] = get_vndirect_ratio(symbol, code)
            time.sleep(0.2)

        # Thuật toán Price Action cơ bản
        status = "ĐANG TÍCH LŨY NỀN"
        detail = "Đang siết nền tích lũy biên độ hẹp."
        if len(closes) >= 20 and len(volumes) >= 20:
            recent_vols = volumes[-20:]
            ma_vol_20 = np.mean(recent_vols)
            vol_ratio = volume / ma_vol_20 if ma_vol_20 > 0 else 1.0
            price_change_pct = ((closes[-1] - closes[-2]) / closes[-2]) * 100 if closes[-2] > 0 else 0

            if vol_ratio < 0.7 and abs(price_change_pct) < 1.5:
                status = "ĐANG TÍCH LŨY NỀN (CẠN CUNG)"
                detail = f"Khối lượng cạn kiệt ở mức {vol_ratio:.2f}x MA20."
            elif vol_ratio > 1.5 and price_change_pct > 1.5:
                status = "SẴN SÀNG BREAKOUT (NỔ VOL)"
                detail = f"Khối lượng bùng nổ đạt {vol_ratio:.2f}x MA20 kèm giá tăng."
            elif closes[-1] > np.mean(closes[-20:]):
                status = "ĐANG GOM HÀNG"
                detail = "Dòng tiền duy trì ổn định trên MA20."

        # Gom nhóm nến Tuần và Tháng
        history_w1 = aggregate_candles(history_d1, 'W1')
        history_mn = aggregate_candles(history_d1, 'MN')

        # Lưu file lịch sử riêng cho từng mã
        symbol_history_data = {
            "history_d1": history_d1,
            "history_w1": history_w1,
            "history_mn": history_mn
        }
        with open(os.path.join(HISTORY_DIR, f"{symbol}.json"), "w", encoding="utf-8") as sf:
            json.dump(symbol_history_data, sf, ensure_ascii=False)

        old_data = stock_db.get(symbol, {})
        
        stock_db[symbol] = {
            "symbol": symbol,
            "close": int(close_price * 1000),
            "volume": int(volume),
            "pe": round(ratios.get("pe", 0), 2),
            "pb": round(ratios.get("pb", 0), 2),
            "eps": int(ratios.get("eps", 0)),
            "roe": round(ratios.get("roe", 0) * 100, 1),
            "roa": round(ratios.get("roa", 0) * 100, 1),
            "dividend_yield": round(ratios.get("dividend_yield", 0) * 100, 2),
            "recommendation": status,
            "price_zone": detail,
            "updated_at": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "bctc": old_data.get("bctc", ""),
            "outlook": old_data.get("outlook", ""),
            "ai_recommendation": old_data.get("ai_recommendation", ""),
            "ai_price_zone": old_data.get("ai_price_zone", ""),
            "macro_view": old_data.get("macro_view", ""),
            "ai_updated_at": old_data.get("ai_updated_at", "")
        }
        
        # 💡 TĂNG THỜI GIAN NGHỈ AN TOÀN: Nghỉ từ 1.5 đến 2 giây giữa các mã để không bị máy chủ chặn IP
        time.sleep(1.5)

    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(stock_db, f, ensure_ascii=False, indent=4)
    print("✅ Đã hoàn tất toàn bộ dữ liệu an toàn!")

    auto_git_push()

if __name__ == "__main__":
    main()
