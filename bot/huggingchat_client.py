import os
import asyncio
import logging
from hugchat import hugchat
from hugchat.login import Login

logger = logging.getLogger(__name__)

# Инициализация клиента
HUGGING_EMAIL = os.environ.get("HUGGING_EMAIL")
HUGGING_PASSWD = os.environ.get("HUGGING_PASSWD")
cookie_path_dir = "./cookies/"  # Завершающий слеш обязателен

if not HUGGING_EMAIL or not HUGGING_PASSWD:
    raise ValueError("Не заданы переменные окружения HUGGING_EMAIL и/или HUGGING_PASSWD.")

sign = Login(HUGGING_EMAIL, HUGGING_PASSWD)
cookies = sign.login(cookie_dir_path=cookie_path_dir, save_cookies=True)
chatbot = hugchat.ChatBot(cookies=cookies.get_dict())

async def generate_and_send_message(context, prompt: str, caption: str = "") -> None:
    """
    Генерирует сообщение через HuggingChat и отправляет его во все чаты из bot_data["chat_ids"].
    """
    try:
        response = await asyncio.to_thread(chatbot.chat, prompt)
        generated_text = response.wait_until_done().strip()
    except Exception as e:
        logger.error(f"Ошибка при вызове hugging-chat-api: {e}")
        generated_text = f"Ошибка генерации текста: {e}"

    chat_ids = context.application.bot_data.get("chat_ids", [])
    for chat_id in chat_ids:
        await context.bot.send_message(chat_id=chat_id, text=f"{caption}\n\n{generated_text}")

async def morning_message(context) -> None:
    prompt = "Сформируй вдохновляющее утреннее сообщение, которое мотивирует на продуктивный день."
    await generate_and_send_message(context, prompt, caption="🌅 Доброе утро!")

async def evening_message(context) -> None:
    prompt = "Составь сообщение с подведением итогов дня, выдели достижения и вдохнови на завтрашний день."
    await generate_and_send_message(context, prompt, caption="🌇 Добрый вечер!")

async def noon_report(context) -> None:
    prompt = ("Сформируй подробный дневной отчёт, включающий краткий обзор проведенных встреч, активность участников и "
              "основные обсуждаемые темы за сегодняшний день.")
    await generate_and_send_message(context, prompt, caption="🕛 Дневной отчёт")

async def weekly_summary(context) -> None:
    # Пример сбора статистики из файла
    import pandas as pd
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
