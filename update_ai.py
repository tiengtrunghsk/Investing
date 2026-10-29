import os
import json
import time
import requests
from urllib.parse import quote

DATA_FILE = "data.json"
ALIBABA_API_KEY = os.environ.get("ALIBABA_API_KEY")
QWEN_API_URL = "https://dashscope-intl.aliyuncs.com/compatible-mode/v1/chat/completions"

# Sử dụng Proxy để lấy giá và chỉ số
PROXY_PREFIX = "https://corsproxy.io/?url="
RAW_DCHART_URL = "https://dchart-api.vndirect.com.vn/dchart/history"
RAW_FUNDAMENTAL_URL = "https://api-finfo.vndirect.com.vn/v4/ratios"

VN100_SYMBOLS = [
    "VCB", "BID", "CTG", "TCB", "MBB", "ACB", "STB", "VPB", "HDB", "VIB", "TPB", "SHB", "SSB", "LPB", "MSB", "OCB", "EIB",
    "SSI", "VCI", "HCM", "VIX", "MBS", "FTS", "BSI", "CTS", "ORS",
    "VHM", "VIC", "VRE", "NVL", "PDR", "DIG", "NLG", "KDH", "CEO", "DXG", "TCH", "SJS", "HDG", "KBC", "IDC", "SZC", "BCM", "PHR",
    "HPG", "HSG", "NKG", "VLB", "CTD", "HBC", "VCG", "HHV", "C4G",
    "FPT", "MWG", "PNJ", "FRT", "VNM", "MSN", "DGW", "SAB", "BHN", "KDC", "PET",
    "GAS", "POW", "BSR", "PVD", "PVS", "DGC", "DCM", "DPM", "GEG", "REE", "PC1", "NT2",
    "GMD", "HAH", "VJC", "HVN", "PVT", "VSC",
    "VHC", "ANV", "DAB", "PAN", "BAF"
]

INDUSTRY_MAP = {
    "VCB": "Ngân hàng", "BID": "Ngân hàng", "CTG": "Ngân hàng", "TCB": "Ngân hàng", "MBB": "Ngân hàng",
    "ACB": "Ngân hàng", "STB": "Ngân hàng", "VPB": "Ngân hàng", "HDB": "Ngân hàng", "VIB": "Ngân hàng",
    "TPB": "Ngân hàng", "SHB": "Ngân hàng", "SSB": "Ngân hàng", "LPB": "Ngân hàng", "MSB": "Ngân hàng",
    "OCB": "Ngân hàng", "EIB": "Ngân hàng", "SSI": "Chứng khoán", "VCI": "Chứng khoán", "HCM": "Chứng khoán",
    "VIX": "Chứng khoán", "MBS": "Chứng khoán", "FTS": "Chứng khoán", "BSI": "Chứng khoán", "CTS": "Chứng khoán", "ORS": "Chứng khoán",
    "VHM": "Bất động sản", "VIC": "Bất động sản", "VRE": "Bất động sản", "NVL": "Bất động sản",
    "PDR": "Bất động sản", "DIG": "Bất động sản", "NLG": "Bất động sản", "KDH": "Bất động sản",
    "CEO": "Bất động sản", "DXG": "Bất động sản", "TCH": "Bất động sản", "HDG": "Bất động sản",
    "KBC": "BĐS Khu công nghiệp", "IDC": "BĐS Khu công nghiệp", "SZC": "BĐS Khu công nghiệp",
    "BCM": "BĐS Khu công nghiệp", "PHR": "BĐS Khu công nghiệp", "HPG": "Thép & VLXD", "HSG": "Thép & VLXD",
    "NKG": "Thép & VLXD", "VLB": "Thép & VLXD", "CTD": "Xây dựng", "VCG": "Xây dựng", "HHV": "Xây dựng", "C4G": "Xây dựng",
    "FPT": "Công nghệ", "MWG": "Bán lẻ", "PNJ": "Bán lẻ", "FRT": "Bán lẻ", "DGW": "Bán lẻ",
    "VNM": "Tiêu dùng", "MSN": "Tiêu dùng", "SAB": "Tiêu dùng", "GAS": "Dầu khí", "PVD": "Dầu khí",
    "PVS": "Dầu khí", "BSR": "Dầu khí", "POW": "Năng lượng", "REE": "Năng lượng", "PC1": "Năng lượng",
    "NT2": "Năng lượng", "DGC": "Hóa chất", "DCM": "Phân bón", "DPM": "Phân bón",
    "GMD": "Cảng biển & Logistics", "HAH": "Cảng biển & Logistics", "PVT": "Vận tải biển",
    "VJC": "Hàng không", "HVN": "Hàng không", "VHC": "Thủy sản", "ANV": "Thủy sản", "DAB": "Nông nghiệp"
}

