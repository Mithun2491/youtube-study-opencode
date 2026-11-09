import os
import requests

for line in open(".env", encoding="utf-8-sig"):
    line = line.strip()
    if line and not line.startswith("#") and "=" in line:
        k, v = line.split("=", 1)
        os.environ[k.strip()] = v.strip()

url = os.environ["OPENAI_BASE_URL"].rstrip("/") + "/chat/completions"

payload = {
    "model": os.environ["OPENAI_MODEL"],
    "messages": [
        {
            "role": "user",
            "content": "Reply exactly: YouTube Study Agent connected!"
        }
    ],
    "max_tokens": 80
}

response = requests.post(
    url,
    headers={
        "Authorization": "Bearer " + os.environ["OPENAI_API_KEY"],
        "Content-Type": "application/json"
    },
    json=payload,
    timeout=120
)

print("HTTP Status:", response.status_code)

if response.ok:
    print("AI Response:")
    print(response.json()["choices"][0]["message"]["content"])
else:
    print("Error:", response.text[:1500])
