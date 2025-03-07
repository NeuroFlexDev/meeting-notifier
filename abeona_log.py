# github_and_trends.py

import requests
import pandas as pd
import matplotlib.pyplot as plt
import io
import configparser
import re
from collections import Counter
from wordcloud import WordCloud
import numpy as np
from PIL import Image
import nltk
from nltk.corpus import stopwords

# Обязательно загрузить список стоп-слов, если еще не загружен
nltk.download("stopwords", quiet=True)
stop_words = set(stopwords.words("russian"))


# ============ Функции для статистики GitHub ============

def fetch_github_repos(org_name: str):
    """
    Получает список репозиториев для указанной организации GitHub.
    
    :param org_name: Имя организации на GitHub.
    :return: JSON-список репозиториев.
    :raises Exception: Если запрос завершился с ошибкой.
    """
    GITHUB_API_URL = f"https://api.github.com/orgs/{org_name}/repos"
    response = requests.get(GITHUB_API_URL)
    if response.status_code == 200:
        return response.json()
    else:
        raise Exception(f"Ошибка загрузки данных GitHub: {response.status_code}")


def analyze_github_stats(repos):
    """
    Анализирует список репозиториев и возвращает DataFrame со статистикой.
    
    :param repos: JSON-данные репозиториев.
    :return: DataFrame с колонками: 'Название', 'Звезды', 'Форки', 'Открытые Issues', 'Последнее обновление'
    """
    data = []
    for repo in repos:
        data.append({
            "Название": repo.get("name", ""),
            "Звезды": repo.get("stargazers_count", 0),
            "Форки": repo.get("forks_count", 0),
            "Открытые Issues": repo.get("open_issues_count", 0),
            "Последнее обновление": repo.get("updated_at", "")
        })
    return pd.DataFrame(data)


def generate_github_bar_chart(df: pd.DataFrame, column: str, title: str) -> io.BytesIO:
    """
    Генерирует столбчатую диаграмму для указанной колонки DataFrame и возвращает изображение в виде буфера.
    
    :param df: DataFrame со статистикой репозиториев.
    :param column: Название колонки для построения диаграммы.
    :param title: Заголовок графика.
    :return: Буфер с изображением графика (PNG).
    """
    fig, ax = plt.subplots()
    df_sorted = df.sort_values(by=column, ascending=False)
    ax.bar(df_sorted["Название"], df_sorted[column])
    ax.set_title(title)
    ax.set_xlabel("Репозиторий")
    ax.set_ylabel(column)
    plt.xticks(rotation=45, ha="right")
    
    buf = io.BytesIO()
    plt.tight_layout()
    fig.savefig(buf, format="png")
    buf.seek(0)
    plt.close(fig)
    return buf


# ============ Функции для трендов и WordCloud ============

def load_chat_activity(file_path: str = "chat_activity.csv") -> pd.DataFrame:
    """
    Загружает данные активности чата из CSV и возвращает DataFrame.
    
    :param file_path: Путь к файлу с логами чата.
    :return: DataFrame с колонками: timestamp, user_id, username, message.
    """
    try:
        df = pd.read_csv(file_path, names=["timestamp", "user_id", "username", "message"])
        return df
    except FileNotFoundError:
        return pd.DataFrame(columns=["timestamp", "user_id", "username", "message"])


def clean_text(text: str) -> list:
    """
    Очищает текст: удаляет знаки препинания, приводит к нижнему регистру и убирает стоп-слова.
    
    :param text: Исходный текст.
    :return: Список очищенных слов.
    """
    text = re.sub(r"[^\w\s]", "", text.lower())
    words = text.split()
    return [word for word in words if word not in stop_words and len(word) > 2]


def analyze_trends(df: pd.DataFrame) -> dict:
    """
    Анализирует сообщения из чата и возвращает словарь с 50 наиболее частыми словами.
    
    :param df: DataFrame с данными активности чата.
    :return: Словарь {слово: частота}.
    """
    if df.empty:
        return {}
    all_words = []
    for message in df["message"].dropna():
        all_words.extend(clean_text(message))
    return dict(Counter(all_words).most_common(50))


def generate_neuroflex_wordcloud(word_freq: dict, mask_image_path: str = "neuroflex_mask.png") -> io.BytesIO:
    """
    Генерирует облако слов в форме изображения (маска) и возвращает изображение в виде буфера.
    
    :param word_freq: Словарь частот слов.
    :param mask_image_path: Путь к изображению-маске (например, с логотипом).
    :return: Буфер с изображением облака слов (PNG).
    :raises Exception: Если не удалось загрузить изображение-маску.
    """
    try:
        mask = np.array(Image.open(mask_image_path))
    except Exception as e:
        raise Exception(f"Ошибка загрузки маски: {e}")
    
    wordcloud = WordCloud(width=800, height=400, background_color="white",
                          mask=mask, contour_width=3, contour_color='black')
    wordcloud.generate_from_frequencies(word_freq)
    
    buf = io.BytesIO()
    wordcloud.to_image().save(buf, format="PNG")
    buf.seek(0)
    return buf

# abeona_log.py

import io
import logging
import configparser
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
from abeona_log import (
    fetch_github_repos,
    analyze_github_stats,
    generate_github_bar_chart,
    load_chat_activity,
    analyze_trends,
    generate_neuroflex_wordcloud
)

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Хендлер для статистики GitHub
async def github_stats_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Обрабатывает команду /github_stats и отправляет статистику репозиториев GitHub.
    """
    try:
        # Здесь задайте название организации (например, "NeuroFlexDev")
        repos = fetch_github_repos("NeuroFlexDev")
        df = analyze_github_stats(repos)
        buf = generate_github_bar_chart(df, "Звезды", "Популярность по звездам")
        await update.message.reply_photo(photo=buf, caption="Статистика репозиториев GitHub")
    except Exception as e:
        logger.error(f"Ошибка получения статистики GitHub: {e}")
        await update.message.reply_text(f"Ошибка получения статистики GitHub: {e}")

# Хендлер для генерации wordcloud с трендами
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

