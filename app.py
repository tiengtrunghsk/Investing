import sys
import os
import requests
import pandas as pd
import streamlit as st
from datetime import datetime, timedelta

# ==========================================
# LẤY TOÀN BỘ DANH SÁCH MÃ & PHÂN NGÀNH TỰ ĐỘNG
# ==========================================
@st.cache_data(ttl=86400)
def get_all_market_stocks():
    """Tự động lấy toàn bộ danh sách cổ phiếu niêm yết trên HOSE, HNX từ API công khai"""
    try:
        url = "https://finfo-api.vndirect.com.vn/v4/stocks?q=type:stock~floor:HOSE,HNX&size=1000"
        headers = {"User-Agent": "Mozilla/5.0"}
        res = requests.get(url, headers=headers, timeout=10)
        
        if res.status_code == 200:
            data = res.json().get("data", [])
            stock_dict = {}
            for item in data:
                code = item.get("code")
                # Lọc bỏ chứng quyền hoặc mã không phải 3 ký tự chuẩn
                if code and len(code) == 3 and "-" not in code:
                    # Phân loại nhóm ngành dựa trên thông tin API hoặc mã phổ biến
                    industry = item.get("industryName", "Khác")
                    stock_dict[code] = industry if industry else "Khác"
            return stock_dict
    except Exception as e:
        print(f"Lỗi tải danh sách thị trường: {e}")
    
    # Danh sách dự phòng mở rộng quy mô lớn nếu API lỗi
    return {
        "FPT": "Công nghệ", "MWG": "Bán lẻ", "PNJ": "Bán lẻ", "FRT": "Bán lẻ", "VNM": "Tiêu dùng", "MSN": "Tiêu dùng",
        "MBB": "Ngân hàng", "TCB": "Ngân hàng", "VCB": "Ngân hàng", "ACB": "Ngân hàng", "STB": "Ngân hàng", 
        "BID": "Ngân hàng", "CTG": "Ngân hàng", "SHB": "Ngân hàng", "TPB": "Ngân hàng", "VIB": "Ngân hàng",
        "SSI": "Chứng khoán", "HCM": "Chứng khoán", "VCI": "Chứng khoán", "VIX": "Chứng khoán", "MBS": "Chứng khoán",
        "HPG": "Thép & Vật liệu", "NKG": "Thép & Vật liệu", "HSG": "Thép & Vật liệu", "DGC": "Hóa chất", "GEX": "Công nghiệp",
        "VIC": "Bất động sản", "VHM": "Bất động sản", "KBC": "Bất động sản", "DIG": "Bất động sản", "NVL": "Bất động sản", "PDR": "Bất động sản"
    }

def get_stock_data_direct(symbol):
    """Lấy dữ liệu lịch sử giá OHLCV trực tiếp"""
    try:
        end_date = datetime.now()
        start_date = end_date - timedelta(days=120)
        
        start_timestamp = int(start_date.timestamp())
        end_timestamp = int(end_date.timestamp())
        
        url = f"https://dchart-api.vndirect.com.vn/dchart/history?resolution=D&symbol={symbol.upper()}&from={start_timestamp}&to={end_timestamp}"
        headers = {"User-Agent": "Mozilla/5.0"}
        
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

def analyze_stock(symbol, industry):
    """Phân tích kỹ thuật (Breakout & Squeeze) trên quy mô rộng"""
    df = get_stock_data_direct(symbol)
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

    # Lọc bỏ các mã thanh khoản quá thấp (tránh cổ phiếu rác, thanh khoản dưới 50k cổ phiếu/phiên)
    if volume < 50000:
        return None

    # Điều kiện Breakout: Giá vượt MA20 + Vol bùng nổ (> 1.5 lần trung bình 20 phiên)
    is_breakout = (close_price > ma20) and (prev['close'] <= prev['MA20']) and (volume > 1.5 * vol_ma20)
    
    # Điều kiện Squeeze (Cạn cung): Biên độ 5 phiên hẹp + Vol thấp
    avg_close_5 = df['close'].tail(5).mean()
    price_range = (df['high'].tail(5) - df['low'].tail(5)).mean() / avg_close_5 if avg_close_5 > 0 else 0
    is_squeeze = (price_range < 0.02) and (volume < 0.8 * vol_ma20)
    
    return {
        "symbol": symbol,
        "industry": industry,
        "close": close_price,
        "volume": volume,
        "is_breakout": is_breakout,
        "is_squeeze": is_squeeze
    }

