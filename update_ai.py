import os
import json
import time
import requests

DATA_FILE = "data.json"
ALIBABA_API_KEY = os.environ.get("ALIBABA_API_KEY")
QWEN_API_URL = "https://dashscope-intl.aliyuncs.com/compatible-mode/v1/chat/completions"

def get_ai_evaluation(symbol, industry, price, pe, pb, roe):
    if not ALIBABA_API_KEY:
        print("  ❌ Thiếu ALIBABA_API_KEY trong môi trường.")
        return None, None, None, None

    prompt = f"""Bạn là một chuyên gia đầu tư giá trị (Value Investor) tại Việt Nam.
Hãy phân tích cổ phiếu {symbol} thuộc nhóm ngành {industry}.
Dưới đây là DỮ LIỆU TÀI CHÍNH hiện tại:
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
    # 1. Kiểm tra xem file data.json có tồn tại không
    if not os.path.exists(DATA_FILE):
        print(f"❌ Không tìm thấy file {DATA_FILE}. Vui lòng đảm bảo file dữ liệu đã tồn tại.")
        return

    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception as e:
        print(f"❌ Lỗi đọc file {DATA_FILE}: {e}")
        return

    total = len(data)
    if total == 0:
        print("⚠️ File data.json trống không có mã nào.")
        return

    updated = 0
    now_iso = time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime())

    print(f"🤖 Bắt đầu dùng AI phân tích lại dựa trên dữ liệu sẵn có trong {DATA_FILE} ({total} mã)...\n")

    # Duyệt qua từng mã đã lưu trong JSON
    for idx, (symbol, info) in enumerate(list(data.items()), 1):
        industry = info.get("industry", "VN100")
        
        # Cố gắng bóc tách giá và các chỉ số từ dữ liệu cũ (nếu có lưu hoặc bạn lưu thêm)
        # Hoặc nếu trong JSON chỉ lưu các trường cũ, ta có thể dùng giá trị mặc định / đọc từ cấu trúc cũ.
        # Ở đây giả định file json của bạn lưu cấu trúc có sẵn, ví dụ chúng ta cần thêm trường giá/pe/pb/roe nếu có, 
        # hoặc nếu file JSON của bạn chỉ có kết quả AI cũ, ta cần bổ sung nguồn giá.
        
        print(f"[{idx}/{total}] Đang xử lý mã {symbol} ({industry})...")
        
        # Lấy các thông số sẵn có từ cấu trúc JSON cũ (nếu bạn có lưu giá/pe/pb trong đó)
        # Nếu file json của bạn chưa lưu giá, bạn có thể bổ sung. Dưới đây lấy mẫu từ info:
        price = info.get("price", 0)
        pe = info.get("pe", 0)
        pb = info.get("pb", 0)
        roe = info.get("roe", 0)

        # Gọi AI phân tích lại
        bctc, outlook, recommendation, price_zone = get_ai_evaluation(symbol, industry, price, pe, pb, roe)
        
        if bctc and outlook:
            data[symbol].update({
                "bctc": bctc,
                "outlook": outlook,
                "recommendation": recommendation or "Chưa có",
                "price_zone": price_zone or "Chưa có",
                "ai_updated_at": now_iso
            })
            updated += 1
            print(f"  ✅ Đã cập nhật xong AI cho {symbol}.")
        else:
            print(f"  ⏭️ Bỏ qua do AI gặp lỗi.")
        
        # Lưu đệm liên tục
        with open(DATA_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=4)
            
        time.sleep(1.5)

    # Ghi file thông báo cho Telegram
    msg = f"🤖 <b>Báo cáo Phân tích AI (Từ dữ liệu JSON)</b>\n\n- Tổng số mã: {total}\n- Cập nhật thành công: {updated}/{total} mã\n- Thời gian: {now_iso}"
    with open("telegram_msg.txt", "w", encoding="utf-8") as f:
        f.write(msg)
        
    print("\n✨ Hoàn tất tiến trình cập nhật từ JSON!")

if __name__ == "__main__":
    main()
