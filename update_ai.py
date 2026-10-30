import json
import os
import time
import requests
import re

DATA_FILE = "data.json"
# Lấy API Key từ biến môi trường của GitHub Actions Secrets
API_KEY = os.getenv("AI_API_KEY", "") 
# Endpoint chuẩn tương thích OpenAI (Ví dụ: Qwen DashScope hoặc OpenAI, DeepSeek...)
API_URL = "https://dashscope-intl.aliyuncs.com/compatible-v1/chat/completions"

def analyze_stock_with_ai(symbol, data):
    if not API_KEY:
        print(f"⚠️ Chưa cấu hình AI_API_KEY. Bỏ qua phân tích AI cho {symbol}.")
        return None

    prompt = f"""
    Bạn là một chuyên gia phân tích định lượng (Quant Analyst) và định giá doanh nghiệp hàng đầu tại thị trường chứng khoán Việt Nam.
    Hãy phân tích mã cổ phiếu: {symbol} thuộc nhóm ngành: {data.get('industry', 'Khác')}.
    
    Dữ liệu thị trường hiện tại:
    - Giá hiện tại: {data.get('close', 0)} (nghìn đồng)
    - P/E: {data.get('pe', 0)}x
    - P/B: {data.get('pb', 0)}x
    - Tỷ suất cổ tức: {data.get('dividendYield', 0)}%

    Bối cảnh vĩ mô: Lãi suất ổn định, dòng tiền luân phiên chọn lọc các doanh nghiệp có nền tảng cơ bản tốt, định giá hấp dẫn và triển vọng tăng trưởng lợi nhuận rõ ràng.

    Yêu cầu: Hãy đóng vai chuyên gia, phân tích và trả về kết quả **BẮT BUỘC DƯỚI DẠNG MỘT ĐỐI TƯỢNG JSON THUẦN TÚY** (không kèm markdown như ```json, chỉ trả về chuỗi JSON hợp lệ) với các khóa (keys) chính xác sau đây:
    1. "bctc": Đánh giá ngắn gọn sức khỏe tài chính, chất lượng tài sản dựa trên định giá P/E, P/B (2 câu).
    2. "outlook": Triển vọng kinh doanh ngắn và trung hạn của ngành và doanh nghiệp (2 câu).
    3. "recommendation": Khuyến nghị đầu tư rõ ràng, chọn 1 trong các trạng thái: "MUA GOM", "TÍCH SẢN", "NẮM GIỮ", "CHỜ ĐỢI", "BÁN GIẢM".
    4. "price_zone": Định giá và đề xuất vùng giá mua gom hợp lý (Ví dụ: "Vùng gom: 20.0 - 22.0 đ").
    5. "macro_view": Tác động vĩ mô và dòng tiền đến nhóm ngành này (2 câu).
    """

    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "model": "qwen-max", # Hoặc model LLM bạn đang sử dụng
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.2
    }

    try:
        response = requests.post(API_URL, headers=headers, json=payload, timeout=40)
        if response.status_code == 200:
            res_json = response.json()
            content = res_json["choices"][0]["message"]["content"].strip()
            
            # Làm sạch chuỗi JSON nếu AI lỡ đính kèm markdown
            content = re.sub(r"^```json\s*", "", content)
            content = re.sub(r"^```\s*", "", content)
            content = re.sub(r"\s*```$", "", content)
            
            parsed_data = json.loads(content)
            return parsed_data
    except Exception as e:
        print(f"Lỗi AI phân tích mã {symbol}: {e}")
    
    return None

def main():
    if not os.path.exists(DATA_FILE):
        print("❌ Không tìm thấy file data.json!")
        return

    with open(DATA_FILE, "r", encoding="utf-8") as f:
        stock_db = json.load(f)

    print("🤖 Bắt đầu tiến trình AI định giá và đánh giá đầu tư cho danh mục...")

    count = 0
    for symbol, data in stock_db.items():
        print(f"Đang gọi AI xử lý mã: {symbol}...")
        ai_result = analyze_stock_with_ai(symbol, data)
        
        if ai_result:
            data["bctc"] = ai_result.get("bctc", data.get("bctc"))
            data["outlook"] = ai_result.get("outlook", data.get("outlook"))
            data["recommendation"] = ai_result.get("recommendation", data.get("recommendation"))
            data["price_zone"] = ai_result.get("price_zone", data.get("price_zone"))
            data["macro_view"] = ai_result.get("macro_view", data.get("macro_view"))
            count += 1
        
        time.sleep(0.5) # Tránh vượt quá giới hạn request (rate-limit) của API AI

    # Ghi đè kết quả đã có nhận định AI vào data.json
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(stock_db, f, ensure_ascii=False, indent=4)

    print(f"✅ Đã hoàn tất cập nhật phân tích AI cho {count} mã cổ phiếu vào data.json!")

if __name__ == "__main__":
    main()
