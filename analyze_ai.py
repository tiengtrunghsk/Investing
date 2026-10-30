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
    Kiểm tra xem có cần gọi API AI hay không:
    Cần chạy khi có ít nhất 1 mã cổ phiếu thỏa mãn:
    1. Chưa từng được AI phân tích (ai_updated_at bị trống/thiếu).
    2. Dữ liệu giá mới cào từ PC mới hơn lần phân tích AI gần nhất (updated_at > ai_updated_at).
    """
    for symbol, data in stock_db.items():
        if data.get('close', 0) <= 0:
            continue
            
        updated_at = data.get("updated_at", "")
        ai_updated_at = data.get("ai_updated_at", "")
        ai_recommendation = data.get("ai_recommendation", "")
        
        # Nếu chưa phân tích AI hoặc dữ liệu giá mới hơn thời điểm AI quét
        if not ai_recommendation or not ai_updated_at or updated_at > ai_updated_at:
            print(f"🔍 Phát hiện dữ liệu mới cần phân tích tại mã: {symbol}")
            return True
            
    return False

def analyze_stock_with_ai(symbol, data):
    if not ALIBABA_API_KEY:
        print(f"❌ LỖI: Biến ALIBABA_API_KEY đang bị trống!")
        return None

    prompt = f"""
    Bạn là một Chuyên gia Phân tích Đầu tư (Portfolio Manager) kết hợp cả trường phái Cơ bản (Fundamental) và Dòng tiền lớn (Smart Money / Price Action & Volume).
    Hãy phân tích toàn diện mã cổ phiếu: {symbol}.

    DỮ LIỆU ĐỊNH GIÁ & CƠ BẢN (Từ VNDirect):
    - P/E: {data.get('pe', 0)} | P/B: {data.get('pb', 0)}
    - EPS: {data.get('eps', 0)} VNĐ | ROE: {data.get('roe', 0)}% | ROA: {data.get('roa', 0)}%
    - Tỷ suất cổ tức: {data.get('dividend_yield', 0)}%

    DỮ LIỆU KỸ THUẬT (Price Action D1):
    - Giá hiện tại: {data.get('close', 0)} VNĐ
    - Khối lượng hiện tại: {data.get('volume', 0)}
    - Trạng thái nến: {data.get('recommendation', 'Chưa xác định')}
    - Phân tích VCP: {data.get('price_zone', 'Chưa có')}

    YÊU CẦU PHÂN TÍCH (Trả về JSON thuần túy):
    1. "bctc": Đánh giá sức khỏe doanh nghiệp dựa trên EPS, ROE, ROA. Doanh nghiệp có đủ nội lực để dòng tiền lớn nắm giữ dài hạn không? (2-3 câu).
    2. "outlook": Đánh giá mức độ hấp dẫn của định giá (P/E, P/B) kết hợp với trạng thái kỹ thuật hiện tại (Ví dụ: "Định giá P/E 8.x là hấp dẫn so với ngành, kết hợp nền giá đang cạn cung tạo điểm mua tốt").
    3. "recommendation": Chọn 1 trong các trạng thái chuẩn: "MUA TÍCH SẢN", "MUA BREAKOUT", "CHỜ TEST LẠI", "THEO DÕI THÊM", "BỎ QUA".
    4. "price_zone": Xác định rõ vùng nền giá tích lũy và điểm mua chuẩn (Ví dụ: "Mua tích lũy: 20.0 - 21.5 | Mua gia tăng khi Breakout > 23.5 kèm Vol lớn").
    5. "macro_view": Đánh giá vĩ mô và sóng ngành (Ngân hàng, BĐS, Thép...) xem có đang ủng hộ dòng tiền lớn nhập cuộc không? (2 câu).

    Yêu cầu trả về **BẮT BUỘC DƯỚI DẠNG MỘT ĐỐI TƯỢNG JSON THUẦN TÚY** (không markdown) với các khóa chính xác: "bctc", "outlook", "recommendation", "price_zone", "macro_view".
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
        response = requests.post(API_URL, headers=headers, json=payload, timeout=45)
        if response.status_code == 200:
            res_json = response.json()
            content = res_json["choices"][0]["message"]["content"].strip()
            content = re.sub(r"^```json\s*", "", content)
            content = re.sub(r"^```\s*", "", content)
            content = re.sub(r"\s*```$", "", content)
            return json.loads(content)
        else:
            print(f"[{symbol}] Lỗi HTTP {response.status_code}: {response.text}")
    except Exception as e:
        print(f"[{symbol}] Lỗi AI: {e}")
    
    return None

def main():
    if not os.path.exists(DATA_FILE):
        print("❌ Không tìm thấy file data.json! Bỏ qua phân tích.")
        return

    # Đọc dữ liệu gốc
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        stock_db = json.load(f)

    # Kiểm tra điều kiện trước khi chạy
    if not check_if_analysis_needed(stock_db):
        print("💤 Dữ liệu không thay đổi hoặc đã được phân tích mới nhất. Dừng lại để tiết kiệm API Alibaba!")
        return

    print(f"🤖 Bắt đầu Phân tích Toàn diện bằng AI cho các mã chưa có/có dữ liệu mới...")
    count = 0
    
    for i, (symbol, data) in enumerate(stock_db.items()):
        if data.get('close', 0) <= 0:
            continue
            
        updated_at = data.get("updated_at", "")
        ai_updated_at = data.get("ai_updated_at", "")
        
        # Chỉ gọi API cho mã nào chưa phân tích hoặc có dữ liệu mới hơn AI cũ
        if not data.get("ai_recommendation") or updated_at > ai_updated_at:
            print(f"[{i+1}/{len(stock_db)}] Đang xử lý AI cho: {symbol}...")
            ai_result = analyze_stock_with_ai(symbol, data)
            
            if ai_result:
                data["bctc"] = ai_result.get("bctc", "")
                data["outlook"] = ai_result.get("outlook", "")
                data["ai_recommendation"] = ai_result.get("recommendation", "")
                data["ai_price_zone"] = ai_result.get("price_zone", "")
                data["macro_view"] = ai_result.get("macro_view", "")
                data["ai_updated_at"] = time.strftime("%Y-%m-%d %H:%M:%S")
                count += 1
                print(f"  -> ✅ Thành công")
            else:
                print(f"  -> ❌ Thất bại (Bỏ qua)")
            
            time.sleep(1.2)
        else:
            print(f"[{i+1}/{len(stock_db)}] Bỏ qua {symbol} (Đã có phân tích AI mới nhất)")

    # Ghi lại file data.json
    if count > 0:
        with open(DATA_FILE, "w", encoding="utf-8") as f:
            json.dump(stock_db, f, ensure_ascii=False, indent=4)
        print(f"\n✅ Đã phân tích AI xong {count} mã! File data.json đã được cập nhật.")
    else:
        print("\nℹ️ Không có cập nhật mới nào được thực hiện.")

if __name__ == "__main__":
    main()
