import sys
import os
import requests
import pandas as pd
import streamlit as st
from datetime import datetime, timedelta

# ==========================================
# DANH SÁCH MÃ THEO DÕI MẶC ĐỊNH (Watchlist)
# ==========================================
DEFAULT_WATCHLIST = [
    "FPT", "MWG", "PNJ", "FRT", "VNM", "MSN",
    "MBB", "TCB", "VCB", "ACB", "STB", "BID", "CTG", "SHB", "TPB", "VIB",
    "SSI", "HCM", "VCI", "VIX",
    "HPG", "DGC", "GEX",
    "VIC", "KBC", "DIG", "NVL", "PDR"
]

# ==========================================
# LẤY DỮ LIỆU GIÁ TRỰC TIẾP QUA API PUBLIC
# ==========================================
def get_stock_data_direct(symbol):
    """Lấy dữ liệu lịch sử giá OHLCV trực tiếp từ API chứng khoán (Không cần thư viện ngoài)"""
    try:
        # Thời gian 100 ngày gần nhất
        end_date = datetime.now()
        start_date = end_date - timedelta(days=120)
        
        start_timestamp = int(start_date.timestamp())
        end_timestamp = int(end_date.timestamp())
        
        # Gọi API public
        url = f"https://dchart-api.vndirect.com.vn/dchart/history?resolution=D&symbol={symbol.upper()}&from={start_timestamp}&to={end_timestamp}"
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }
        
        res = requests.get(url, headers=headers, timeout=10)
        if res.status_code == 200:
            data = res.json()
            if data.get("s") == "ok":
                df = pd.DataFrame({
                    "time": pd.to_datetime(data["t"], unit="s"),
                    "open": data["o"],
                    "high": data["h"],
                    "low": data["l"],
                    "close": data["c"],
                    "volume": data["v"]
                })
                return df
    except Exception as e:
        print(f"Lỗi tải mã {symbol}: {e}")
    return None

def analyze_stock(symbol):
    """Phân tích kỹ thuật (Breakout & Squeeze)"""
    df = get_stock_data_direct(symbol)
    if df is None or len(df) < 20:
        return None
    
    # Tính MA20 và Volume MA20
    df['MA20'] = df['close'].rolling(window=20).mean()
    df['Volume_MA20'] = df['volume'].rolling(window=20).mean()
    
    latest = df.iloc[-1]
    prev = df.iloc[-2]
    
    close_price = latest['close']
    ma20 = latest['MA20']
    volume = latest['volume']
    vol_ma20 = latest['Volume_MA20']
    
    if pd.isna(prev['MA20']) or pd.isna(ma20) or pd.isna(vol_ma20):
        return None

    # Điều kiện Breakout: Giá vượt MA20 + Vol bùng nổ (> 1.5 lần trung bình 20 phiên)
    is_breakout = (close_price > ma20) and (prev['close'] <= prev['MA20']) and (volume > 1.5 * vol_ma20)
    
    # Điều kiện Squeeze (Cạn cung): Biên độ 5 phiên hẹp + Vol thấp
    avg_close_5 = df['close'].tail(5).mean()
    price_range = (df['high'].tail(5) - df['low'].tail(5)).mean() / avg_close_5 if avg_close_5 > 0 else 0
    is_squeeze = (price_range < 0.02) and (volume < 0.8 * vol_ma20)
    
    return {
        "symbol": symbol,
        "close": close_price,
        "volume": volume,
        "is_breakout": is_breakout,
        "is_squeeze": is_squeeze
    }

def run_screening(watchlist):
    """Quét toàn bộ danh sách mã"""
    breakout_list = []
    squeeze_list = []
    
    for symbol in watchlist:
        res = analyze_stock(symbol.strip().upper())
        if res:
            if res["is_breakout"]:
                breakout_list.append(res)
            if res["is_squeeze"]:
                squeeze_list.append(res)
                
    return breakout_list, squeeze_list

