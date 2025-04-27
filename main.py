import os
import requests
from flask import Flask, request, jsonify

app = Flask(__name__)

# ——— Config ———
BOT_TOKEN = os.environ.get("TELEGRAM_TOKEN")
CHAT_ID   = os.environ.get("TELEGRAM_CHAT_ID")
if not BOT_TOKEN or not CHAT_ID:
    raise RuntimeError("Set TELEGRAM_TOKEN and TELEGRAM_CHAT_ID in env")

TELEGRAM_URL = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"

# ——— Helper to send to Telegram ———
def send_message(text: str):
    resp = requests.post(TELEGRAM_URL, json={
        "chat_id": CHAT_ID,
        "text": text,
        "parse_mode": "Markdown"
    })
    resp.raise_for_status()
    return resp.json()

# ——— Endpoint ———
@app.route("/send", methods=["POST"])
def send():
    if not request.is_json:
        return jsonify(ok=False, error="Content-Type must be application/json"), 400

    # 2) Parse body
    data = request.get_json(force=True)
    print(data)
    # 3) Validate fields
    required = ("name", "email", "question")
    missing = [k for k in required if not isinstance(data.get(k), str) or not data[k].strip()]
    if missing:
        return (
            jsonify(ok=False, error=f"Missing or empty fields: {', '.join(missing)}"),
            400
        )

    # 4) Build and send the Telegram message
    text = (
        "*New Submission*\n"
        f"*Name:* {data['name']}\n"
        f"*Email:* {data['email']}\n\n"
        "*Question:*\n"
        f"{data['question']}"
    )
    try:
        result = send_message(text)
        return jsonify(ok=True, telegram=result)
    except requests.HTTPError as e:
        return jsonify(ok=False, error=f"Telegram API error: {e}"), 502
    except Exception as e:
        return jsonify(ok=False, error=str(e)), 500

# ——— Run on Replit ———
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
