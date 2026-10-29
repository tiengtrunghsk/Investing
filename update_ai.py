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

# Danh sách chuẩn rổ VN100
VN100_SYMBOLS = [
    "ACB", "ANV", "BAF", "BCM", "BID", "BMP", "BSI", "BSR", "BVH", "BWE", 
    "CII", "CMG", "CTD", "CTG", "CTR", "CTS", "DBC", "DCM", "DGC", "DGW", 
    "DIG", "DPM", "DSE", "DXG", "DXS", "EIB", "EVF", "FPT", "FRT", "FTS", 
    "GAS", "GEE", "GEX", "GMD", "GVR", "HAG", "HCM", "HDB", "HDC", "HDG", 
    "HHV", "HPG", "HSG", "HT1", "IMP", "KBC", "KDC", "KDH", "KOS", "LPB", 
    "MBB", "MCH", "MSB", "MSN", "MWG", "NAB", "NKG", "NLG", "NT2", "NVL", 
    "OCB", "PAN", "PC1", "PDR", "PHR", "PLX", "PNJ", "POW", "PPC", "PTB", 
    "PVD", "PVT", "REE", "SAB", "SBT", "SCS", "SHB", "SIP", "SJS", "SSB", 
    "SSI", "STB", "SZC", "TAL", "TCB", "TCH", "TCX", "TPB", "VCB", "VCG", 
    "VCI", "VCK", "VGC", "VHC", "VHM", "VIB", "VIC", "VIX", "VJC", "VND", 
    "VNM", "VPB", "VPI", "VPL", "VPX", "VRE", "VSC", "VTP"
]

# Bảng map nhóm ngành cho các mã trong VN100
INDUSTRY_MAP = {
    "ACB": "Ngân hàng", "ANV": "Thủy sản", "BAF": "Nông nghiệp", "BCM": "Bất động sản KCN", 
    "BID": "Ngân hàng", "BMP": "Nhựa & Vật liệu", "BSI": "Chứng khoán", "BSR": "Dầu khí", 
    "BVH": "Bảo hiểm", "BWE": "Tiện ích & Nước", "CII": "Hạ tầng & Xây dựng", "CMG": "Công nghệ thông tin", 
    "CTD": "Xây dựng", "CTG": "Ngân hàng", "CTR": "Công nghệ & Viettel", "CTS": "Chứng khoán", 
    "DBC": "Nông nghiệp & Thực phẩm", "DCM": "Phân bón & Hóa chất", "DGC": "Hóa chất", "DGW": "Bán lẻ", 
    "DIG": "Bất động sản", "DPM": "Phân bón & Hóa chất", "DSE": "Chứng khoán", "DXG": "Bất động sản", 
    "DXS": "Bất động sản", "EIB": "Ngân hàng", "EVF": "Tài chính", "FPT": "Công nghệ thông tin", 
    "FRT": "Bán lẻ", "FTS": "Chứng khoán", "GAS": "Dầu khí", "GEE": "Thiết bị điện", 
    "GEX": "Thiết bị điện & Công nghiệp", "GMD": "Logistics & Cảng biển", "GVR": "Cao su & Công nghiệp", 
    "HAG": "Nông nghiệp", "HCM": "Chứng khoán", "HDB": "Ngân hàng", "HDC": "Bất động sản", 
    "HDG": "Bất động sản & Năng lượng", "HHV": "Hạ tầng giao thông", "HPG": "Thép & Vật liệu", 
    "HSG": "Thép & Vật liệu", "HT1": "Vật liệu xây dựng", "IMP": "Dược phẩm", "KBC": "Bất động sản KCN", 
    "KDC": "Thực phẩm & Đồ uống", "KDH": "Bất động sản", "KOS": "Năng lượng & Hạ tầng", "LPB": "Ngân hàng", 
    "MBB": "Ngân hàng", "MCH": "Hàng tiêu dùng", "MSB": "Ngân hàng", "MSN": "Hàng tiêu dùng & Bán lẻ", 
    "MWG": "Bán lẻ", "NAB": "Ngân hàng", "NKG": "Thép & Vật liệu", "NLG": "Bất động sản", 
    "NT2": "Điện & Năng lượng", "NVL": "Bất động sản", "OCB": "Ngân hàng", "PAN": "Nông nghiệp & Thực phẩm", 
    "PC1": "Xây lắp điện & Năng lượng", "PDR": "Bất động sản", "PHR": "Cao su", "PLX": "Xăng dầu & Dầu khí", 
    "PNJ": "Bán lẻ trang sức", "POW": "Điện & Năng lượng", "PPC": "Điện & Năng lượng", "PTB": "Đá mỹ nghệ & Gỗ", 
    "PVD": "Dầu khí", "PVT": "Vận tải biển & Dầu khí", "REE": "Cơ điện lạnh & Năng lượng", "SAB": "Đồ uống", 
    "SBT": "Nông nghiệp & Thực phẩm", "SCS": "Logistics & Hàng hóa", "SHB": "Ngân hàng", "SIP": "Bất động sản KCN", 
    "SJS": "Bất động sản", "SSB": "Ngân hàng", "SSI": "Chứng khoán", "STB": "Ngân hàng", 
    "SZC": "Bất động sản KCN", "TAL": "Bất động sản", "TCB": "Ngân hàng", "TCH": "Bất động sản & Tài chính", 
    "TCX": "Chứng khoán", "TPB": "Ngân hàng", "VCB": "Ngân hàng", "VCG": "Xây dựng & Bất động sản", 
    "VCI": "Chứng khoán", "VCK": "Chứng khoán", "VGC": "Vật liệu xây dựng & KCN", "VHC": "Thủy sản", 
    "VHM": "Bất động sản", "VIB": "Ngân hàng", "VIC": "Bất động sản & Đa ngành", "VIX": "Chứng khoán", 
    "VJC": "Hàng không", "VND": "Chứng khoán", "VNM": "Thực phẩm & Sữa", "VPB": "Ngân hàng", 
    "VPI": "Bất động sản", "VPL": "Dịch vụ du lịch & Nghỉ dưỡng", "VPX": "Chứng khoán", "VRE": "Bất động sản bán lẻ", 
    "VSC": "Logistics & Cảng biển", "VTP": "Bưu chính Viettel"
}

