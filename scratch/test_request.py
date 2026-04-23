import requests
import json

url = "http://127.0.0.1:8010/v2/estimate"
payload = {
    "user_id": "test_debug",
    "text": "我喝了一杯珍珠奶茶",
    "allow_search": True
}

try:
    response = requests.post(url, json=payload, timeout=60)
    print(f"Status Code: {response.status_code}")
    print(f"Response Body: {json.dumps(response.json(), indent=2, ensure_ascii=False)}")
except Exception as e:
    print(f"Error: {e}")
