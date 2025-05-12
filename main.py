import os
import requests
from flask import Flask, request, jsonify
import asyncio
from typing import Iterable, Sequence
from telethon import TelegramClient, functions, types
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


async def create_group_with_link(
    title: str,
    welcome_messages: Sequence[str] | None = None,
    invite_usernames: Iterable[str] | None = None,
) -> str:
    """
    Create a Telegram super‑group, send `welcome_messages`, invite `invite_usernames`,
    and return a permanent join link.
    """
    async with TelegramClient(SESSION, os.environ.get("API_ID"), os.environ.get("API_HASH")) as client:

        # 1️⃣  Create the super‑group (a “megagroup” channel)  ────────────────
        result = await client(
            functions.channels.CreateChannelRequest(
                title=title,
                about="Auto‑created by script",
                megagroup=True           # makes it act like a group, not a broadcast channel
            )
        )                                                # :contentReference[oaicite:0]{index=0}
        group = result.chats[0]        # the newly‑created chat object

        # 2️⃣  Optionally add more members (users or bots)  ──────────────────
        if invite_usernames:
            peers = [await client.get_input_entity(u) for u in invite_usernames]
            await client(
                functions.channels.InviteToChannelRequest(
                    channel=group,
                    users=peers
                )
            )                                            # :contentReference[oaicite:1]{index=1}

        # 3️⃣  Drop some welcome messages  ───────────────────────────────────
        for text in (welcome_messages or ()):
            await client.send_message(group, text)

        # 4️⃣  Export a join link  ───────────────────────────────────────────
        invite = await client(
            functions.messages.ExportChatInviteRequest(   # ← messages.* not channels.*
                peer=group                                # any InputPeer/Entity is fine
            )   
        )                                                # :contentReference[oaicite:2]{index=2}

        return invite.link

# ——— Endpoint ———
@app.route("/send", methods=["POST"])
def send():
    if not request.is_json:
        return jsonify(ok=False, error="Content-Type must be application/json"), 400

    # 2) Parse body
    data = request.get_json(force=True)
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
        link = asyncio.run(
        create_group_with_link(
            title=f"*IT-Enterprise. Підтримка {data['name']}",
            welcome_messages=["👋 Вітаємо!", f"Чат стосовно питання {data['question']}, електронна пошта користувача - {data['email']}"],
            invite_usernames=["+380665699272", "@TestFlowiseMessageBot"]   # can mix @usernames & phone contacts you imported
        )
    )
    return jsonify(ok=True, link), 200
    except requests.HTTPError as e:
        return jsonify(ok=False, error=f"Telegram API error: {e}"), 502
    except Exception as e:
        return jsonify(ok=False, error=str(e)), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=1000)