def fetch_via_proxy(url, params):
    req = requests.Request('GET', url, params=params).prepare()
    proxy_url = PROXY_PREFIX + quote(req.url, safe='')
    try:
        r = requests.get(proxy_url, headers={"User-Agent": "Mozilla/5.0"}, timeout=15)
        if r.status_code == 200:
            return r.json()
    except Exception as e:
        print(f"    ⚠️ Lỗi kết nối proxy: {e}")
    return None

def fetch_data_for_ai(symbol):
    """Lấy Giá, P/E, P/B, ROE thực tế để đưa cho AI phân tích"""
    now = int(time.time())
    params_price = {"resolution": "D", "symbol": symbol, "from": now - 30 * 86400, "to": now}
    price_data = fetch_via_proxy(RAW_DCHART_URL, params_price)
    
    current_price = 0
    try:
        if price_data and price_data.get("s") == "ok" and price_data.get("c"):
            current_price = price_data["c"][-1]
    except (IndexError, KeyError):
        current_price = 0
    
    def get_ratio(code):
        params = {"q": f"code:{symbol}~ratioCode:{code}", "size": 1, "sort": "reportDate:desc"}
        data = fetch_via_proxy(RAW_FUNDAMENTAL_URL, params)
        try:
            if data and data.get("data") and len(data["data"]) > 0:
                val = data["data"][0].get("value")
                return float(val) if val is not None else 0.0
        except Exception:
            pass
        return 0.0

    pe = get_ratio("PRICE_TO_EARNINGS")
    pb = get_ratio("PRICE_TO_BOOK")
    roe = get_ratio("ROAE_TR_AVG5Q")
    
    return current_price, pe, pb, roe

def get_ai_evaluation(symbol, industry, price, pe, pb, roe):
    if not ALIBABA_API_KEY:
        print("  ❌ Thiếu ALIBABA_API_KEY trong môi trường.")
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
            
            if content.startswith("```"):
                content = content.split("```")[1]
                if content.startswith("json"):
                    content = content[4:].strip()
                content = content.strip("`").strip()
                
            eval_data = json.loads(content)
            return (
                eval_data.get("bctc"), 
                eval_data.get("outlook"), 
                eval_data.get("recommendation"),
                eval_data.get("price_zone")
            )
        else:
            print(f"  ⚠️ Lỗi Qwen API ({r.status_code}): {r.text}")
    except Exception as e:
        print(f"  ⚠️ Lỗi xử lý AI cho {symbol}: {e}")
        
    return None, None, None, None

def main():
    data = {}
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception:
            data = {}

    symbols = sorted(set(VN100_SYMBOLS))
    total = len(symbols)
    updated = 0
    now_iso = time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime())

    print(f"🤖 Bắt đầu phân tích chỉ số & Cập nhật AI cho {total} mã...\n")

    for idx, symbol in enumerate(symbols, 1):
        industry = INDUSTRY_MAP.get(symbol, "VN100")
        
        print(f"[{idx}/{total}] Đang lấy dữ liệu {symbol}...")
        price, pe, pb, roe = fetch_data_for_ai(symbol)
        
        if price == 0:
            print(f"  ❌ Không lấy được giá {symbol}, bỏ qua.")
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
            print(f"  ✅ AI đã phân tích xong {symbol}.")
        else:
            print(f"  ⏭️ Bỏ qua do AI gặp lỗi.")
        
        with open(DATA_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=4)
            
        time.sleep(2)

    msg = f"🤖 <b>Báo cáo Phân tích AI (Dài hạn)</b>\n\n- Tổng số mã: {total}\n- Cập nhật thành công: {updated}/{total} mã\n- Thời gian: {now_iso}"
    with open("telegram_msg.txt", "w", encoding="utf-8") as f:
        f.write(msg)
        
    print("\n✨ Hoàn tất tiến trình!")

if __name__ == "__main__":
    main()
