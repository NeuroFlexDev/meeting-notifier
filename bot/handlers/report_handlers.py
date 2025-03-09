from telegram import Update
from telegram.ext import ContextTypes

# Импортируем функции генерации отчётов из модуля с интеграцией HuggingChat
from bot.huggingchat_client import noon_report, weekly_summary

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
