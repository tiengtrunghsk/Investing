import os
import time
import requests
import re
import json

DATA_FILE = "data.json"

ALIBABA_API_KEY = os.getenv("ALIBABA_API_KEY", "").strip()
API_URL = "https://ws-8lcqaxwxdv0h9xzy.ap-southeast-1.maas.aliyuncs.com/compatible-mode/v1/chat/completions"

def check_if_analysis_needed(stock_db):
    """
    Kiểm tra tự động xem mã nào cần AI phân tích lại:
    - Chưa có phân tích AI.
    - Hoặc dữ liệu giá/thông số mới cào từ thị trường mới hơn thời điểm AI quét trước đó.
    """
    for symbol, data in stock_db.items():
        if data.get('close', 0) <= 0:
            continue
            
        updated_at = data.get("updated_at", "")
        ai_updated_at = data.get("ai_updated_at", "")
        ai_recommendation = data.get("ai_recommendation", "")
        
        if not ai_recommendation or not ai_updated_at or updated_at > ai_updated_at:
            return True
            
    return False

def analyze_stock_with_ai(symbol, data):
    if not ALIBABA_API_KEY:
        print(f"❌ LỖI: Biến môi trường ALIBABA_API_KEY đang bị trống!")
        return None

    # Prompt đỉnh cao: Kết hợp đặc thù ngành, vĩ mô toàn cầu và BẮT BUỘC DẪN CHỨNG TÊN DỰ ÁN THỰC TẾ
    prompt = f"""
    Bạn là một Chuyên gia Phân tích Tài chính Cấp cao kiêm Quản lý Quỹ Đầu tư (Portfolio Manager) xuất sắc. Hãy thực hiện một bản **đánh giá phân tích chiến lược chuyên sâu, đầy đủ ý và có dẫn chứng thực tế** đối với mã cổ phiếu: {symbol}.

    NGUYÊN TẮC BÓC TÁCH CHUYÊN SÂU & DẪN CHỨNG DỰ ÁN THỰC TẾ (BẮT BUỘC ÁP DỤNG):
    1. **Móc nối dự án thực tế đang triển khai:** 
       - Bạn **PHẢI GỌI TÊN CỤ THỂ CÁC DỰ ÁN TRỌNG ĐIỂM** mà doanh nghiệp này đang làm (ví dụ: các đại dự án BĐS, các gói thầu hạ tầng/đầu tư công lớn, các mỏ dầu khí/dự án điện, hay các khu công nghiệp mới) để làm bằng chứng thực tế cho luận điểm tăng trưởng.
       - Đánh giá rõ tiến độ pháp lý, thời điểm điểm rơi hạch toán doanh thu/lợi nhuận của từng dự án đó.
    2. **Đặc thù ngành & Định giá:** 
       - Ngân hàng (P/B, Nợ xấu, NIM); Chứng khoán (Tự doanh FVTPL, Margin); BĐS/Hạ tầng (Tiến độ dự án, Người mua trả tiền trước); Sản xuất/Thép (Hàng tồn kho, Giá hàng hóa thế giới).
    3. **Bối cảnh vĩ mô toàn cầu & Tiềm năng tương lai:** Gắn liền với lãi suất, tỷ giá USD/VND, chu kỳ hàng hóa thế giới, chiến tranh/địa chính trị và các xu hướng lớn (xe điện, năng lượng sạch, chuyển đổi số).

    DỮ LIỆU THỊ TRƯỜNG & TÀI CHÍNH HIỆN TẠI:
    - Giá đóng cửa hiện tại: {data.get('close', 0)} VNĐ | Khối lượng: {data.get('volume', 0)}
    - Chỉ số định giá cơ bản: P/E = {data.get('pe', 0)} | P/B = {data.get('pb', 0)}
    - Khả năng sinh lời: EPS = {data.get('eps', 0)} VNĐ | ROE = {data.get('roe', 0)}% | ROA = {data.get('roa', 0)}%
    - Cổ tức: {data.get('dividend_yield', 0)}%
    - Trạng thái kỹ thuật/nến thô: {data.get('recommendation', 'Chưa xác định')} | Vùng giá thô: {data.get('price_zone', 'Chưa có')}

    YÊU CẦU TRẢ VỀ BẢN PHÂN TÍCH CHI TIẾT (Dạng JSON thuần túy, tuyệt đối không dùng định dạng markdown như ```json):
    1. "bctc": Phân tích sức khỏe tài chính chiều sâu (Viết chi tiết từ 4-6 câu): Đánh giá cấu trúc vốn, đòn bẩy và chất lượng dòng tiền cốt lõi. **Phải lồng ghép dẫn chứng về các khoản người mua trả tiền trước hoặc vốn đầu tư đang đổ vào các dự án chính.**
    2. "outlook": Đánh giá triển vọng định giá và biên an toàn (Viết chi tiết từ 4-6 câu): Phân tích xem mức giá hiện tại so với giá trị thực tế của các dự án đang triển khai và hiệu quả sinh lời (ROE/ROA) đang là ĐẮT hay RẺ, đã có biên an toàn chưa?
    3. "recommendation": Đưa ra khuyến nghị hành động sắc bén, chuẩn mực của Quản lý quỹ (Ngắn gọn từ 3-6 từ, ví dụ: "Tích sản dài hạn giá hấp dẫn", "Định giá quá cao - Chờ chiết khấu", "Breakout dòng tiền lớn - Mua gia tăng").
    4. "price_zone": Vạch rõ chiến lược hành động giá chi tiết: Xác định rõ vùng giá gom hợp lý / vùng định giá rẻ, kèm theo mốc chặn lỗ hoặc điểm gia tăng tỷ trọng khi có dòng tiền lớn xác nhận.
    5. "macro_view": Phân tích bức tranh vĩ mô toàn cầu & triển vọng dự án tương lai (Viết chi tiết từ 5-7 câu): Đan xen hài hòa giữa vĩ mô hiện tại (lãi suất, tỷ giá, chu kỳ hàng hóa thế giới, địa chính trị) với **tầm nhìn từ tiến độ các dự án trọng điểm và xu hướng ngành** đang tác động trực tiếp ra sao đến dư địa tăng trưởng dài hạn của doanh nghiệp.

    BẮT BUỘC TRẢ VỀ ĐỐI TƯỢNG JSON THUẦN TÚY với các khóa chính xác: "bctc", "outlook", "recommendation", "price_zone", "macro_view".
    """

    headers = {
        "Authorization": f"Bearer {ALIBABA_API_KEY}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "model": "qwen-max",
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.2
    }

    try:
        response = requests.post(API_URL, headers=headers, json=payload, timeout=60)
        if response.status_code == 200:
            res_json = response.json()
            content = res_json["choices"][0]["message"]["content"].strip()
            # Làm sạch chuỗi phản hồi để đảm bảo load JSON an toàn tuyệt đối
            content = re.sub(r"^```json\s*", "", content)
            content = re.sub(r"^```\s*", "", content)
            content = re.sub(r"\s*```$", "", content)
            return json.loads(content)
        else:
            print(f"[{symbol}] Lỗi HTTP {response.status_code}: {response.text}")
    except Exception as e:
        print(f"[{symbol}] Lỗi phân tích từ AI: {e}")
    
    return None

