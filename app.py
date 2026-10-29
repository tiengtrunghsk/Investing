import sys
import os
import requests
import pandas as pd
import streamlit as st
from datetime import datetime, timedelta

# ==========================================
# DANH SÁCH ~100 MÃ CƠ BẢN CÓ THANH KHOẢN TỐT NHẤT THỊ TRƯỜNG
# ==========================================
CURATED_100_STOCKS = {
    # 🏦 Ngân hàng
    "VCB": "Ngân hàng", "BID": "Ngân hàng", "CTG": "Ngân hàng", "TCB": "Ngân hàng", 
    "MBB": "Ngân hàng", "ACB": "Ngân hàng", "STB": "Ngân hàng", "SHB": "Ngân hàng", 
    "TPB": "Ngân hàng", "VIB": "Ngân hàng", "HDB": "Ngân hàng", "LPB": "Ngân hàng", 
    "MSB": "Ngân hàng", "SSB": "Ngân hàng", "EIB": "Ngân hàng", "OCB": "Ngân hàng",

    # 📊 Chứng khoán
    "SSI": "Chứng khoán", "VCI": "Chứng khoán", "HCM": "Chứng khoán", "VIX": "Chứng khoán", 
    "MBS": "Chứng khoán", "FTS": "Chứng khoán", "BSI": "Chứng khoán", "SHS": "Chứng khoán", 
    "CTS": "Chứng khoán", "AGR": "Chứng khoán", "ORS": "Chứng khoán",

    # 🏗️ Bất động sản
    "VIC": "Bất động sản", "VHM": "Bất động sản", "VRE": "Bất động sản", "KBC": "Bất động sản", 
    "DIG": "Bất động sản", "NVL": "Bất động sản", "PDR": "Bất động sản", "DXG": "Bất động sản", 
    "NLG": "Bất động sản", "KDH": "Bất động sản", "HDG": "Bất động sản", "CEO": "Bất động sản", 
    "VPI": "Bất động sản", "DIG": "Bất động sản",

    # ⚙️ Thép & Vật liệu xây dựng
    "HPG": "Thép & Vật liệu", "NKG": "Thép & Vật liệu", "HSG": "Thép & Vật liệu", 
    "VGS": "Thép & Vật liệu", "BCC": "Thép & Vật liệu", "HT1": "Thép & Vật liệu",

    # 🛒 Bán lẻ & Tiêu dùng & Thực phẩm
    "FPT": "Công nghệ & Bán lẻ", "MWG": "Công nghệ & Bán lẻ", "PNJ": "Công nghệ & Bán lẻ", 
    "FRT": "Công nghệ & Bán lẻ", "VNM": "Tiêu dùng", "MSN": "Tiêu dùng", "SAB": "Tiêu dùng", 
    "KDC": "Tiêu dùng", "QNS": "Tiêu dùng", "VHC": "Thủy sản & Xuất khẩu", "ANV": "Thủy sản & Xuất khẩu",

    # ⚡ Năng lượng, Dầu khí & Hóa chất
    "GAS": "Năng lượng & Dầu khí", "POW": "Năng lượng & Dầu khí", "BSR": "Năng lượng & Dầu khí", 
    "PLX": "Năng lượng & Dầu khí", "PVD": "Năng lượng & Dầu khí", "PVS": "Năng lượng & Dầu khí", 
    "DGC": "Hóa chất", "DCM": "Hóa chất", "DPM": "Hóa chất", "GEX": "Công nghiệp", 
    "REE": "Công nghiệp", "PC1": "Công nghiệp", "VGC": "Khu công nghiệp", "SZC": "Khu công nghiệp"
}

def get_stock_data_direct(symbol):
    """Lấy dữ liệu lịch sử giá OHLCV trực tiếp qua API với tốc độ cao"""
    try:
        end_date = datetime.now()
        start_date = end_date - timedelta(days=120)
        
        start_timestamp = int(start_date.timestamp())
        end_timestamp = int(end_date.timestamp())
        
        url = f"https://dchart-api.vndirect.com.vn/dchart/history?resolution=D&symbol={symbol.upper()}&from={start_timestamp}&to={end_timestamp}"
        headers = {"User-Agent": "Mozilla/5.0"}
        
        res = requests.get(url, headers=headers, timeout=5)
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
        pass
    return None

