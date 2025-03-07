import configparser
import logging
import csv
import io
import datetime
import re
from collections import Counter

import requests
import pandas as pd
import matplotlib.pyplot as plt

from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ConversationHandler,
    CallbackQueryHandler,
    PollHandler,
    ContextTypes,
    filters,
)

# Импорт функций для встреч
from meeting import (
    schedule_start,
    schedule_topic,
    schedule_link,
    schedule_thread,
    schedule_poll_duration,
    add_time_option,
    create_poll,
    choose_participants,
    send_meeting_notification,
    TOPIC,
    LINK,
    THREAD,
    POLL_DURATION,
    TIME_OPTION,
    PARTICIPANTS
)
from poll_handler import poll_handler
from logger import log_chat_activity

# Импорт функций для GitHub и трендов
from abeona_log import (
    fetch_github_repos,
    analyze_github_stats,
    generate_github_bar_chart,
    load_chat_activity,
    analyze_trends,
    generate_neuroflex_wordcloud
)

# Импорт функции отправки статистики, если она есть
from app import send_stats_to_telegram

# Импорт cohere и инициализация клиента
import cohere
COHERE_API_KEY = "0abiLXNoDdCyXTRLNhtwnYPsgRpoiwpmHUyZiy67  "  # Замените на свой ключ
co = cohere.ClientV2(COHERE_API_KEY)

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ----------------- Функции для генерации сообщений с помощью Cohere -----------------

async def generate_and_send_message(context: ContextTypes.DEFAULT_TYPE, prompt: str, caption: str = "") -> None:
    """
    Генерирует сообщение через Cohere и отправляет его во все чаты из bot_data["chat_ids"].
    """
    try:
        response = co.chat(
            model="command-r-plus", 
            messages=[{"role": "user", "content": prompt}]
        )
        generated_text = response.generations[0].text.strip()
    except Exception as e:
        logger.error(f"Ошибка при вызове Cohere: {e}")
        generated_text = f"Ошибка генерации текста: {e}"

    chat_ids = context.application.bot_data.get("chat_ids", [])
    for chat_id in chat_ids:
        await context.bot.send_message(chat_id=chat_id, text=f"{caption}\n\n{generated_text}")

# Функции-обёртки для разных периодов

async def morning_message(context: ContextTypes.DEFAULT_TYPE) -> None:
    prompt = "Сформируй вдохновляющее утреннее сообщение, которое мотивирует на продуктивный день."
    await generate_and_send_message(context, prompt, caption="🌅 Доброе утро!")

async def evening_message(context: ContextTypes.DEFAULT_TYPE) -> None:
    prompt = "Составь сообщение с подведением итогов дня, выдели достижения и вдохнови на завтрашний день."
    await generate_and_send_message(context, prompt, caption="🌇 Добрый вечер!")

async def noon_report(context: ContextTypes.DEFAULT_TYPE) -> None:
    # Здесь можно добавить логику сбора данных за день
    prompt = ("Сформируй подробный дневной отчёт, включающий краткий обзор проведенных встреч, активность участников и "
              "основные обсуждаемые темы за сегодняшний день.")
    await generate_and_send_message(context, prompt, caption="🕛 Дневной отчёт")

async def weekly_summary(context: ContextTypes.DEFAULT_TYPE) -> None:
    # Пример сбора статистики из файлов (можно заменить на свою логику)
    try:
        meetings_df = pd.read_csv("meetings.csv")
    except Exception:
        meetings_df = pd.DataFrame(columns=["poll_id", "topic", "link", "thread_id", "created_at", "options", "proposed_by", "participants"])

    total_meetings = len(meetings_df)
    top_creator = meetings_df["proposed_by"].mode()[0] if not meetings_df.empty else "Нет данных"
    topics = meetings_df["topic"].unique().tolist() if not meetings_df.empty else []
    
    prompt = (f"Сформируй недельную сводку:\n"
              f"- Всего встреч проведено: {total_meetings}\n"
              f"- Самый активный организатор: {top_creator}\n"
              f"- Обсуждаемые темы: {', '.join(topics)}\n\n"
              "Опиши сводку в красивой и подробной форме.")
    await generate_and_send_message(context, prompt, caption="📊 Недельная сводка")