def fetch_via_proxy(url, params):
    req = requests.Request('GET', url, params=params).prepare()
    proxy_url = PROXY_PREFIX + quote(req.url, safe='')
    try:
        r = requests.get(proxy_url, headers={"User-Agent": "Mozilla/5.0"}, timeout=15)
        if r.status_code == 200: return r.json()
    except Exception: pass
    return None

def fetch_data_for_ai(symbol):
    now = int(time.time())
    params_price = {"resolution": "D", "symbol": symbol, "from": now - 30 * 86400, "to": now}
    price_data = fetch_via_proxy(RAW_DCHART_URL, params_price)
    current_price = price_data["c"][-1] if (price_data and price_data.get("s") == "ok") else 0
    
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
        return None, None, None, None, None

    prompt = f"""Bạn là một Giám đốc Đầu tư (CIO) tại Việt Nam, có tầm nhìn vĩ mô và chiến lược đầu tư giá trị dài hạn.
Hãy phân tích cổ phiếu {symbol} thuộc nhóm ngành {industry}.
DỮ LIỆU THỰC TẾ HIỆN TẠI:
- Giá: {price:,.0f} VNĐ
- P/E: {pe}
- P/B: {pb}
- ROE: {roe}%

Dựa vào các CHỈ SỐ trên và BỐI CẢNH VĨ MÔ VIỆT NAM (lãi suất đang ở mức thấp, chính sách hỗ trợ tăng trưởng, đầu tư công...), hãy đưa ra đánh giá.
Trả về DUY NHẤT JSON thuần túy (không markdown) gồm 5 trường:
1. "bctc": Nhận xét sức khỏe tài chính, tối đa 40 từ.
2. "outlook": Triển vọng 1-3 năm tới của doanh nghiệp, tối đa 40 từ.
3. "recommendation": Chỉ chọn 1 trong các từ ("GOM TÍCH SẢN", "NẮM GIỮ CHẶT", "CHỜ ĐỢI", "HẠ TỶ TRỌNG") kèm 1 câu lý do dựa trên định giá.
4. "buy_zone": Đưa ra VÙNG MUA CỤ THỂ dựa trên giá {price:,.0f} VNĐ. VD: "Mua tích lũy 30% vị thế ở vùng 40.000 - 42.000. Mua thêm nếu về 38.000."
5. "macro_view": Phân tích bối cảnh VĨ MÔ ảnh hưởng đến mã này. Nên mua khi lãi suất/chính sách thế nào? (VD: "Hưởng lợi lớn khi lãi suất duy trì thấp và chính sách đẩy mạnh đầu tư công. Canh mua khi Fed hạ lãi suất.")
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
                eval_data.get("buy_zone"),
                eval_data.get("macro_view")
            )
    except Exception as e:
        print(f"  ⚠️ Lỗi AI {symbol}: {e}")
    return None, None, None, None, None

def main():
    data = {}
    symbols = sorted(set(VN100_SYMBOLS))
    total = len(symbols)
    updated = 0
    now_iso = time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime())

    print(f"🤖 Phân tích Vĩ mô & Chỉ số cho {total} mã...\n")

    for idx, symbol in enumerate(symbols, 1):
        industry = INDUSTRY_MAP.get(symbol, "VN100")
        
        print(f"[{idx}/{total}] Đang lấy dữ liệu {symbol}...")
        price, pe, pb, roe = fetch_data_for_ai(symbol)
        
        if price == 0:
            print(f"  ❌ Không lấy được dữ liệu {symbol}, bỏ qua.")
            continue

        bctc, outlook, recommendation, buy_zone, macro_view = get_ai_evaluation(symbol, industry, price, pe, pb, roe)
        
        if bctc and outlook:
            data[symbol] = {
                "symbol": symbol,
                "industry": industry,
                "bctc": bctc,
                "outlook": outlook,
                "recommendation": recommendation or "Chưa có",
                "price_zone": buy_zone or "Chưa có vùng giá",
                "macro_view": macro_view or "Chưa có phân tích vĩ mô",
                "ai_updated_at": now_iso
            }
            updated += 1
            print(f"  ✅ AI đã phân tích xong.")
        else:
            print(f"  ⏭️ AI lỗi, bỏ qua.")
        
        time.sleep(1.0)

    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

    # Ghi file gửi Telegram
    msg = f"🤖 <b>Báo cáo Phân tích AI (Dài hạn)</b>\n\n- Tổng số mã: {total}\n- Phân tích thành công: {updated}/{total} mã\n- Thời gian: {now_iso}"
    with open("telegram_msg.txt", "w", encoding="utf-8") as f:
        f.write(msg)

if __name__ == "__main__":
    main()