def main():
    if not os.path.exists(DATA_FILE):
        print("❌ Không tìm thấy file data.json!")
        return

    with open(DATA_FILE, "r", encoding="utf-8") as f:
        stock_db = json.load(f)

    if not check_if_analysis_needed(stock_db):
        print("💤 Dữ liệu không thay đổi. Không cần gọi AI để tiết kiệm tài nguyên.")
        return

    print(f"🤖 Chuyên gia AI đang tiến hành viết bản phân tích chuyên sâu có dẫn chứng dự án thực tế...")
    count = 0
    
    for i, (symbol, data) in enumerate(stock_db.items()):
        if data.get('close', 0) <= 0:
            continue
            
        updated_at = data.get("updated_at", "")
        ai_updated_at = data.get("ai_updated_at", "")
        
        # Chỉ gọi AI khi chưa phân tích hoặc dữ liệu giá/cơ bản mới hơn lần quét trước
        if not data.get("ai_recommendation") or updated_at > ai_updated_at:
            print(f"[{i+1}/{len(stock_db)}] Đang phân tích chi tiết kèm dự án cho mã: {symbol}...")
            ai_result = analyze_stock_with_ai(symbol, data)
            
            if ai_result:
                data["bctc"] = ai_result.get("bctc", "")
                data["outlook"] = ai_result.get("outlook", "")
                data["ai_recommendation"] = ai_result.get("recommendation", "")
                data["ai_price_zone"] = ai_result.get("price_zone", "")
                data["macro_view"] = ai_result.get("macro_view", "")
                data["ai_updated_at"] = time.strftime("%Y-%m-%d %H:%M:%S")
                count += 1
                print(f"  -> ✅ Phân tích thành công")
            else:
                print(f"  -> ❌ Lỗi gọi AI, bỏ qua mã này")
            
            time.sleep(1.5)
        else:
            print(f"[{i+1}/{len(stock_db)}] Bỏ qua {symbol} (Đã có nhận định AI mới nhất)")

    if count > 0:
        with open(DATA_FILE, "w", encoding="utf-8") as f:
            json.dump(stock_db, f, ensure_ascii=False, indent=4)
        print(f"\n🎉 Hoàn thành! Đã cập nhật các bản phân tích chiến lược có dẫn chứng dự án cho {count} mã vào data.json.")
    else:
        print("\nℹ️ Không có dữ liệu mới cần chạy.")

if __name__ == "__main__":
    main()