# ----------------- Хендлеры для встреч -----------------
async def log_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Логируем сообщения пользователей в чатах."""
    user = update.effective_user
    log_chat_activity(user.id, user.username, update.message.text)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Отправляет приветственное сообщение."""
    await update.message.reply_text(
        "Привет! Я бот для уведомлений о собраниях и генерации отчётов.\n"
        "Команды:\n"
        "/schedule - запланировать встречу\n"
        "/meetings - показать все запланированные встречи\n"
        "/stats - получить статистику активности\n"
        "/github_stats - статистика GitHub репозиториев\n"
        "/trends_wordcloud - облако слов трендов чата\n"
        "/noon_report - сформировать дневной отчёт\n"
        "/weekly_summary - сформировать недельную сводку"
    )

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Отменяет процесс планирования встречи."""
    await update.message.reply_text("Планирование встречи отменено.")
    return ConversationHandler.END

async def list_meetings(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Выводит список запланированных встреч с кнопками управления."""
    try:
        with open("meetings.csv", "r", encoding="utf-8") as file:
            reader = csv.DictReader(file)
            meetings = list(reader)

        if not meetings:
            await update.message.reply_text("Нет запланированных встреч.")
            return

        for meeting in meetings:
            meeting_id = meeting["poll_id"]
            text = (
                f"📌 **Тема:** {meeting['topic']}\n"
                f"🔗 **Ссылка:** {meeting['link']}\n"
                f"📅 **Создано:** {meeting['created_at']}\n"
            )
            if meeting.get("thread_id"):
                text += f"📍 **ID топика:** {meeting['thread_id']}\n"

            keyboard = [
                [
                    InlineKeyboardButton("🔔 Напомнить", callback_data=f"remind_{meeting_id}"),
                    InlineKeyboardButton("🗑 Отменить", callback_data=f"cancel_{meeting_id}")
                ],
                [
                    InlineKeyboardButton("⏳ Перенести", callback_data=f"reschedule_{meeting_id}")
                ]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await update.message.reply_text(text, reply_markup=reply_markup, parse_mode="Markdown")

    except Exception as e:
        await update.message.reply_text("Ошибка при чтении запланированных встреч.")
        logger.error(f"Ошибка чтения CSV: {e}")

async def remind_meeting(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Отправляет напоминание о встрече в чаты."""
    query = update.callback_query
    await query.answer()

    meeting_id = query.data.replace("remind_", "")
    with open("meetings.csv", "r", encoding="utf-8") as file:
        reader = csv.DictReader(file)
        meetings = {row["poll_id"]: row for row in reader}

    meeting = meetings.get(meeting_id)
    if not meeting:
        await query.message.reply_text("Ошибка: встреча не найдена.")
        return

    text = (
        f"🔔 **Напоминание о встрече!**\n"
        f"📌 **Тема:** {meeting['topic']}\n"
        f"🔗 **Ссылка:** {meeting['link']}\n"
    )

    chat_ids = context.bot_data.get("chat_ids", [])
    for chat_id in chat_ids:
        await context.bot.send_message(chat_id=chat_id, text=text, parse_mode="Markdown")

    await query.message.reply_text("✅ Напоминание отправлено!")

async def cancel_meeting(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Удаляет встречу из списка."""
    query = update.callback_query
    await query.answer()

    meeting_id = query.data.replace("cancel_", "")
    with open("meetings.csv", "r", encoding="utf-8") as file:
        reader = csv.DictReader(file)
        meetings = [row for row in reader if row["poll_id"] != meeting_id]

    fieldnames = ["poll_id", "topic", "link", "thread_id", "created_at", "options", "proposed_by", "participants"]
    with open("meetings.csv", "w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        for row in meetings:
            cleaned_row = {key: row.get(key, "") for key in fieldnames}
            writer.writerow(cleaned_row)

    await query.message.reply_text("✅ Встреча отменена.")

async def show_stats(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Отправляет статистику в Telegram."""
    send_stats_to_telegram()
    await update.message.reply_text("📊 Статистика отправлена в чаты!")

# ----------------- Хендлеры для GitHub и трендов -----------------
async def github_stats_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Обрабатывает команду /github_stats и отправляет статистику репозиториев GitHub.
    """
    try:
        repos = fetch_github_repos("NeuroFlexDev")
        df = analyze_github_stats(repos)
        buf = generate_github_bar_chart(df, "Звезды", "Популярность по звездам")
        await update.message.reply_photo(photo=buf, caption="Статистика репозиториев GitHub")
    except Exception as e:
        logger.error(f"Ошибка получения статистики GitHub: {e}")
        await update.message.reply_text(f"Ошибка получения статистики GitHub: {e}")

async def trends_wordcloud_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Обрабатывает команду /trends_wordcloud и отправляет облако слов с трендами обсуждений.
    """
    try:
        df = load_chat_activity("chat_activity.csv")
        trends = analyze_trends(df)
        if not trends:
            await update.message.reply_text("Нет данных для анализа трендов.")
            return
        buf = generate_neuroflex_wordcloud(trends, "neuroflex_mask.png")
        await update.message.reply_photo(photo=buf, caption="Облако слов (тренды в чатах)")
    except Exception as e:
        logger.error(f"Ошибка генерации wordcloud: {e}")
        await update.message.reply_text(f"Ошибка генерации wordcloud: {e}")

# ----------------- Хендлеры для генерации отчётов -----------------

async def noon_report_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Обрабатывает команду /noon_report для формирования дневного отчёта.
    """
    await noon_report(context)

async def weekly_summary_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Обрабатывает команду /weekly_summary для формирования недельной сводки.
    """
    await weekly_summary(context)

# ----------------- Основная функция -----------------
def main() -> None:
    config = configparser.ConfigParser()
    config.read("config.ini", encoding="utf-8")

    bot_token = config.get("TELEGRAM", "BOT_TOKEN", fallback=None)
    chat_ids_raw = config.get("TELEGRAM", "CHAT_IDS", fallback="")

    try:
        chat_ids = [int(chat.strip()) for chat in chat_ids_raw.split(",") if chat.strip()]
    except ValueError as e:
        logger.error(f"Ошибка преобразования CHAT_IDS в int: {e}")
        chat_ids = []

    if not chat_ids:
        logger.error("❌ Ошибка: CHAT_IDS не загружены или пусты! Проверьте config.ini.")
    else:
        logger.info(f"✅ Загруженные CHAT_IDS: {chat_ids}")

    application = Application.builder().token(bot_token).build()
    application.bot_data["chat_ids"] = chat_ids

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("schedule", schedule_start)],
        states={
            TOPIC: [MessageHandler(filters.TEXT & ~filters.COMMAND, schedule_topic)],
            LINK: [MessageHandler(filters.TEXT & ~filters.COMMAND, schedule_link)],
            THREAD: [MessageHandler(filters.TEXT & ~filters.COMMAND, schedule_thread)],
            POLL_DURATION: [MessageHandler(filters.TEXT & ~filters.COMMAND, schedule_poll_duration)],
            TIME_OPTION: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_time_option)],
            PARTICIPANTS: [MessageHandler(filters.TEXT & ~filters.COMMAND, choose_participants)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )

    # Регистрируем хендлеры для встреч
    application.add_handler(CommandHandler("start", start))
    application.add_handler(conv_handler)
    application.add_handler(PollHandler(poll_handler))
    application.add_handler(CommandHandler("meetings", list_meetings))
    application.add_handler(CommandHandler("stats", show_stats))
    application.add_handler(CallbackQueryHandler(remind_meeting, pattern="^remind_"))
    application.add_handler(CallbackQueryHandler(cancel_meeting, pattern="^cancel_"))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, log_message))

    # Регистрируем хендлеры для GitHub и трендов
    application.add_handler(CommandHandler("github_stats", github_stats_handler))
    application.add_handler(CommandHandler("trends_wordcloud", trends_wordcloud_handler))

    # Регистрируем хендлеры для отчётов
    application.add_handler(CommandHandler("noon_report", noon_report_handler))
    application.add_handler(CommandHandler("weekly_summary", weekly_summary_handler))

    # Планирование задач через JobQueue
    job_queue = application.job_queue

    # Утреннее сообщение – например, в 9:00
    job_queue.run_daily(morning_message, time=datetime.time(hour=9, minute=0, second=0))
    # Вечернее сообщение – например, в 18:00
    job_queue.run_daily(evening_message, time=datetime.time(hour=18, minute=0, second=0))
    # Дневной отчёт – в 12:00
    job_queue.run_daily(noon_report, time=datetime.time(hour=12, minute=0, second=0))
    # Недельная сводка – каждое воскресенье в 20:00
    job_queue.run_daily(
        weekly_summary,
        time=datetime.time(hour=20, minute=0, second=0),
        days=(6,)  # Только по воскресеньям
    )

    logger.info("Бот запущен!")
    application.run_polling()

if __name__ == '__main__':
    main()
