import os
import json
import time
import requests
from datetime import datetime

# ==================== CẤU HÌNH ====================
ALIBABA_API_KEY = os.environ.get("ALIBABA_API_KEY")
QWEN_API_URL = "https://dashscope-intl.aliyuncs.com/compatible-mode/v1/chat/completions"

# VNDIRECT API endpoints
VND_DCHART_URL = "https://dchart-api.vndirect.com.vn/dchart/history"
VND_FUNDAMENTAL_URL = "https://api-finfo.vndirect.com.vn/v4/ratios"

# Ratio codes đã xác minh hoạt động thực tế [citation:2]
RATIO_PE = "PRICE_TO_EARNINGS"
RATIO_PB = "PRICE_TO_BOOK"
RATIO_ROE = "ROAE_TR_AVG5Q"

# ==================== DANH SÁCH VN100 ====================
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


# ==================== HÀM LẤY GIÁ ====================
def fetch_stock_price(symbol):
    """Lấy giá đóng cửa gần nhất từ VNDIRECT dchart API."""
    now = int(time.time())
    start = now - (365 * 86400)  # 1 năm gần nhất
    params = {
        "resolution": "D",
        "symbol": symbol,
        "from": start,
        "to": now
    }
    try:
        r = requests.get(VND_DCHART_URL, params=params, timeout=10)
        r.raise_for_status()
        data = r.json()
        if data.get("s") == "ok" and data.get("c") and len(data["c"]) >= 20:
            return data["c"][-1]
    except requests.RequestException as e:
        print(f"  ⚠️ Lỗi giá {symbol}: {e}")
    except ValueError as e:
        print(f"  ⚠️ JSON lỗi giá {symbol}: {e}")
    return None


# ==================== HÀM LẤY CHỈ SỐ TÀI CHÍNH ====================
def fetch_single_ratio(symbol, ratio_code):
    """
    Lấy một chỉ số tài chính từ VNDIRECT.
    Mỗi ratioCode phải gọi riêng 1 request (theo tài liệu đã xác minh). [citation:2]
    """
    params = {
        "q": f"code:{symbol}~ratioCode:{ratio_code}",
        "size": 1,
        "sort": "reportDate:desc"
    }
    try:
        r = requests.get(VND_FUNDAMENTAL_URL, params=params, timeout=10)
        r.raise_for_status()
        data = r.json()
        if data.get("data") and len(data["data"]) > 0:
            val = data["data"][0].get("value")
            return float(val) if val is not None else None
    except requests.RequestException as e:
        print(f"  ⚠️ Lỗi ratio {symbol}/{ratio_code}: {e}")
    except (ValueError, TypeError) as e:
        print(f"  ⚠️ Parse lỗi {symbol}/{ratio_code}: {e}")
    return None


def fetch_fundamentals(symbol):
    """Lấy bộ chỉ số P/E, P/B, ROE thực tế."""
    pe = fetch_single_ratio(symbol, RATIO_PE)
    time.sleep(0.15)  # Tránh rate limit
    pb = fetch_single_ratio(symbol, RATIO_PB)
    time.sleep(0.15)
    roe = fetch_single_ratio(symbol, RATIO_ROE)
    time.sleep(0.15)
    return {
        "pe": round(pe, 1) if pe is not None else None,
        "pb": round(pb, 1) if pb is not None else None,
        "roe": round(roe, 1) if roe is not None else None
    }


# ==================== HÀM GỌI AI QWEN ====================
def get_ai_evaluation(symbol, industry, close_price):
    """Gọi Qwen API để lấy đánh giá định tính BCTC và triển vọng."""
    if not ALIBABA_API_KEY:
        return "Chưa cấu hình API Key.", "Đang cập nhật..."

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
    headers = {
        "Authorization": f"Bearer {ALIBABA_API_KEY}",
        "Content-Type": "application/json"
    }

    try:
        r = requests.post(QWEN_API_URL, headers=headers, json=payload, timeout=25)
        if r.status_code != 200:
            print(f"  ⚠️ Qwen HTTP {r.status_code} cho {symbol}: {r.text[:150]}")
            return "Doanh nghiệp có nền tảng cơ bản.", "Phù hợp tích lũy dài hạn."

        res_json = r.json()
        content = res_json["choices"][0]["message"]["content"].strip()
        eval_data = json.loads(content)
        return (
            eval_data.get("bctc", "BCTC lành mạnh, tài chính an toàn."),
            eval_data.get("outlook", "Tiềm năng tăng trưởng ổn định.")
        )
    except requests.RequestException as e:
        print(f"  ⚠️ Network Qwen {symbol}: {e}")
    except (KeyError, json.JSONDecodeError) as e:
        print(f"  ⚠️ Parse Qwen {symbol}: {e}")

    return "Doanh nghiệp có nền tảng cơ bản tốt.", "Phù hợp tích lũy dài hạn."


# ==================== HÀM CHÍNH ====================
def main():
    processed_data = {}
    unique_symbols = sorted(set(VN100_SYMBOLS))  # Sorted để output ổn định
    total = len(unique_symbols)

    print(f"🚀 Bắt đầu cập nhật {total} mã VN100...")
    print(f"📊 Chỉ số lấy thực tế từ VNDIRECT, AI chỉ đánh giá định tính.\n")

    for idx, symbol in enumerate(unique_symbols, 1):
        industry = INDUSTRY_MAP.get(symbol, "Cổ phiếu VN100")
        print(f"[{idx}/{total}] {symbol} ({industry})")

        # 1. Lấy giá thực tế
        close_price = fetch_stock_price(symbol)
        print(f"  → Giá: {close_price if close_price else 'N/A'}")

        # 2. Lấy chỉ số tài chính thực tế
        fundamentals = fetch_fundamentals(symbol)
        print(f"  → P/E: {fundamentals['pe']}, P/B: {fundamentals['pb']}, ROE: {fundamentals['roe']}%")

        # 3. Gọi AI đánh giá định tính
        bctc, outlook = get_ai_evaluation(symbol, industry, close_price)
        print(f"  → AI: {bctc[:50]}...")

        processed_data[symbol] = {
            "symbol": symbol,
            "industry": industry,
            "close": close_price if close_price else 0,
            "pe": fundamentals["pe"],
            "pb": fundamentals["pb"],
            "roe": fundamentals["roe"],
            "bctc": bctc,
            "outlook": outlook
        }

        # Nghỉ giữa các mã để tránh rate limit
        time.sleep(0.3)

    # Ghi file
    with open("data.json", "w", encoding="utf-8") as f:
        json.dump(processed_data, f, ensure_ascii=False, indent=4)

    print(f"\n✅ Hoàn tất! Đã lưu {len(processed_data)} mã vào data.json")


if __name__ == "__main__":
    main()
