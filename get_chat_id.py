import configparser
import logging
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, ContextTypes, filters

# Настройка логирования
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

async def get_ids(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id = update.effective_chat.id
    # Если сообщение отправлено в топике, message_thread_id будет присутствовать
    message_thread_id = (
        update.message.message_thread_id if update.message.message_thread_id else "Отсутствует"
    )
    text = f"Chat ID: {chat_id}\nMessage Thread ID: {message_thread_id}"
    await update.message.reply_text(text)
    logger.info(text)

def main() -> None:
    config = configparser.ConfigParser()
    config.read("config.ini")
    bot_token = config["TELEGRAM"]["BOT_TOKEN"]

    application = Application.builder().token(bot_token).build()

    # Любое текстовое сообщение вызовет обработчик, который отправит вам айди
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, get_ids))
    application.add_handler(CommandHandler("start", get_ids))

    application.run_polling()

if __name__ == "__main__":
    main()