def send_telegram_message(message):
    """Gửi thông báo Telegram"""
    token = os.environ.get("TELEGRAM_TOKEN")
    chat_id = os.environ.get("CHAT_ID")
    
    if not token and hasattr(st, "secrets"):
        token = st.secrets.get("TELEGRAM_TOKEN")
        chat_id = st.secrets.get("CHAT_ID")
        
    if not token or not chat_id:
        print("Chưa cấu hình TELEGRAM_TOKEN hoặc CHAT_ID!")
        return
        
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": message,
        "parse_mode": "Markdown"
    }
    try:
        response = requests.post(url, json=payload)
        if response.status_code == 200:
            print("Đã gửi Telegram thành công!")
    except Exception as e:
        print(f"Lỗi Telegram: {e}")

# ==========================================
# CHẾ ĐỘ AUTO BÁO CÁO (GitHub Actions)
# ==========================================
if len(sys.argv) > 1 and sys.argv[1] == "--auto":
    print("Đang chạy chế độ tự động...")
    breakouts, squeezes = run_screening(DEFAULT_WATCHLIST)
    
    msg = "🚨 *PRO QUANT SCREENER - BÁO CÁO TỰ ĐỘNG* 🚨\n\n"
    msg += "🚀 *1. Nhóm Breakout (Nổ Vol & Vượt MA20):*\n"
    if breakouts:
        for b in breakouts:
            # Giá API VNDirect tính bằng VNĐ chuẩn (ví dụ 30,000)
            msg += f"• `{b['symbol']}` - Giá: {b['close']:,.0f} | Vol: {b['volume']:,.0f}\n"
    else:
        msg += "• Không có mã nào đạt tiêu chí hôm nay.\n"
        
    msg += "\n📦 *2. Nhóm Squeeze (Cạn cung / Tích lũy hẹp):*\n"
    if squeezes:
        for s in squeezes:
            msg += f"• `{s['symbol']}` - Giá: {s['close']:,.0f}\n"
    else:
        msg += "• Không có mã nào đạt tiêu chí hôm nay.\n"
        
    send_telegram_message(msg)
    sys.exit(0)

# ==========================================
# GIAO DIỆN STREAMLIT WEB
# ==========================================
st.set_page_config(page_title="Pro Quant Screener", page_icon="📈", layout="wide")

st.title("📈 Pro Quant Stock Screener")
st.markdown("Hệ thống lọc cổ phiếu định lượng tự động (**Breakout** & **Squeeze**).")

st.sidebar.header("⚙️ Cấu hình quét")
watchlist_input = st.sidebar.text_area(
    "Danh sách cổ phiếu theo dõi:",
    value=", ".join(DEFAULT_WATCHLIST),
    height=150
)

if st.sidebar.button("🚀 Chạy Quét Tất Cả Chiến Lược", type="primary"):
    custom_watchlist = [s.strip() for s in watchlist_input.split(",") if s.strip()]
    
    with st.spinner("Đang tải dữ liệu và phân tích thị trường..."):
        breakouts, squeezes = run_screening(custom_watchlist)
        
    st.success("Quét hoàn tất!")
    
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("🚀 Nhóm Breakout")
        if breakouts:
            df_b = pd.DataFrame(breakouts)
            st.dataframe(df_b[['symbol', 'close', 'volume']], use_container_width=True)
        else:
            st.info("Không tìm thấy mã Breakout nào.")
            
    with col2:
        st.subheader("📦 Nhóm Squeeze (Cạn cung)")
        if squeezes:
            df_s = pd.DataFrame(squeezes)
            st.dataframe(df_s[['symbol', 'close', 'volume']], use_container_width=True)
        else:
            st.info("Không tìm thấy mã Squeeze nào.")
            
    if st.button("📤 Gửi báo cáo này về Telegram"):
        msg = f"📊 *BÁO CÁO TỪ WEB*\nBreakout: {len(breakouts)} mã | Squeeze: {len(squeezes)} mã"
        send_telegram_message(msg)
        st.toast("Đã gửi thông báo!", icon="✅")
