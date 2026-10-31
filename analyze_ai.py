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

    # Prompt chuyên sâu: Tự động đổi lăng kính phân tích tùy thuộc vào mô hình kinh doanh cốt lõi của từng doanh nghiệp
    prompt = f"""
    Bạn là một Chuyên gia Phân tích Tài chính Cấp cao kiêm Quản lý Quỹ Đầu tư (Portfolio Manager) xuất sắc. Hãy thực hiện một bản **đánh giá phân tích chiến lược chuyên sâu, bám sát bản chất kinh doanh cốt lõi** đối với mã cổ phiếu: {symbol}.

    NGUYÊN TẮC BÓC TÁCH ĐỘNG LỰC TĂNG TRƯỞNG CỐT LÕI THEO TỪNG MÔ HÌNH KINH DOANH:
    1. **Nếu là BẤT ĐỘNG SẢN / HẠ TẦNG / KHU CÔNG NGHIỆP:** 
       - Bắt buộc gọi tên các dự án trọng điểm đang triển khai, pháp lý, tiến độ giải phóng mặt bằng, quỹ đất gối đầu và khoản tiền "Người mua trả tiền trước".
    2. **Nếu là BÁN LẺ & TIÊU DÙNG:** 
       - Tập trung vào tốc độ mở rộng chuỗi cửa hàng, hiệu suất hoạt động trên mỗi điểm bán, biên lợi nhuận gộp và sức mua vĩ mô.
    3. **Nếu là SẢN XUẤT / THÉP / HÓA CHẤT / VẬT LIỆU:** 
       - Tập trung vào công suất nhà máy, chu kỳ vòng quay hàng tồn kho, biên lợi nhuận gộp và biến động giá nguyên liệu đầu vào trên thị trường thế giới.
    4. **Nếu là NGÂN HÀNG & CHỨNG KHOÁN:** 
       - Ngân hàng tập trung vào P/B, nợ xấu (NPL), NIM; Chứng khoán tập trung vào danh mục Tự doanh (FVTPL), dư nợ Margin và thị phần môi giới.
    5. **Nếu là ĐIỆN & NĂNG LƯỢNG / DẦU KHÍ:** 
       - Tập trung vào sản lượng phát điện, hiệu suất giàn khoan/khai thác, và giá dầu thô/khí thế giới.
    6. **Nếu là CÔNG NGHỆ:** 
       - Tập trung vào doanh thu dịch vụ công nghệ thị trường nước ngoài và biên lợi nhuận cao từ các hợp đồng lớn.

    BỐI CẢNH VĨ MÔ & TẦM NHÌN: Gắn liền với mặt bằng lãi suất, tỷ giá USD/VND, lạm phát và các xu hướng lớn (chuyển đổi số, năng lượng sạch, chuỗi cung ứng).

    DỮ LIỆU THỊ TRƯỜNG & TÀI CHÍNH HIỆN TẠI:
    - Giá đóng cửa hiện tại: {data.get('close', 0)} VNĐ | Khối lượng: {data.get('volume', 0)}
    - Chỉ số định giá cơ bản: P/E = {data.get('pe', 0)} | P/B = {data.get('pb', 0)}
    - Khả năng sinh lời: EPS = {data.get('eps', 0)} VNĐ | ROE = {data.get('roe', 0)}% | ROA = {data.get('roa', 0)}%
    - Cổ tức: {data.get('dividend_yield', 0)}%
    - Trạng thái kỹ thuật/nến thô: {data.get('recommendation', 'Chưa xác định')} | Vùng giá thô: {data.get('price_zone', 'Chưa có')}

    YÊU CẦU TRẢ VỀ BẢN PHÂN TÍCH CHI TIẾT (Dạng JSON thuần túy, tuyệt đối không dùng định dạng markdown như ```json):
    1. "bctc": Phân tích sức khỏe tài chính chiều sâu (Viết chi tiết từ 4-6 câu): Đánh giá cấu trúc vốn, đòn bẩy và chất lượng dòng tiền. **Phải xoáy sâu vào mảng kinh doanh cốt lõi phù hợp nhất với mô hình của doanh nghiệp này** (Ví dụ: Dự án/Người mua trả tiền trước với BĐS; Hàng tồn kho/Biên gộp với Sản xuất; Hoặc Mở rộng chuỗi với Bán lẻ).
    2. "outlook": Đánh giá triển vọng định giá và biên an toàn (Viết chi tiết từ 4-6 câu): Phân tích xem mức giá hiện tại so với giá trị thực tế của động lực kinh doanh chính đang là ĐẮT hay RẺ, đã có biên an toàn chưa?
    3. "recommendation": Đưa ra khuyến nghị hành động sắc bén, chuẩn mực của Quản lý quỹ (Ngắn gọn từ 3-6 từ, ví dụ: "Tích sản dài hạn giá hấp dẫn", "Định giá quá cao - Chờ chiết khấu", "Breakout dòng tiền lớn - Mua gia tăng").
    4. "price_zone": Vạch rõ chiến lược hành động giá chi tiết: Xác định rõ vùng giá gom hợp lý / vùng định giá rẻ, kèm theo mốc chặn lỗ hoặc điểm gia tăng tỷ trọng khi có dòng tiền lớn xác nhận.
    5. "macro_view": Phân tích bức tranh vĩ mô toàn cầu & triển vọng ngành tương lai (Viết chi tiết từ 5-7 câu): Đan xen hài hòa giữa vĩ mô hiện tại (lãi suất, tỷ giá, chu kỳ hàng hóa thế giới, địa chính trị) với **tầm nhìn từ mô hình kinh doanh và động lực cốt lõi** tác động trực tiếp ra sao đến dư địa tăng trưởng dài hạn của doanh nghiệp.

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

    print(f"🤖 Chuyên gia AI đang tiến hành viết bản phân tích chuyên sâu bám sát động lực cốt lõi của từng doanh nghiệp...")
    count = 0
    
    for i, (symbol, data) in enumerate(stock_db.items()):
        if data.get('close', 0) <= 0:
            continue
            
        updated_at = data.get("updated_at", "")
        ai_updated_at = data.get("ai_updated_at", "")
        
        # Chỉ gọi AI khi chưa phân tích hoặc dữ liệu giá/cơ bản mới hơn lần quét trước
        if not data.get("ai_recommendation") or updated_at > ai_updated_at:
            print(f"[{i+1}/{len(stock_db)}] Đang phân tích chiến lược cốt lõi cho mã: {symbol}...")
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
        print(f"\n🎉 Hoàn thành! Đã cập nhật bản phân tích chuyên sâu theo đúng bản chất từng ngành cho {count} mã vào data.json.")
    else:
        print("\nℹ️ Không có dữ liệu mới cần chạy.")

if __name__ == "__main__":
    main()
