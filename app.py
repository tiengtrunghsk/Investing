import os
import requests
import pandas as pd
import pandas_ta as ta
import streamlit as st
from vnstock import Market, Fundamental

# --- CẤU HÌNH GIAO DIỆN WEB ---
st.set_page_config(
    page_title="Pro Quant Screener & Auto Bot",
    page_icon="⚡",
    layout="wide"
)

st.title("⚡ Pro Quant Screener (Breakout & Squeeze)")
st.markdown("Hệ thống định lượng kết hợp PTCB + PTKT: Tự động quét, hiển thị trên Web và hỗ trợ gửi Telegram.")

# --- SIDEBAR: THIẾT LẬP THÔNG SỐ ---
st.sidebar.header("⚙️ 1. Bộ lọc Phân tích Cơ bản")
min_roe = st.sidebar.slider("ROE tối thiểu (%)", 0.0, 40.0, 12.0) / 100.0
max_pe = st.sidebar.slider("P/E tối đa", 5.0, 40.0, 20.0)

st.sidebar.header("🤖 2. Cấu hình Telegram")
# Lấy mặc định từ biến môi trường (nếu chạy tự động trên GitHub) hoặc nhập tay trên web
default_token = os.getenv('TELEGRAM_TOKEN', '')
default_chat = os.getenv('CHAT_ID', '')
telegram_token = st.sidebar.text_input("Telegram Bot Token", value=default_token, type="password")
chat_id = st.sidebar.text_input("Telegram Chat ID", value=default_chat)

default_watchlist = "FPT, VNM, HPG, MBB, TCB, MWG, VCB, ACB, SSI, VIC, MSN, PNJ, STB, BID, CTG, DGC, FRT, GEX"
watchlist_input = st.sidebar.text_area("Danh sách cổ phiếu theo dõi", default_watchlist)

# --- HÀM GỬI TELEGRAM ---
def send_telegram_alert(message):
    token = telegram_token or os.getenv('TELEGRAM_TOKEN')
    c_id = chat_id or os.getenv('CHAT_ID')
    
    if not token or not c_id:
        return False
    
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {"chat_id": c_id, "text": message, "parse_mode": "Markdown"}
    try:
        res = requests.post(url, json=payload, timeout=10)
        return res.status_code == 200
    except Exception as e:
        print(f"Lỗi gửi Telegram: {e}")
        return False

# --- HÀM QUÉT DỮ LIỆU CHUNG (DÙNG CHO CẢ WEB & BOT) ---
def run_quant_scan(symbols_list):
    market = Market()
    fa = Fundamental()
    
    breakout_list = []
    squeeze_list = []
    
    for symbol in symbols_list:
        try:
            # 1. Kiểm tra Cơ bản (PTCB)
            ratios = fa.ratio(symbol=symbol, period='quarter', lang='vi')
            roe = ratios['ROE'].iloc[-1]
            pe = ratios['P/E'].iloc[-1]
            if not (roe >= min_roe and 0 < pe <= max_pe):
                continue
            
            # 2. Kiểm tra Kỹ thuật (PTKT)
            df = market.equity.ohlcv(symbol=symbol, length=100)
            if len(df) < 40: continue
            
            df['MA20'] = ta.sma(df['close'], length=20)
            df['RSI'] = ta.rsi(df['close'], length=14)
            df['Vol_MA5'] = ta.sma(df['volume'], length=5)
            df['Vol_MA20'] = ta.sma(df['volume'], length=20)
            df['High_20'] = df['high'].shift(1).rolling(window=20).max()
            df['Price_Range_%'] = (df['high'] - df['low']) / df['close'] * 100
            df['Avg_Range_5'] = df['Price_Range_%'].rolling(window=5).mean()

            latest_close = df['close'].iloc[-1]
            latest_ma20 = df['MA20'].iloc[-1]
            latest_rsi = df['RSI'].iloc[-1]
            latest_vol = df['volume'].iloc[-1]
            vol_ma5 = df['Vol_MA5'].iloc[-1]
            vol_ma20 = df['Vol_MA20'].iloc[-1]
            prev_high_20 = df['High_20'].iloc[-1]
            avg_range_5 = df['Avg_Range_5'].iloc[-1]

            # Chiến lược A: Breakout
            if latest_close >= prev_high_20 * 0.995 and latest_vol >= (1.5 * vol_ma20) and latest_rsi <= 75 and latest_close > latest_ma20:
                breakout_list.append({
                    'Mã': symbol, 'Giá': latest_close, 'Tăng Vol': f"{round(latest_vol/vol_ma20, 1)}x", 
                    'RSI': round(latest_rsi, 1), 'ROE (%)': round(roe*100, 1), 'P/E': round(pe, 1)
                })
                continue

            # Chiến lược B: Cạn cung (Squeeze)
            if vol_ma5 <= (0.7 * vol_ma20) and avg_range_5 <= 2.2 and latest_close >= (latest_ma20 * 0.97):
                squeeze_list.append({
                    'Mã': symbol, 'Giá': latest_close, 'Cạn Vol (5/20)': f"{round(vol_ma5/vol_ma20*100)}%", 
                    'Biên độ 5p': f"{round(avg_range_5, 2)}%", 'ROE (%)': round(roe*100, 1), 'P/E': round(pe, 1)
                })
        except:
            continue
            
    return breakout_list, squeeze_list

