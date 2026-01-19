import requests
import time

def check_binance():
    url = "https://api.binance.com/api/v3/ping"
    print(f"📡 Đang thử kết nối tới: {url}")
    try:
        t0 = time.time()
        response = requests.get(url, timeout=5)
        latency = (time.time() - t0) * 1000
        
        if response.status_code == 200:
            print(f"✅ Kết nối TỐT! Độ trễ: {latency:.2f}ms")
        else:
            print(f"⚠️ Kết nối được nhưng lỗi Status: {response.status_code}")
            
    except Exception as e:
        print(f"❌ KHÔNG THỂ kết nối: {e}")
        print("👉 Gợi ý: Hãy đổi DNS sang 8.8.8.8 hoặc bật VPN.")

if __name__ == "__main__":
    check_binance()