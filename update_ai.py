import json
import os
import time
import requests
import re

DATA_FILE = "data.json"

ALIBABA_API_KEY = os.getenv("ALIBABA_API_KEY", "").strip()
API_URL = "https://ws-8lcqaxwxdv0h9xzy.ap-southeast-1.maas.aliyuncs.com/compatible-mode/v1/chat/completions"

def analyze_stock_with_ai(symbol, data):
    if not ALIBABA_API_KEY:
        print(f"❌ LỖI: Biến ALIBABA_API_KEY đang bị trống!")
        return None

    # Prompt thuần túy Price Action, VCP, Volume & Tích lũy nền trên khung D1
    prompt = f"""
    Bạn là một chuyên gia giao dịch theo trường phái Dòng tiền lớn (Smart Money / Price Action & Volume Spread Analysis - VCP) trên khung đồ thị Ngày (D1) tại thị trường chứng khoán Việt Nam.
    Hãy phân tích mã cổ phiếu: {symbol} thuộc nhóm ngành: {data.get('industry', 'Khác')}.
    
    Dữ liệu thị trường hiện tại (Khung D1):
    - Giá hiện tại: {data.get('close', 0)} (nghìn đồng)
    - P/E: {data.get('pe', 0)}x | P/B: {data.get('pb', 0)}x
    - Tỷ suất cổ tức: {data.get('dividendYield', 0)}%

    Yêu cầu phân tích tập trung vào hành động giá và khối lượng (Price & Volume):
    1. "bctc": Đánh giá nhanh nền tảng cơ bản xem doanh nghiệp có đủ chất lượng để dòng tiền lớn gom dài hạn không (2 câu).
    2. "outlook": Đánh giá trạng thái vận động của giá trên nền D1 (Đang siết nền tích lũy biên độ hẹp, kiệt volume, hay đang chuẩn bị breakout/test lại kháng cự?).
    3. "recommendation": Chọn 1 trong các trạng thái chuẩn: "GOM TÍCH SẢN", "SẴN SÀNG BREAKOUT", "ĐANG TÍCH LŨY NỀN", "CHỜ TEST LẠI", "NGOÀI DANH MỤC".
    4. "price_zone": Xác định rõ vùng nền giá tích lũy và điểm mua chuẩn (Ví dụ: "Nền gom: 20.0 - 22.0 | Mua gia tăng khi Breakout > 23.5 kèm Vol lớn").
    5. "macro_view": Đánh giá vĩ mô và sóng ngành ủng hộ dòng tiền lớn (2 câu).

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
        response = requests.post(API_URL, headers=headers, json=payload, timeout=40)
        if response.status_code == 200:
            res_json = response.json()
            content = res_json["choices"][0]["message"]["content"].strip()
            content = re.sub(r"^```json\s*", "", content)
            content = re.sub(r"^```\s*", "", content)
            content = re.sub(r"\s*```$", "", content)
            return json.loads(content)
    except Exception as e:
        print(f"[{symbol}] Lỗi AI: {e}")
    
    return None

def main():
    if not os.path.exists(DATA_FILE):
        print("❌ Không tìm thấy file data.json!")
        return

    with open(DATA_FILE, "r", encoding="utf-8") as f:
        stock_db = json.load(f)

    print(f"🤖 Bắt đầu quét Price & Volume (D1) cho {len(stock_db)} mã...")
    count = 0
    for symbol, data in stock_db.items():
        print(f"Đang xử lý: {symbol}...")
        ai_result = analyze_stock_with_ai(symbol, data)
        
        if ai_result:
            data["bctc"] = ai_result.get("bctc", data.get("bctc"))
            data["outlook"] = ai_result.get("outlook", data.get("outlook"))
            data["recommendation"] = ai_result.get("recommendation", data.get("recommendation"))
            data["price_zone"] = ai_result.get("price_zone", data.get("price_zone"))
            data["macro_view"] = ai_result.get("macro_view", data.get("macro_view"))
            data["ai_updated_at"] = time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime())
            count += 1
            print(f"  -> ✅ Thành công {symbol}")
        time.sleep(0.5)

    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(stock_db, f, ensure_ascii=False, indent=4)

    print(f"✅ Đã cập nhật xong {count} mã!")

if __name__ == "__main__":
    main()
