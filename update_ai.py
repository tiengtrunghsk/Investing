import os
import json
import time
import requests

DATA_FILE = "data.json"
ALIBABA_API_KEY = os.environ.get("ALIBABA_API_KEY")
QWEN_API_URL = "https://dashscope-intl.aliyuncs.com/compatible-mode/v1/chat/completions"


def load_data():
    if not os.path.exists(DATA_FILE):
        raise FileNotFoundError("Chưa có data.json. Chạy update_screener.py trước.")
    with open(DATA_FILE, encoding="utf-8") as f:
        return json.load(f)


def get_ai_evaluation(symbol, industry, close_price):
    if not ALIBABA_API_KEY:
        return None, None

    price_str = f"{close_price:,.0f} VNĐ" if close_price else "chưa có"
    prompt = f"""Bạn là chuyên gia phân tích tài chính chứng khoán Việt Nam.
Phân tích cổ phiếu {symbol} thuộc nhóm ngành {industry} (giá hiện tại khoảng {price_str}).

Trả về DUY NHẤT JSON thuần túy (không markdown, không văn bản thừa) gồm 2 trường:
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
        if r.status_code != 200:
            print(f"  ⚠️ Qwen HTTP {r.status_code} cho {symbol}: {r.text[:150]}")
            return None, None
        content = r.json()["choices"][0]["message"]["content"].strip()
        eval_data = json.loads(content)
        return eval_data.get("bctc"), eval_data.get("outlook")
    except requests.RequestException as e:
        print(f"  ⚠️ Network Qwen {symbol}: {e}")
    except (KeyError, json.JSONDecodeError) as e:
        print(f"  ⚠️ Parse Qwen {symbol}: {e}")
    return None, None


def main():
    data = load_data()
    total = len(data)
    print(f"🤖 Cập nhật đánh giá AI cho {total} mã...\n")

    updated = 0
    now_iso = time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime())

    for idx, (symbol, info) in enumerate(data.items(), 1):
        industry = info.get("industry", "Cổ phiếu VN100")
        close_price = info.get("close", 0)
        print(f"[{idx}/{total}] {symbol} ({industry})")

        bctc, outlook = get_ai_evaluation(symbol, industry, close_price)
        if bctc and outlook:
            info["bctc"] = bctc
            info["outlook"] = outlook
            info["ai_updated_at"] = now_iso
            updated += 1
            print(f"  ✅ AI cập nhật")
        else:
            print(f"  ⏭️ Bỏ qua")
        time.sleep(0.3)

    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

    # Ghi message Telegram
    msg = f"🤖 <b>Cập nhật Đánh giá AI (Qwen)</b>\n\n- Tổng số mã: {total}\n- Cập nhật thành công: {updated}/{total} mã\n- Thời gian: {now_iso}\n- Trạng thái: Thành công ✅"
    with open("telegram_msg.txt", "w", encoding="utf-8") as f:
        f.write(msg)

    print(f"\n✅ Hoàn tất! Đã cập nhật AI cho {updated}/{total} mã.")


if __name__ == "__main__":
    main()