def run_screening_market(stock_dict):
    """Quét toàn bộ danh sách thị trường"""
    breakout_list = []
    squeeze_list = []
    
    for symbol, industry in stock_dict.items():
        res = analyze_stock(symbol, industry)
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
        return
        
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": message,
        "parse_mode": "Markdown"
    }
    try:
        requests.post(url, json=payload, timeout=10)
    except Exception as e:
        print(f"Lỗi Telegram: {e}")

# ==========================================
# CHẾ ĐỘ AUTO BÁO CÁO (GitHub Actions)
# ==========================================
if len(sys.argv) > 1 and sys.argv[1] == "--auto":
    print("Đang quét toàn bộ thị trường tự động...")
    all_stocks = get_all_market_stocks()
    breakouts, squeezes = run_screening_market(all_stocks)
    
    msg = "🚨 *PRO QUANT SCREENER - TOÀN THỊ TRƯỜNG* 🚨\n\n"
    msg += f"🔍 *Đã quét trên tổng số {len(all_stocks)} mã cổ phiếu.*\n\n"
    
    msg += "🚀 *1. Nhóm Breakout (Nổ Vol & Vượt MA20):*\n"
    if breakouts:
        for b in breakouts[:15]: # Giới hạn hiển thị top 15 mã để tránh tin nhắn quá dài
            msg += f"• `{b['symbol']}` ({b['industry']}) - Giá: {b['close']:,.2f} | Vol: {b['volume']:,.0f}\n"
    else:
        msg += "• Không có mã nào đạt tiêu chí hôm nay.\n"
        
    msg += "\n📦 *2. Nhóm Squeeze (Cạn cung / Tích lũy hẹp):*\n"
    if squeezes:
        for s in squeezes[:15]:
            msg += f"• `{s['symbol']}` ({s['industry']}) - Giá: {s['close']:,.2f}\n"
    else:
        msg += "• Không có mã nào đạt tiêu chí hôm nay.\n"
        
    send_telegram_message(msg)
    sys.exit(0)

# ==========================================
# GIAO DIỆN STREAMLIT WEB
# ==========================================
st.set_page_config(page_title="Pro Quant Screener - Toàn Thị Trường", page_icon="📈", layout="wide")

st.title("📈 Pro Quant Stock Screener (Quét Toàn Thị Trường)")
st.markdown("Hệ thống tự động quét **hàng trăm mã cổ phiếu** trên toàn thị trường, lọc bỏ mã thanh khoản kém và tìm kiếm cơ hội **Breakout & Squeeze** theo nhóm ngành.")

all_stocks = get_all_market_stocks()

with st.spinner(f"⏳ Đang tải và phân tích dữ liệu toàn thị trường ({len(all_stocks)} mã)... Quá trình này có thể mất vài giây..."):
    breakouts, squeezes = run_screening_market(all_stocks)

st.success(f"✅ Quét toàn bộ {len(all_stocks)} mã thành công!")

col1, col2 = st.columns(2)
with col1:
    st.subheader(f"🚀 Nhóm Breakout ({len(breakouts)} mã)")
    if breakouts:
        df_b = pd.DataFrame(breakouts)
        st.dataframe(df_b[['symbol', 'industry', 'close', 'volume']], use_container_width=True)
    else:
        st.info("Không tìm thấy mã Breakout nào hôm nay.")
        
with col2:
    st.subheader(f"📦 Nhóm Squeeze - Cạn Cung ({len(squeezes)} mã)")
    if squeezes:
        df_s = pd.DataFrame(squeezes)
        st.dataframe(df_s[['symbol', 'industry', 'close', 'volume']], use_container_width=True)
    else:
        st.info("Không tìm thấy mã Squeeze nào hôm nay.")
        
if st.button("📤 Gửi báo cáo toàn thị trường về Telegram", type="primary"):
    msg = f"📊 *BÁO CÁO TOÀN THỊ TRƯỜNG*\nQuét: {len(all_stocks)} mã\nBreakout: {len(breakouts)} mã | Squeeze: {len(squeezes)} mã"
    send_telegram_message(msg)
    st.toast("Đã gửi thông báo!", icon="✅")
