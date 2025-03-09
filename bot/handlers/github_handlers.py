import logging
from telegram import Update
from telegram.ext import ContextTypes

# Импортируем функции для получения и обработки данных GitHub и трендов
from bot.abeona_log import (
    fetch_github_repos,
    analyze_github_stats,
    generate_github_bar_chart,
    load_chat_activity,
    analyze_trends,
    generate_neuroflex_wordcloud
)

logger = logging.getLogger(__name__)

async def github_stats_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Обрабатывает команду /github_stats и отправляет расширенную статистику репозиториев GitHub,
    включая такие метрики, как звезды, форки, открытые Issues и дату последнего обновления.
    """
    try:
        # Получаем репозитории для организации "NeuroFlexDev"
        repos = fetch_github_repos("NeuroFlexDev")
        # Анализируем статистику, возвращается DataFrame с расширенными данными
        df = analyze_github_stats(repos)
        
        # Отладка: вывод доступных столбцов
        logger.info(f"Доступные столбцы: {df.columns}")
        
        # Генерация графиков для различных метрик, используя корректные имена столбцов
        stars_chart = generate_github_bar_chart(df, "Звезды", "Звезды")
        forks_chart = generate_github_bar_chart(df, "Форки", "Форки")
        issues_chart = generate_github_bar_chart(df, "Открытые Issues", "Открытые Issues")
        
        # Формирование текстовой сводки по каждому репозиторию
        summary_lines = []
        for _, row in df.iterrows():
            line = (
                f"📦 {row['Название']}\n"
                f"⭐ Звезды: {row['Звезды']} | 🍴 Форки: {row['Форки']} | ❗ Открытые Issues: {row['Открытые Issues']}\n"
                f"🔄 Последнее обновление: {row['Последнее обновление']}\n"
            )
            summary_lines.append(line)
        summary_text = "\n".join(summary_lines)
        
        # Отправляем текстовую сводку
        await update.message.reply_text(f"Расширенная статистика репозиториев GitHub:\n\n{summary_text}")
        # Отправляем графики по метрикам
        await update.message.reply_photo(photo=stars_chart, caption="Статистика: Звезды")
        await update.message.reply_photo(photo=forks_chart, caption="Статистика: Форки")
        await update.message.reply_photo(photo=issues_chart, caption="Статистика: Открытые Issues")
    except Exception as e:
        logger.error(f"Ошибка получения расширенной статистики GitHub: {e}")
        await update.message.reply_text(f"Ошибка получения расширенной статистики GitHub: {e}")

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
