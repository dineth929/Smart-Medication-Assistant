import json
import urllib.request
from core.database import get_db_path
import os

# 1. Grab your key
key = os.environ.get("GEMINI_API_KEY", "").strip()
if not key:
    key_file = get_db_path().parent / "api_key.txt"
    if key_file.exists():
        key = key_file.read_text().strip()

print("Using key starting with:", key[:8] if key else "EMPTY")

# 2. Ask Google for the EXACT list of available models for your key
url = f"https://generativelanguage.googleapis.com/v1beta/models?key={key}"

try:
    req = urllib.request.Request(url)
    with urllib.request.urlopen(req) as resp:
        data = json.load(resp)
        print("\n--- AVAILABLE MODELS FOR YOUR KEY ---")
        for m in data.get("models", []):
            methods = m.get("supportedGenerationMethods", [])
            if "generateContent" in methods:
                print(m["name"].replace("models/", ""))
except Exception as e:
    print("Error querying models:", e)