# --- GIAO DIỆN TƯƠNG TÁC TRÊN WEB ---
if st.button("🚀 Chạy Quét Tất Cả Chiến Lược"):
    symbols = [s.strip().upper() for s in watchlist_input.split(",")]
    
    with st.spinner("Đang phân tích định lượng thị trường..."):
        breakout_list, squeeze_list = run_quant_scan(symbols)

    st.subheader("🔥 1. Nhóm Breakout (Nổ Vol + Vượt Đỉnh)")
    if breakout_list:
        st.dataframe(pd.DataFrame(breakout_list), use_container_width=True)
    else:
        st.info("Không có mã nào đạt chuẩn Breakout.")

    st.subheader("🟡 2. Nhóm Cạn Cung (Squeeze - Chờ Nổ)")
    if squeeze_list:
        st.dataframe(pd.DataFrame(squeeze_list), use_container_width=True)
    else:
        st.info("Không có mã nào đạt chuẩn Cạn Cung.")

    # Nút bấm gửi báo cáo thủ công từ Web
    if breakout_list or squeeze_list:
        if st.button("📤 Gửi báo cáo này về Telegram"):
            msg = "🎯 *BẢN TIN QUÉT ĐỊNH LƯỢNG TỪ WEB*\n--------------------------------------\n"
            if breakout_list:
                msg += "🔥 **NHÓM BREAKOUT:**\n"
                for item in breakout_list:
                    msg += f"• *{item['Mã']}* | Giá: `{item['Giá']}` | Vol: `{item['Tăng Vol']}` | ROE: `{item['ROE (%)']}%`\n"
            if squeeze_list:
                msg += "\n🟡 **NHÓM CẠN CUNG:**\n"
                for item in squeeze_list:
                    msg += f"• *{item['Mã']}* | Giá: `{item['Giá']}` | Cạn Vol: `{item['Cạn Vol (5/20)']}` | ROE: `{item['ROE (%)']}%`\n"
            
            if send_telegram_alert(msg):
                st.success("Đã bắn tin nhắn báo cáo về Telegram thành công!")
            else:
                st.error("Gửi thất bại! Kiểm tra lại Token hoặc Chat ID.")

# --- CHẾ ĐỘ CHẠY NGẦM TỰ ĐỘNG (KHI GITHUB ACTIONS GỌI) ---
# Đoạn này giúp file app.py tự động quét và gửi Telegram khi chạy lệnh: python app.py --auto
if __name__ == "__main__" and "--auto" in os.sys.argv:
    print("🤖 Đang chạy chế độ tự động hóa quét định lượng...")
    symbols = [s.strip().upper() for s in default_watchlist.split(",")]
    bo_list, sq_list = run_quant_scan(symbols)
    
    if bo_list or sq_list:
        report = "🔔 *BẢN TIN TỰ ĐỘNG HÀNG NGÀY*\n--------------------------------------\n"
        if bo_list:
            report += "🔥 **NHÓM BREAKOUT:**\n"
            for item in bo_list:
                report += f"• *{item['Mã']}* | Giá: `{item['Giá']}` | Vol: `{item['Tăng Vol']}` | ROE: `{item['ROE (%)']}%`\n"
        if sq_list:
            report += "\n🟡 **NHÓM CẠN CUNG:**\n"
            for item in sq_list:
                report += f"• *{item['Mã']}* | Giá: `{item['Giá']}` | Cạn Vol: `{item['Cạn Vol (5/20)']}` | ROE: `{item['ROE (%)']}%`\n"
        
        send_telegram_alert(report)
        print("Đã gửi bản tin tự động thành công!")
    else:
        print("Hôm nay không có mã nào đạt tiêu chí.")
