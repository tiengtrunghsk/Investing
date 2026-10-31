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

    # Prompt hoàn toàn mở, để AI tự do phân tích toàn diện định giá đắt/rẻ và kỹ thuật không qua bất kỳ ràng buộc cứng nào
    prompt = f"""
    Bạn là một Chuyên gia Quản lý Quỹ Đầu tư (Portfolio Manager) hàng đầu. Hãy dùng toàn bộ tư duy tài chính, kinh tế vĩ mô và phân tích kỹ thuật của bạn để đánh giá toàn diện mã cổ phiếu: {symbol}.

    DỮ LIỆU THỊ TRƯỜNG & TÀI CHÍNH HIỆN TẠI:
    - Giá đóng cửa hiện tại: {data.get('close', 0)} VNĐ
    - Khối lượng giao dịch: {data.get('volume', 0)}
    - Chỉ số định giá cơ bản: P/E = {data.get('pe', 0)} | P/B = {data.get('pb', 0)}
    - Khả năng sinh lời: EPS = {data.get('eps', 0)} VNĐ | ROE = {data.get('roe', 0)}% | ROA = {data.get('roa', 0)}%
    - Cổ tức: {data.get('dividend_yield', 0)}%
    - Trạng thái nến/kỹ thuật thô: {data.get('recommendation', 'Chưa xác định')}
    - Vùng giá/VCP thô: {data.get('price_zone', 'Chưa có')}

    YÊU CẦU PHÂN TÍCH (Trả về JSON thuần túy, không định dạng markdown):
    1. "bctc": Đánh giá sức khỏe tài chính và chất lượng nội tại của doanh nghiệp dựa trên các con số trên. (2-3 câu).
    2. "outlook": Phân tích chuyên sâu xem **mức giá hiện tại đang ĐẮT hay RẺ**, có biên an toàn chưa, dựa trên P/E, P/B so với hiệu quả sinh lời ROE. (2-3 câu).
    3. "recommendation": Đưa ra quyết định đầu tư thuần túy từ AI, chọn 1 trong các trạng thái: "MUA TÍCH SẢN", "MUA BREAKOUT", "CHỜ TEST LẠI", "CẠN CUNG", "THEO DÕI THÊM", "BỎ QUA".
    4. "price_zone": Xác định rõ vùng giá mua gom hợp lý / vùng định giá rẻ và ngưỡng hành động giá.
    5. "macro_view": Đánh giá góc nhìn vĩ mô và dòng tiền lớn với ngành chứa cổ phiếu này. (2 câu).

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
        response = requests.post(API_URL, headers=headers, json=payload, timeout=45)
        if response.status_code == 200:
            res_json = response.json()
            content = res_json["choices"][0]["message"]["content"].strip()
            # Làm sạch chuỗi phản hồi để đảm bảo load JSON an toàn
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

    print(f"🤖 Đang để AI tự động phân tích và định giá toàn bộ thị trường...")
    count = 0
    
    for i, (symbol, data) in enumerate(stock_db.items()):
        if data.get('close', 0) <= 0:
            continue
            
        updated_at = data.get("updated_at", "")
        ai_updated_at = data.get("ai_updated_at", "")
        
        # Nhờ AI phân tích hoàn toàn dựa trên dữ liệu mới
        if not data.get("ai_recommendation") or updated_at > ai_updated_ai if 'ai_updated_ai' in locals() else not data.get("ai_recommendation") or updated_at > ai_updated_at:
            print(f"[{i+1}/{len(stock_db)}] AI đang đánh giá mã: {symbol}...")
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
            
            time.sleep(1.2)
        else:
            print(f"[{i+1}/{len(stock_db)}] Bỏ qua {symbol} (Đã có dữ liệu AI mới nhất)")

    if count > 0:
        with open(DATA_FILE, "w", encoding="utf-8") as f:
            json.dump(stock_db, f, ensure_ascii=False, indent=4)
        print(f"\n🎉 Đã hoàn thành! AI đã phân tích xong {count} mã và cập nhật vào data.json.")
    else:
        print("\nℹ️ Không có mã nào cần phân tích mới.")

if __name__ == "__main__":
    main()
