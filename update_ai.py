import os
import json
import time
import requests

DATA_FILE = "data.json"
ALIBABA_API_KEY = os.environ.get("ALIBABA_API_KEY")
QWEN_API_URL = "https://dashscope-intl.aliyuncs.com/compatible-mode/v1/chat/completions"

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

def get_ai_evaluation(symbol, industry):
    if not ALIBABA_API_KEY:
        return None, None

    prompt = f"""Bạn là chuyên gia phân tích tài chính chứng khoán Việt Nam.
Phân tích cổ phiếu {symbol} thuộc nhóm ngành {industry}.
Trả về DUY NHẤT JSON thuần túy (không markdown) gồm 2 trường:
1. "bctc": Tóm tắt sức khỏe BCTC/tài chính, tối đa 40 từ.
2. "outlook": Triển vọng đầu tư ngắn & dài hạn, tối đa 40 từ.
"""
    payload = {
        "model": "qwen-plus",
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.2,
        "response_format": {"type": "json_object"}
    }
    headers = {"Authorization": f"Bearer {ALIBABA_API_KEY}", "Content-Type": "application/json"}
    try:
        r = requests.post(QWEN_API_URL, headers=headers, json=payload, timeout=25)
        if r.status_code == 200:
            content = r.json()["choices"][0]["message"]["content"].strip()
            eval_data = json.loads(content)
            return eval_data.get("bctc"), eval_data.get("outlook")
    except Exception as e:
        print(f"  ⚠️ Lỗi AI {symbol}: {e}")
    return None, None

def main():
    data = {}
    symbols = sorted(set(VN100_SYMBOLS))
    total = len(symbols)
    updated = 0
    now_iso = time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime())

    print(f"🤖 Cập nhật đánh giá AI cho {total} mã...\n")

    for idx, symbol in enumerate(symbols, 1):
        industry = INDUSTRY_MAP.get(symbol, "VN100")
        print(f"[{idx}/{total}] {symbol} ({industry})")
        
        bctc, outlook = get_ai_evaluation(symbol, industry)
        
        if bctc and outlook:
            data[symbol] = {
                "symbol": symbol,
                "industry": industry,
                "bctc": bctc,
                "outlook": outlook,
                "ai_updated_at": now_iso
            }
            updated += 1
            print(f"  ✅ AI cập nhật")
        else:
            print(f"  ⏭️ Bỏ qua")
        
        time.sleep(0.3)

    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

    msg = f"🤖 <b>Cập nhật Đánh giá AI (Qwen)</b>\n\n- Tổng số mã: {total}\n- Cập nhật thành công: {updated}/{total} mã\n- Thời gian: {now_iso}\n- Trạng thái: Thành công ✅"
    with open("telegram_msg.txt", "w", encoding="utf-8") as f:
        f.write(msg)

    print(f"\n✅ Hoàn tất! Đã cập nhật AI cho {updated}/{total} mã.")

if __name__ == "__main__":
    main()
