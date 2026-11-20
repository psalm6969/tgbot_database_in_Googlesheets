"""Telegram email capture bot -> Google Sheets, using a service account.

Configuration is read from environment variables. Do not commit secrets.
"""

from __future__ import annotations

import json
import os
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen

from google.auth.transport.requests import Request as GoogleAuthRequest
from google.oauth2.service_account import Credentials


EMAIL_RE = re.compile(r"^[A-Z0-9.!#$%&'*+/=?^_`{|}~-]+@[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?(?:\.[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?)+$", re.I)
SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]
STATE_FILE = Path(os.getenv("BOT_STATE_FILE", "email_bot_state.json"))
SHEET_RANGE = os.getenv("GOOGLE_SHEET_RANGE", "'Задача 3'!A:D")


def required_env(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value:
        raise RuntimeError(f"Missing required environment variable: {name}")
    return value


BOT_TOKEN = required_env("TELEGRAM_BOT_TOKEN")
SPREADSHEET_ID = required_env("GOOGLE_SPREADSHEET_ID")
SERVICE_ACCOUNT_FILE = Path(required_env("GOOGLE_SERVICE_ACCOUNT_FILE"))


def load_state() -> int:
    try:
        return int(json.loads(STATE_FILE.read_text(encoding="utf-8")).get("next_update_id", 0))
    except FileNotFoundError:
        return 0
    except (ValueError, TypeError, json.JSONDecodeError):
        print("State file is invalid; starting Telegram update cursor at 0.", file=sys.stderr)
        return 0


def save_state(next_update_id: int) -> None:
    tmp = STATE_FILE.with_suffix(STATE_FILE.suffix + ".tmp")
    tmp.write_text(json.dumps({"next_update_id": next_update_id}), encoding="utf-8")
    tmp.replace(STATE_FILE)


def telegram(method: str, payload: dict, timeout: int = 40) -> dict:
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/{method}"
    body = json.dumps(payload).encode("utf-8")
    req = Request(url, data=body, headers={"Content-Type": "application/json"}, method="POST")
    with urlopen(req, timeout=timeout) as response:
        result = json.loads(response.read().decode("utf-8"))
    if not result.get("ok"):
        raise RuntimeError(f"Telegram API {method} failed: {result}")
    return result["result"]


def get_credentials() -> Credentials:
    if not SERVICE_ACCOUNT_FILE.is_file():
        raise RuntimeError(f"Service account key file not found: {SERVICE_ACCOUNT_FILE}")
    creds = Credentials.from_service_account_file(str(SERVICE_ACCOUNT_FILE), scopes=SCOPES)
    creds.refresh(GoogleAuthRequest())
    return creds


def sheets_append(email: str, user: dict, update_id: int) -> None:
    creds = get_credentials()
    timestamp = datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")
    user_label = "@" + user["username"] if user.get("username") else str(user.get("id", ""))
    values = [[timestamp, email, user_label, str(update_id)]]
    url = (
        "https://sheets.googleapis.com/v4/spreadsheets/"
        + quote(SPREADSHEET_ID, safe="")
        + "/values/"
        + quote(SHEET_RANGE, safe="'!:A-Z0-9_%")
        + ":append?valueInputOption=USER_ENTERED&insertDataOption=INSERT_ROWS"
    )
    body = json.dumps({"majorDimension": "ROWS", "values": values}).encode("utf-8")
    req = Request(
        url,
        data=body,
        headers={"Authorization": f"Bearer {creds.token}", "Content-Type": "application/json"},
        method="POST",
    )
    with urlopen(req, timeout=30) as response:
        result = json.loads(response.read().decode("utf-8"))
    if "updates" not in result:
        raise RuntimeError(f"Google Sheets append returned unexpected result: {result}")


def send_message(chat_id: int, text: str) -> None:
    telegram("sendMessage", {"chat_id": chat_id, "text": text}, timeout=20)


def handle_update(update: dict) -> None:
    message = update.get("message") or update.get("edited_message")
    if not message or not message.get("text"):
        return
    chat_id = message["chat"]["id"]
    text = message["text"].strip()
    user = message.get("from", {})
    if text.startswith("/"):
        send_message(chat_id, "Отправьте email одним сообщением — я добавлю его в таблицу.")
        return

    email = text.strip(" <>\t\r\n")
    if not EMAIL_RE.fullmatch(email):
        send_message(chat_id, "Не похоже на email. Пришлите адрес в формате name@example.com.")
        return

    try:
        sheets_append(email, user, int(update["update_id"]))
    except (HTTPError, URLError, TimeoutError, RuntimeError, OSError) as exc:
        print(f"Failed to store an email (update {update.get('update_id')}): {exc}", file=sys.stderr)
        send_message(chat_id, "Не получилось записать адрес в таблицу. Попробуйте позже.")
        return
    send_message(chat_id, "Готово, email добавлен в таблицу.")


def main() -> None:
    offset = load_state()
    print("Email capture bot started. Stop with Ctrl+C.")
    while True:
        try:
            updates = telegram("getUpdates", {"offset": offset, "timeout": 30, "allowed_updates": ["message"]}, timeout=40)
            for update in updates:
                update_id = int(update["update_id"])
                try:
                    handle_update(update)
                except (HTTPError, URLError, TimeoutError, RuntimeError, OSError) as exc:
                    print(f"Update {update_id} failed: {exc}", file=sys.stderr)
                offset = update_id + 1
                save_state(offset)
        except KeyboardInterrupt:
            print("Stopped.")
            return
        except (HTTPError, URLError, TimeoutError, RuntimeError, OSError, json.JSONDecodeError) as exc:
            print(f"Polling error: {exc}", file=sys.stderr)
            time.sleep(3)


if __name__ == "__main__":
    main()