def analyze_stock(symbol, industry):
    """Phân tích kỹ thuật Breakout & Squeeze"""
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

    # Lọc thanh khoản tối thiểu (đảm bảo trên 100k cổ phiếu/phiên cho nhóm 100 mã lớn)
    if volume < 100000:
        return None

    # Điều kiện Breakout
    is_breakout = (close_price > ma20) and (prev['close'] <= prev['MA20']) and (volume > 1.5 * vol_ma20)
    
    # Điều kiện Squeeze (Cạn cung)
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

def run_screening_fast():
    """Quét nhanh danh sách 100 mã cốt lõi"""
    breakout_list = []
    squeeze_list = []
    
    for symbol, industry in CURATED_100_STOCKS.items():
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
    print("Đang chạy quét nhanh 100 mã chất lượng cao...")
    breakouts, squeezes = run_screening_fast()
    
    msg = "🚨 *PRO QUANT SCREENER - TOP 100 MÃ BLUECHIP/MIDCAP* 🚨\n\n"
    
    msg += "🚀 *1. Nhóm Breakout (Nổ Vol & Vượt MA20):*\n"
    if breakouts:
        for b in breakouts:
            msg += f"• `{b['symbol']}` ({b['industry']}) - Giá: {b['close']:,.2f} | Vol: {b['volume']:,.0f}\n"
    else:
        msg += "• Không có mã nào đạt tiêu chí hôm nay.\n"
        
    msg += "\n📦 *2. Nhóm Squeeze (Cạn cung / Tích lũy hẹp):*\n"
    if squeezes:
        for s in squeezes:
            msg += f"• `{s['symbol']}` ({s['industry']}) - Giá: {s['close']:,.2f} | Vol: {s['volume']:,.0f}\n"
    else:
        msg += "• Không có mã nào đạt tiêu chí hôm nay.\n"
        
    send_telegram_message(msg)
    sys.exit(0)

# ==========================================
# GIAO DIỆN STREAMLIT WEB
# ==========================================
st.set_page_config(page_title="Pro Quant Screener - Top 100", page_icon="📈", layout="wide")

st.title("📈 Pro Quant Stock Screener (Top 100 Mã Thanh Khoản Tốt)")
st.markdown("Hệ thống lọc định lượng tập trung vào các nhóm ngành chủ lực, tối ưu tốc độ xử lý và độ chính xác cao.")

with st.spinner("⚡ Đang quét nhanh nhóm 100 cổ phiếu hàng đầu..."):
    breakouts, squeezes = run_screening_fast()

st.success("✅ Hoàn tất phân tích tốc độ cao!")

col1, col2 = st.columns(2)
with col1:
    st.subheader(f"🚀 Nhóm Breakout ({len(breakouts)} mã)")
    if breakouts:
        df_b = pd.DataFrame(breakouts)
        st.dataframe(df_b[['symbol', 'industry', 'close', 'volume']], use_container_width=True)
    else:
        st.info("Không tìm thấy mã Breakout nào.")
        
with col2:
    st.subheader(f"📦 Nhóm Squeeze - Cạn Cung ({len(squeezes)} mã)")
    if squeezes:
        df_s = pd.DataFrame(squeezes)
        st.dataframe(df_s[['symbol', 'industry', 'close', 'volume']], use_container_width=True)
    else:
        st.info("Không tìm thấy mã Squeeze nào.")
        
if st.button("📤 Gửi báo cáo về Telegram", type="primary"):
    msg = f"📊 *BÁO CÁO TỪ WEB (TOP 100)*\nBreakout: {len(breakouts)} mã | Squeeze: {len(squeezes)} mã"
    send_telegram_message(msg)
    st.toast("Đã gửi thông báo!", icon="✅")
