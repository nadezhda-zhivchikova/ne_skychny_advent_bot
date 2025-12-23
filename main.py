import asyncio
from datetime import date, datetime, time

import pytz
from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import (
    Application,
    ApplicationBuilder,
    CommandHandler,
    ContextTypes,
)

from config import ADVENT_END, ADVENT_START, ADMIN_USER_IDS, BOT_TOKEN, DAILY_SEND_HOUR, TIMEZONE
from storage import (
    User,
    get_advent_day,
    get_subscribed_users,
    list_advent_days,
    set_advent_day,
    set_user_last_sent,
    upsert_user,
    delete_advent_day,
)

import logging

logging.basicConfig(
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

import os

CODE_VERSION = "v2025-12-23-19:40-TBILI"  # любая уникальная строка
logger.info("BOOT %s | file=%s | cwd=%s", CODE_VERSION, __file__, os.getcwd())

async def on_error(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    logger.exception("Unhandled error while handling an update:", exc_info=context.error)


WELCOME_TEXT = (
    "Привет! Я адвент-бот 🎄\n\n"
    "С 26 декабря по 11 января я буду каждый день присылать тебе идеи: игры, рецепты "
    "и маршруты зимних прогулок.\n\n"
    "Чтобы получать ежедневные адвенты, нажми /subscribe\n"
    "Чтобы отписаться — /unsubscribe\n"
    "Чтобы получить сегодняшний адвент вручную — /today"
)


def is_advent_active(now: datetime) -> bool:
    today = now.date()
    return ADVENT_START <= today <= ADVENT_END


async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.effective_chat:
        return
    chat_id = update.effective_chat.id
    upsert_user(chat_id=chat_id, is_subscribed=True)
    await update.message.reply_text(WELCOME_TEXT)


async def cmd_subscribe(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.effective_chat:
        return
    chat_id = update.effective_chat.id
    upsert_user(chat_id=chat_id, is_subscribed=True)
    await update.message.reply_text(
        "Ты успешно подписан на ежедневные адвенты! Я буду писать раз в день 🎁"
    )


async def cmd_unsubscribe(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.effective_chat:
        return
    chat_id = update.effective_chat.id
    upsert_user(chat_id=chat_id, is_subscribed=False)
    await update.message.reply_text("Подписка отключена. Если передумаешь — /subscribe")


async def format_advent_for_date(d: date) -> str | None:
    day = get_advent_day(d)
    if not day:
        return None
    return f"*{day.title}* ({d.strftime('%d.%m.%Y')})\n\n{day.description}"


async def send_advent_to_user(user: User, d: date, context: ContextTypes.DEFAULT_TYPE):
    text = await format_advent_for_date(d)
    if not text:
        return
    try:
        await context.bot.send_message(
            chat_id=user.chat_id,
            text=text,
            parse_mode=ParseMode.MARKDOWN,
        )
        set_user_last_sent(user.chat_id, d)
    except Exception:
        # Игнорируем временные ошибки отправки
        return


async def cmd_today(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.effective_chat:
        return

    tz = pytz.timezone(TIMEZONE)
    now = datetime.now(tz)

    # Для обычных пользователей ограничиваем периодом адвента,
    # администратор может смотреть адвенты без ограничений по датам.
    if not is_admin(update) and not is_advent_active(now):
        await update.message.reply_text(
            "Адвент-бот активен только с 26 декабря по 11 января."
        )
        return

    text = await format_advent_for_date(now.date())
    if not text:
        await update.message.reply_text(
            "На сегодня ещё нет заполненного адвента."
        )
        return

    await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)


def is_admin(update: Update) -> bool:
    return (
        True
     #   update.effective_user is not None
    #    and update.effective_user.id in [6006682315, 2094234407, 1646380100]
    )


async def cmd_admin_help(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not is_admin(update):
        return
    text = (
        "Админ-команды:\n"
        "/admin_add_day YYYY-MM-DD | Заголовок | Описание — добавить/обновить день\n"
        "/admin_list_days — список всех дней\n"
        "/admin_show_day YYYY-MM-DD — показать адвент за конкретный день\n"
        "/admin_delete_day YYYY-MM-DD — удалить адвент за конкретный день\n"
        "/admin_broadcast_today — разослать сегодняшний адвент всем подписчикам сейчас"
    )
    await update.message.reply_text(text)


async def cmd_admin_add_day(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not is_admin(update):
        return
    if not update.message or not update.message.text:
        return

    # Ожидаемый формат:
    # /admin_add_day YYYY-MM-DD | Заголовок | Описание
    raw = update.message.text[len("/admin_add_day") :].strip()
    try:
        date_part, title, description = [p.strip() for p in raw.split("|", 2)]
        d = date.fromisoformat(date_part)
    except Exception:
        await update.message.reply_text(
            "Неверный формат. Пример:\n"
            "/admin_add_day 2025-12-26 | Игровой вечер | Описание игры и активности"
        )
        return

    day = set_advent_day(d, title=title, description=description)
    await update.message.reply_text(
        f"Адвент на {day.day} сохранён.\nЗаголовок: {day.title}"
    )


async def cmd_admin_list_days(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    if not is_admin(update):
        return
    days = list_advent_days()
    if not days:
        await update.message.reply_text("Пока нет ни одного дня в календаре.")
        return

    lines = []
    for d in days:
        lines.append(f"{d.day}: {d.title}")
    await update.message.reply_text("\n".join(lines))


async def cmd_admin_show_day(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    if not is_admin(update):
        return
    if not update.message or not update.message.text:
        return

    raw = update.message.text[len("/admin_show_day") :].strip()
    try:
        d = date.fromisoformat(raw)
    except Exception:
        await update.message.reply_text(
            "Неверный формат. Пример:\n"
            "/admin_show_day 2025-12-26"
        )
        return

    day = get_advent_day(d)
    if not day:
        await update.message.reply_text(
            f"Адвента на дату {d.isoformat()} нет."
        )
        return

    text = f"*{day.title}* ({d.strftime('%d.%m.%Y')})\n\n{day.description}"
    await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)


async def cmd_admin_delete_day(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    if not is_admin(update):
        return
    if not update.message or not update.message.text:
        return

    raw = update.message.text[len("/admin_delete_day") :].strip()
    try:
        d = date.fromisoformat(raw)
    except Exception:
        await update.message.reply_text(
            "Неверный формат. Пример:\n"
            "/admin_delete_day 2025-12-26"
        )
        return

    removed = delete_advent_day(d)
    if removed:
        await update.message.reply_text(
            f"Адвент на дату {d.isoformat()} удалён."
        )
    else:
        await update.message.reply_text(
            f"Адвента на дату {d.isoformat()} не было."
        )


async def cmd_admin_broadcast_today(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    if not is_admin(update):
        return

    tz = pytz.timezone(TIMEZONE)
    now = datetime.now(tz)
    if not is_advent_active(now):
        await update.message.reply_text(
            "Сейчас бот вне периода адвента (26 декабря — 11 января)."
        )
        return

    text = await format_advent_for_date(now.date())
    if not text:
        await update.message.reply_text(
            "На сегодня адвент не заполнен. Сначала добавьте его через /admin_add_day."
        )
        return

    users = get_subscribed_users()
    for u in users:
        await send_advent_to_user(u, now.date(), context)

    await update.message.reply_text(
        f"Отправил сегодняшний адвент {len(users)} подписчикам."
    )


async def daily_broadcast_job(context: ContextTypes.DEFAULT_TYPE) -> None:
    tz = pytz.timezone(TIMEZONE)
    now = datetime.now(tz)
    if not is_advent_active(now):
        return

    today = now.date()
    text = await format_advent_for_date(today)
    if not text:
        return

    users = get_subscribed_users()
    for u in users:
        # Проверяем, не отправляли ли уже сегодня
        if u.last_sent_date == today.isoformat():
            continue
        await send_advent_to_user(u, today, context)


def build_application() -> Application:
    if not BOT_TOKEN:
        raise RuntimeError("BOT_TOKEN не задан. Укажите его в config.py.")

    app = (
        ApplicationBuilder()
        .token(BOT_TOKEN)
        .build()
    )

    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("subscribe", cmd_subscribe))
    app.add_handler(CommandHandler("unsubscribe", cmd_unsubscribe))
    app.add_handler(CommandHandler("today", cmd_today))

    # Админ-команды
    app.add_handler(CommandHandler("admin_help", cmd_admin_help))
    app.add_handler(CommandHandler("admin_add_day", cmd_admin_add_day))
    app.add_handler(CommandHandler("admin_list_days", cmd_admin_list_days))
    app.add_handler(CommandHandler("admin_show_day", cmd_admin_show_day))
    app.add_handler(CommandHandler("admin_delete_day", cmd_admin_delete_day))
    app.add_handler(CommandHandler("admin_broadcast_today", cmd_admin_broadcast_today))

    return app

def main() -> None:
    logger.info("Starting bot...")
    logger.info("MAIN %s | job_queue=%r", CODE_VERSION, getattr(application, "job_queue", "NO_ATTR"))

    application = build_application()
    application.add_error_handler(on_error)

    tz = pytz.timezone(TIMEZONE)
    if application.job_queue is None:
        logger.warning(
            "JobQueue is not available. Install: pip install 'python-telegram-bot[job-queue]' "
        "or add it to requirements.txt."
        )
    else:
        application.job_queue.run_daily(
            callback=daily_broadcast_job,
            time=time(DAILY_SEND_HOUR, 0, tzinfo=tz),
        )
        logger.info("Daily job scheduled at %02d:00 (%s)", DAILY_SEND_HOUR, TIMEZONE)

    # ВАЖНО: если раньше был webhook — удаляем, иначе polling может молчать
    application.run_polling(
        allowed_updates=Update.ALL_TYPES,
        drop_pending_updates=True,
        close_loop=False,
    )

    tz = pytz.timezone(TIMEZONE)


if __name__ == "__main__":
    main()

