import os
import requests

def telegram_get_me() -> dict:
    token = "8287096896:AAEfektF87MQEut1pZoy4IaizsmL-Yn9GFM"

    url = f"https://api.telegram.org/bot{token}/getMe"

    try:
        r = requests.get(url, timeout=10)
        r.raise_for_status()
        data = r.json()
    except requests.exceptions.RequestException as e:
        raise RuntimeError(f"Network/HTTP error while calling Telegram API: {e}") from e
    except ValueError as e:
        raise RuntimeError("Telegram returned non-JSON response.") from e

    if not data.get("ok"):
        # Важно: не выводим токен, и вообще избегаем лишних подробностей
        desc = data.get("description", "No description")
        code = data.get("error_code", "No error_code")
        raise RuntimeError(f"Telegram API error {code}: {desc}")

    return data["result"]

if __name__ == "__main__":
    me = telegram_get_me()
    print("Bot info:")
    print("  id:", me.get("id"))
    print("  name:", me.get("first_name"))
    print("  username:", "@" + me.get("username", ""))

