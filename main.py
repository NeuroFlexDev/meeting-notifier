import configparser
import datetime
import logging

from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ConversationHandler,
    CallbackQueryHandler,
    PollHandler,
    filters
)

# Импорт обработчиков встреч из модуля meeting_handlers
from bot.handlers.meeting_handlers import (
    start,
    cancel,
    list_meetings,
    log_message,
    remind_meeting,
    cancel_meeting
)

# Импорт функций для этапов планирования встречи из модуля meeting (conversation)
from bot.meeting import (
    schedule_start,
    schedule_topic,
    schedule_link,
    schedule_thread,
    schedule_poll_duration,
    add_time_option,
    choose_participants,
    TOPIC,
    LINK,
    THREAD,
    POLL_DURATION,
    TIME_OPTION,
    PARTICIPANTS
)

# Импорт обработчиков GitHub и трендов
from bot.handlers.github_handlers import github_stats_handler, trends_wordcloud_handler

# Импорт функций для генерации отчётов с помощью HuggingChat (используются в качестве периодических задач)
from bot.huggingchat_client import (
    morning_message,
    evening_message,
    noon_report,
    weekly_summary
)
from bot.handlers.help_handler import help_handler

# Импорт обработчиков отчётов для команды (если они нужны для ручного запуска)
from bot.handlers.report_handlers import noon_report_handler, weekly_summary_handler

# Импорт обработчика для опросов (poll_handler)
from bot.poll_handler import poll_handler

# # Импорт функции отправки статистики (если используется)
# from bot.app import send_stats_to_telegram

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)


def main() -> None:
    # Загрузка конфигурации из config.ini
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

    # Инициализация приложения Telegram
    application = Application.builder().token(bot_token).build()
    application.bot_data["chat_ids"] = chat_ids

    # Создание ConversationHandler для планирования встреч
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
        fallbacks=[CommandHandler("cancel", cancel)]
    )

    # Регистрация хендлеров
    application.add_handler(CommandHandler("start", start))
    application.add_handler(conv_handler)
    application.add_handler(PollHandler(poll_handler))
    application.add_handler(CommandHandler("meetings", list_meetings))
    application.add_handler(CommandHandler("stats", lambda update, context: send_stats_to_telegram()))
    application.add_handler(CallbackQueryHandler(remind_meeting, pattern="^remind_"))
    application.add_handler(CallbackQueryHandler(cancel_meeting, pattern="^cancel_"))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, log_message))
    application.add_handler(CommandHandler("github_stats", github_stats_handler))
    application.add_handler(CommandHandler("trends_wordcloud", trends_wordcloud_handler))
    # Команды для ручного формирования отчётов
    application.add_handler(CommandHandler("noon_report", noon_report_handler))
    application.add_handler(CommandHandler("weekly_summary", weekly_summary_handler))

    application.add_handler(CommandHandler("help", help_handler))

    # Планирование периодических задач через JobQueue
    job_queue = application.job_queue
    job_queue.run_daily(morning_message, time=datetime.time(hour=9, minute=0, second=0))
    job_queue.run_daily(evening_message, time=datetime.time(hour=18, minute=0, second=0))
    job_queue.run_daily(noon_report, time=datetime.time(hour=12, minute=0, second=0))
    job_queue.run_daily(weekly_summary, time=datetime.time(hour=20, minute=0, second=0), days=(6,))  # Только по воскресеньям

    logger.info("Бот запущен!")
    application.run_polling()


if __name__ == '__main__':
    main()
