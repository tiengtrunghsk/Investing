import os
import json
import time
import requests

DATA_FILE = "data.json"
ALIBABA_API_KEY = os.environ.get("ALIBABA_API_KEY")
QWEN_API_URL = "https://dashscope-intl.aliyuncs.com/compatible-mode/v1/chat/completions"

# API TCBS (Không chặn IP GitHub, không cần Proxy)
TCBS_PRICE_URL = "https://apipubaws.tcbs.com.vn/stock-insight/v1/stock/price-board?ticker={symbol}"
TCBS_RATIO_URL = "https://apipubaws.tcbs.com.vn/tcanalysis/v1/finance/ratio?ticker={symbol}"

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

def fetch_tcbs_data(symbol):
    """Lấy Giá, P/E, P/B, ROE trực tiếp từ API TCBS"""
    price = 0
    pe, pb, roe = 0, 0, 0
    
    headers = {"User-Agent": "Mozilla/5.0"}
    
    # 1. Lấy Giá
    try:
        r_price = requests.get(TCBS_PRICE_URL.format(symbol=symbol), headers=headers, timeout=10)
        if r_price.status_code == 200:
            data = r_price.json().get("data", [])
            if data:
                # TCBS trả về matchPrice (giá khớp) hoặc refPrice (giá tham chiếu)
                price = data[0].get("matchPrice", 0) or data[0].get("refPrice", 0)
    except Exception as e:
        print(f"  ⚠️ Lỗi lấy giá {symbol}: {e}")

    # 2. Lấy P/E, P/B, ROE
    try:
        r_ratio = requests.get(TCBS_RATIO_URL.format(symbol=symbol), headers=headers, timeout=10)
        if r_ratio.status_code == 200:
            data = r_ratio.json().get("data", [])
            if data:
                ratio_data = data[0]
                pe = ratio_data.get("priceToEarning", 0) or 0
                pb = ratio_data.get("priceToBook", 0) or 0
                roe = ratio_data.get("roe", 0) or 0
                
                # Sửa lỗi đơn vị ROE (nếu TCBS trả về 0.2 thì đổi thành 20%)
                if 0 < roe < 1:
                    roe *= 100
    except Exception as e:
        print(f"  ⚠️ Lỗi lấy chỉ số {symbol}: {e}")

    return price, pe, pb, roe

def get_ai_evaluation(symbol, industry, price, pe, pb, roe):
    if not ALIBABA_API_KEY:
        return None, None, None, None, None

    # Xử lý hiển thị số liệu cho đẹp (nếu bằng 0 thì hiển thị N/A)
    pe_str = f"{pe:.1f}" if pe else "N/A"
    pb_str = f"{pb:.1f}" if pb else "N/A"
    roe_str = f"{roe:.1f}" if roe else "N/A"

    prompt = f"""Bạn là một Giám đốc Đầu tư (CIO) tại Việt Nam, có tầm nhìn vĩ mô và chiến lược đầu tư giá trị dài hạn.
Hãy phân tích cổ phiếu {symbol} thuộc nhóm ngành {industry}.
DỮ LIỆU THỰC TẾ HIỆN TẠI:
- Giá: {price:,.0f} VNĐ
- P/E: {pe_str}
- P/B: {pb_str}
- ROE: {roe_str}%

Dựa vào các CHỈ SỐ trên và BỐI CẢNH VĨ MÔ VIỆT NAM (lãi suất đang ở mức thấp, chính sách hỗ trợ tăng trưởng, đầu tư công...), hãy đưa ra đánh giá.
Trả về DUY NHẤT JSON thuần túy (không markdown) gồm 5 trường:
1. "bctc": Nhận xét sức khỏe tài chính, tối đa 40 từ.
2. "outlook": Triển vọng 1-3 năm tới của doanh nghiệp, tối đa 40 từ.
3. "recommendation": Chỉ chọn 1 trong các từ ("GOM TÍCH SẢN", "NẮM GIỮ CHẶT", "CHỜ ĐỢI", "HẠ TỶ TRỌNG") kèm 1 câu lý do dựa trên định giá.
4. "buy_zone": Đưa ra VÙNG MUA CỤ THỂ dựa trên giá {price:,.0f} VNĐ. VD: "Mua tích lũy 30% vị thế ở vùng 40.000 - 42.000. Mua thêm nếu về 38.000."
5. "macro_view": Phân tích bối cảnh VĨ MÔ ảnh hưởng đến mã này. Nên mua khi lãi suất/chính sách thế nào? (VD: "Hưởng lợi lớn khi lãi suất duy trì thấp và chính sách đẩy mạnh đầu tư công.")
"""
    payload = {
        "model": "qwen-plus",
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.3,
        "response_format": {"type": "json_object"}
    }
    headers = {"Authorization": f"Bearer {ALIBABA_API_KEY}", "Content-Type": "application/json"}
    
    try:
        r = requests.post(QWEN_API_URL, headers=headers, json=payload, timeout=30)
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
        else:
            print(f"  ⚠️ Lỗi Qwen API {symbol} (HTTP {r.status_code}): {r.text[:100]}")
    except Exception as e:
        print(f"  ⚠️ Lỗi gọi AI {symbol}: {e}")
        
    return None, None, None, None, None

def main():
    data = {}
    symbols = sorted(set(VN100_SYMBOLS))
    total = len(symbols)
    updated = 0
    now_iso = time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime())

    print(f"🤖 Lấy dữ liệu từ TCBS & Phân tích AI cho {total} mã...\n")

    for idx, symbol in enumerate(symbols, 1):
        industry = INDUSTRY_MAP.get(symbol, "VN100")
        
        print(f"[{idx}/{total}] Đang xử lý {symbol}...")
        price, pe, pb, roe = fetch_tcbs_data(symbol)
        
        if price == 0:
            print(f"  ❌ Không lấy được giá {symbol}, bỏ qua.")
            continue

        print(f"  -> Giá: {price:,.0f} | P/E: {pe:.1f} | P/B: {pb:.1f} | ROE: {roe:.1f}%")
        
        bctc, outlook, recommendation, buy_zone, macro_view = get_ai_evaluation(symbol, industry, price, pe, pb, roe)
        
        # Lưu dữ liệu (kể cả khi AI lỗi thì vẫn lưu giá & chỉ số)
        data[symbol] = {
            "symbol": symbol,
            "industry": industry,
            "close": price,
            "pe": pe,
            "pb": pb,
            "roe": roe,
            "bctc": bctc or "Chưa có đánh giá",
            "outlook": outlook or "Chưa có triển vọng",
            "recommendation": recommendation or "Chờ AI cập nhật",
            "price_zone": buy_zone or "Chưa có vùng giá",
            "macro_view": macro_view or "Chưa có phân tích vĩ mô",
            "ai_updated_at": now_iso if (bctc and outlook) else None
        }
        
        if bctc and outlook:
            updated += 1
            print(f"  ✅ AI đã phân tích xong.")
        else:
            print(f"  ⏭️ AI lỗi, chỉ lưu dữ liệu giá.")
        
        time.sleep(1.0)

    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

    msg = f"🤖 <b>Báo cáo Phân tích AI (Dài hạn)</b>\n\n- Tổng số mã: {total}\n- Cập nhật dữ liệu giá: {len(data)} mã\n- Phân tích AI thành công: {updated} mã\n- Thời gian: {now_iso}"
    with open("telegram_msg.txt", "w", encoding="utf-8") as f:
        f.write(msg)

    print(f"\n✅ Hoàn tất! Đã lưu {len(data)} mã vào {DATA_FILE}")

if __name__ == "__main__":
    main()
