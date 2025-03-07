import pandas as pd
import streamlit as st
from collections import Counter
import nltk
from nltk.corpus import stopwords
from wordcloud import WordCloud
import matplotlib.pyplot as plt
import numpy as np
import re
import requests
import configparser
from PIL import Image

# Загрузка конфигурации
config = configparser.ConfigParser()
config.read("config.ini", encoding="utf-8")
BOT_TOKEN = config["TELEGRAM"]["BOT_TOKEN"]
CHAT_IDS = [int(chat.strip()) for chat in config["TELEGRAM"]["CHAT_IDS"].split(",") if chat.strip()]

# Загрузка данных
nltk.download("stopwords")
stop_words = set(stopwords.words("russian"))

def load_chat_data():
    try:
        df = pd.read_csv("chat_activity.csv", names=["timestamp", "user_id", "username", "message"])
        return df
    except FileNotFoundError:
        st.error("Файл chat_activity.csv не найден.")
        return pd.DataFrame(columns=["timestamp", "user_id", "username", "message"])

# Очистка текста
def clean_text(text):
    text = re.sub(r"[^\w\s]", "", text.lower())
    words = text.split()
    return [word for word in words if word not in stop_words and len(word) > 2]

# Анализ популярных слов
def analyze_trends(df):
    if df.empty:
        return {}
    all_words = []
    for message in df["message"].dropna():
        all_words.extend(clean_text(message))
    return dict(Counter(all_words).most_common(50))

# Отправка статистики в Telegram
def send_trends_to_telegram(word_freq):
    if not word_freq:
        return
    
    text = "📊 *Тренды обсуждений в чатах:*\n"
    for word, count in word_freq.items():
        text += f"🔹 {word}: {count} раз\n"
    
    for chat_id in CHAT_IDS:
        requests.post(
            f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
            json={"chat_id": chat_id, "text": text, "parse_mode": "Markdown"}
        )

# Генерация облака слов в форме слова NeuroFlex
def generate_neuroflex_wordcloud(word_freq):
    mask = np.array(Image.open("neuroflex_mask.png"))  # Используем изображение с формой текста "NeuroFlex"
    wordcloud = WordCloud(width=800, height=400, background_color="white", mask=mask, contour_width=3, contour_color='black')
    wordcloud.generate_from_frequencies(word_freq)
    return wordcloud

# Streamlit UI
st.title("5️⃣ Тренды обсуждений в чатах")
df = load_chat_data()
word_freq = analyze_trends(df)

if word_freq:
    st.subheader("📌 Самые популярные темы")
    st.write(pd.DataFrame(word_freq.items(), columns=["Слово", "Частота"]))
    
    # Генерация облака слов
    st.subheader("☁ Облако слов в форме 'NeuroFlex'")
    wordcloud = generate_neuroflex_wordcloud(word_freq)
    fig, ax = plt.subplots()
    ax.imshow(wordcloud, interpolation="bilinear")
    ax.axis("off")
    st.pyplot(fig)
    
    if st.button("📤 Отправить тренды в Telegram"):
        send_trends_to_telegram(word_freq)
        st.success("Статистика отправлена!")
else:
    st.write("Нет данных для анализа.")
