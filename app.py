import sys
import subprocess
import os

# ==========================================
# CÀI ĐẶT & IMPORT TỰ ĐỘNG VNSTOCK DỰ PHÒNG
# ==========================================
try:
    import vnstock
    from vnstock import Market
except ImportError:
    print("🔄 Đang cài đặt tự động vnstock...")
    subprocess.check_call([
        sys.executable, "-m", "pip", "install", 
        "vnstock==5.0.1", 
        "--extra-index-url", "https://vnstocks.com/api/packages"
    ])
    import vnstock
    from vnstock import Market

import requests
import pandas as pd
import streamlit as st

# ==========================================
# CẤU HÌNH XÁC THỰC VNSTOCK
# ==========================================
api_key = os.environ.get("VNSTOCK_API_KEY")
if not api_key and hasattr(st, "secrets") and "VNSTOCK_API_KEY" in st.secrets:
    api_key = st.secrets["VNSTOCK_API_KEY"]

if api_key:
    try:
        vnstock.login(api_key)
        print("✅ Đăng nhập vnstock thành công!")
    except Exception as e:
        print(f"❌ Lỗi đăng nhập vnstock: {e}")
else:
    print("⚠️ Không tìm thấy VNSTOCK_API_KEY. Chạy ở cấp Khách (Guest)!")

# ==========================================
# DANH SÁCH MÃ THEO DÕI MẶC ĐỊNH
# ==========================================
DEFAULT_WATCHLIST = [
    "FPT", "MWG", "PNJ", "FRT", "VNM", "MSN",
    "MBB", "TCB", "VCB", "ACB", "STB", "BID", "CTG", "SHB", "TPB", "VIB",
    "SSI", "HCM", "VCI", "VIX",
    "HPG", "DGC", "GEX",
    "VIC", "KBC", "DIG", "NVL", "PDR"
]

# ==========================================
# CÁC HÀM XỬ LÝ DỮ LIỆU & CHIẾN LƯỢC QUANT
# ==========================================
def get_stock_data(symbol):
    """Lấy dữ liệu lịch sử giá từ vnstock 5.x"""
    try:
        df = Market().equity(symbol).ohlcv(limit=60)
        if df is not None and not df.empty:
            df['time'] = pd.to_datetime(df['time'])
            return df
    except Exception as e:
        print(f"Lỗi khi lấy dữ liệu mã {symbol}: {e}")
    return None

def analyze_stock(symbol):
    """Tính toán chỉ báo kỹ thuật cho từng mã"""
    df = get_stock_data(symbol)
    if df is None or len(df) < 20:
        return None
    
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

    # Điều kiện Breakout
    is_breakout = (close_price > ma20) and (prev['close'] <= prev['MA20']) and (volume > 1.5 * vol_ma20)
    
    # Điều kiện Squeeze (Cạn cung)
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
    """Chạy quét toàn bộ danh sách mã"""
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
    """Gửi thông báo về Telegram"""
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
            print("Đã gửi tin nhắn Telegram thành công!")
        else:
            print(f"Lỗi gửi Telegram: {response.text}")
    except Exception as e:
        print(f"Lỗi kết nối Telegram: {e}")

# ==========================================
# CHẾ ĐỘ CHẠY TỰ ĐỘNG (GitHub Actions / CLI)
# ==========================================
if len(sys.argv) > 1 and sys.argv[1] == "--auto":
    print("Đang chạy chế độ tự động (Auto Mode)...")
    breakouts, squeezes = run_screening(DEFAULT_WATCHLIST)
    
    msg = "🚨 *PRO QUANT SCREENER - BÁO CÁO TỰ ĐỘNG* 🚨\n\n"
    
    msg += "🚀 *1. Nhóm Breakout (Nổ Vol & Vượt MA20):*\n"
    if breakouts:
        for b in breakouts:
            price_str = f"{b['close'] * 1000:,.0f}" 
            msg += f"• `{b['symbol']}` - Giá: {price_str} | Vol: {b['volume']:,.0f}\n"
    else:
        msg += "• Không có mã nào đạt tiêu chí hôm nay.\n"
        
    msg += "\n📦 *2. Nhóm Squeeze (Cạn cung / Tích lũy hẹp):*\n"
    if squeezes:
        for s in squeezes:
            price_str = f"{s['close'] * 1000:,.0f}"
            msg += f"• `{s['symbol']}` - Giá: {price_str}\n"
    else:
        msg += "• Không có mã nào đạt tiêu chí hôm nay.\n"
        
    send_telegram_message(msg)
    sys.exit(0)

# ==========================================
# CHẾ ĐỘ GIAO DIỆN WEB (Streamlit UI)
# ==========================================
st.set_page_config(
    page_title="Pro Quant Screener",
    page_icon="📈",
    layout="wide"
)

st.title("📈 Pro Quant Stock Screener")
st.markdown("Hệ thống lọc cổ phiếu định lượng tự động (**Breakout** & **Squeeze**) sử dụng dữ liệu vnstock 5.x.")

st.sidebar.header("⚙️ Cấu hình quét")
watchlist_input = st.sidebar.text_area(
    "Danh sách cổ phiếu theo dõi (phân tách bằng dấu phẩy):",
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
            df_b['close'] = df_b['close'] * 1000
            st.dataframe(df_b[['symbol', 'close', 'volume']], use_container_width=True)
        else:
            st.info("Không tìm thấy mã Breakout nào.")
            
    with col2:
        st.subheader("📦 Nhóm Squeeze (Cạn cung)")
        if squeezes:
            df_s = pd.DataFrame(squeezes)
            df_s['close'] = df_s['close'] * 1000
            st.dataframe(df_s[['symbol', 'close', 'volume']], use_container_width=True)
        else:
            st.info("Không tìm thấy mã Squeeze nào.")
            
    if st.button("📤 Gửi báo cáo này về Telegram"):
        msg = "📊 *BÁO CÁO THỦ CÔNG TỪ WEB*\n\n"
        msg += f"Số mã Breakout: {len(breakouts)} | Số mã Squeeze: {len(squeezes)}"
        send_telegram_message(msg)
        st.toast("Đã gửi thông báo tới Telegram của bạn!", icon="✅")
