import os
import json
import time
import requests
from urllib.parse import quote

DATA_FILE = "data.json"
ALIBABA_API_KEY = os.environ.get("ALIBABA_API_KEY")
QWEN_API_URL = "https://dashscope-intl.aliyuncs.com/compatible-mode/v1/chat/completions"

# Dùng Proxy để lấy dữ liệu (tránh lỗi 403)
PROXY_PREFIX = "https://corsproxy.io/?url="
RAW_DCHART_URL = "https://dchart-api.vndirect.com.vn/dchart/history"
RAW_FUNDAMENTAL_URL = "https://api-finfo.vndirect.com.vn/v4/ratios"

VN100_SYMBOLS = [...] # (Giữ nguyên danh sách VN100)
INDUSTRY_MAP = {...}  # (Giữ nguyên map ngành)

def fetch_via_proxy(url, params):
    req = requests.Request('GET', url, params=params).prepare()
    proxy_url = PROXY_PREFIX + quote(req.url, safe='')
    try:
        r = requests.get(proxy_url, headers={"User-Agent": "Mozilla/5.0"}, timeout=15)
        if r.status_code == 200: return r.json()
    except Exception: pass
    return None

def fetch_data_for_ai(symbol):
    """Lấy Giá, P/E, P/B, ROE thực tế để đưa cho AI phân tích"""
    now = int(time.time())
    # Lấy giá
    params_price = {"resolution": "D", "symbol": symbol, "from": now - 30 * 86400, "to": now}
    price_data = fetch_via_proxy(RAW_DCHART_URL, params_price)
    current_price = price_data["c"][-1] if (price_data and price_data.get("s") == "ok") else 0
    
    # Lấy P/E, P/B, ROE
    def get_ratio(code):
        params = {"q": f"code:{symbol}~ratioCode:{code}", "size": 1, "sort": "reportDate:desc"}
        data = fetch_via_proxy(RAW_FUNDAMENTAL_URL, params)
        if data and data.get("data") and len(data["data"]) > 0:
            val = data["data"][0].get("value")
            return float(val) if val is not None else 0
        return 0

    pe = get_ratio("PRICE_TO_EARNINGS")
    pb = get_ratio("PRICE_TO_BOOK")
    roe = get_ratio("ROAE_TR_AVG5Q")
    
    return current_price, pe, pb, roe

def get_ai_evaluation(symbol, industry, price, pe, pb, roe):
    if not ALIBABA_API_KEY:
        return None, None, None, None

    prompt = f"""Bạn là một chuyên gia đầu tư giá trị (Value Investor) tại Việt Nam.
Hãy phân tích cổ phiếu {symbol} thuộc nhóm ngành {industry}.
Dưới đây là DỮ LIỆU THỰC TẾ hiện tại:
- Giá: {price:,.0f} VNĐ
- P/E: {pe}
- P/B: {pb}
- ROE: {roe}%

Dựa vào các CHỈ SỐ TÀI CHÍNH trên, hãy đưa ra đánh giá và chiến lược gom dài hạn.
Trả về DUY NHẤT JSON thuần túy (không markdown) gồm 4 trường:
1. "bctc": Nhận xét sức khỏe tài chính dựa trên P/E, P/B, ROE, tối đa 40 từ.
2. "outlook": Triển vọng kinh doanh 1-3 năm tới, tối đa 40 từ.
3. "recommendation": Chỉ chọn 1 trong các từ ("GOM TÍCH SẢN", "NẮM GIỮ CHẶT", "CHỜ ĐỢI", "HẠ TỶ TRỌNG") kèm 1 câu lý do dựa trên định giá.
4. "price_zone": Chiến lược gom vốn. VD: "P/E đang thấp, gom 30% vị thế. Chia 3 đợt gom nếu về vùng 40.000 - 42.000. Giữ 2-3 năm."
"""
    payload = {
        "model": "qwen-plus",
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.3,
        "response_format": {"type": "json_object"}
    }
    headers = {"Authorization": f"Bearer {ALIBABA_API_KEY}", "Content-Type": "application/json"}
    try:
        r = requests.post(QWEN_API_URL, headers=headers, json=payload, timeout=25)
        if r.status_code == 200:
            content = r.json()["choices"][0]["message"]["content"].strip()
            eval_data = json.loads(content)
            return (
                eval_data.get("bctc"), 
                eval_data.get("outlook"), 
                eval_data.get("recommendation"),
                eval_data.get("price_zone")
            )
    except Exception as e:
        print(f"  ⚠️ Lỗi AI {symbol}: {e}")
    return None, None, None, None

def main():
    data = {}
    symbols = sorted(set(VN100_SYMBOLS))
    total = len(symbols)
    updated = 0
    now_iso = time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime())

    print(f"🤖 Phân tích chỉ số & Cập nhật AI cho {total} mã...\n")

    for idx, symbol in enumerate(symbols, 1):
        industry = INDUSTRY_MAP.get(symbol, "VN100")
        
        # Lấy dữ liệu chỉ số
        print(f"[{idx}/{total}] Đang lấy dữ liệu {symbol}...")
        price, pe, pb, roe = fetch_data_for_ai(symbol)
        
        if price == 0:
            print(f"  ❌ Không lấy được dữ liệu {symbol}, bỏ qua.")
            continue

        print(f"  -> Giá: {price:,.0f} | P/E: {pe} | P/B: {pb} | ROE: {roe}%")
        
        bctc, outlook, recommendation, price_zone = get_ai_evaluation(symbol, industry, price, pe, pb, roe)
        
        if bctc and outlook:
            data[symbol] = {
                "symbol": symbol,
                "industry": industry,
                "bctc": bctc,
                "outlook": outlook,
                "recommendation": recommendation or "Chưa có",
                "price_zone": price_zone or "Chưa có",
                "ai_updated_at": now_iso
            }
            updated += 1
            print(f"  ✅ AI đã phân tích xong.")
        else:
            print(f"  ⏭️ AI lỗi, bỏ qua.")
        
        time.sleep(1.5) # Nghỉ lâu hơn do gọi proxy nhiều lần

    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

    # Ghi file gửi Telegram
    msg = f"🤖 <b>Báo cáo Phân tích AI (Dài hạn)</b>\n\n- Tổng số mã: {total}\n- Phân tích thành công: {updated}/{total} mã\n- Thời gian: {now_iso}"
    with open("telegram_msg.txt", "w", encoding="utf-8") as f:
        f.write(msg)

if __name__ == "__main__":
    main()
