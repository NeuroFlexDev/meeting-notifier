import csv
import logging
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ContextTypes, ConversationHandler, MessageHandler, CommandHandler, CallbackQueryHandler, filters

# Импорт функций для планирования встреч из модуля meeting.py
from bot.meeting import (
    schedule_start,
    schedule_topic,
    schedule_link,
    schedule_thread,
    schedule_poll_duration,
    add_time_option,
    choose_participants,
    TOPIC, LINK, THREAD, POLL_DURATION, TIME_OPTION, PARTICIPANTS
)

# Импорт функции логирования сообщений
from bot.logger import log_chat_activity

logger = logging.getLogger(__name__)

async def log_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Логирует входящие сообщения пользователей."""
    user = update.effective_user
    log_chat_activity(user.id, user.username, update.message.text)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Отправляет стартовое сообщение с описанием доступных команд."""
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
    """Обрабатывает отмену процесса планирования встречи."""
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
    try:
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
    except Exception as e:
        logger.error(f"Ошибка при отправке напоминания: {e}")
        await query.message.reply_text("Ошибка при отправке напоминания.")

async def cancel_meeting(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Удаляет встречу из списка."""
    query = update.callback_query
    await query.answer()

    meeting_id = query.data.replace("cancel_", "")
    try:
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

        await query.message.reply_text("✅ Встреча отменена!")
    except Exception as e:
        logger.error(f"Ошибка при отмене встречи: {e}")
        await query.message.reply_text("Ошибка при отмене встречи.")
