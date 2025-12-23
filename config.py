from datetime import date

# ===== НАСТРОЙКИ БОТА (ЗАДАЮТСЯ В КОДЕ) =====

# Токен бота от BotFather
BOT_TOKEN: str = "8287096896:AAEfektF87MQEut1pZoy4IaizsmL-Yn9GFM"

# Telegram user ID администраторов (целые числа)
# Узнать можно, например, через бота @userinfobot
# Можно указать один или несколько ID через запятую
ADMIN_USER_IDS: tuple[int, ...] = (
    6006682315,
    2094234407,
    1646380100,
    5047298882,
)

# Час отправки по умолчанию (по часовому поясу TIMEZONE)
DAILY_SEND_HOUR: int = 10

# Часовой пояс в формате IANA (используется в python-telegram-bot)
TIMEZONE: str = "Europe/Moscow"

# Период работы адвента
ADVENT_START: date = date(date.today().year, 12, 26)
ADVENT_END: date = date(date.today().year + 1, 1, 11)


