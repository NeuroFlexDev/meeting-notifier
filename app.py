import streamlit as st
import pandas as pd
import csv
import requests
import configparser
import datetime
from collections import Counter
from telegram import Bot
import matplotlib.pyplot as plt
import re

# Загрузка конфигурации
config = configparser.ConfigParser()
config.read("config.ini", encoding="utf-8")
BOT_TOKEN = config["TELEGRAM"]["BOT_TOKEN"]
CHAT_IDS = [int(chat.strip()) for chat in config["TELEGRAM"]["CHAT_IDS"].split(",") if chat.strip()]
bot = Bot(token=BOT_TOKEN)

# ================================================
# Функции для управления встречами (meetings)
# ================================================

def load_meetings():
    try:
        return pd.read_csv("meetings.csv")
    except FileNotFoundError:
        return pd.DataFrame(columns=["poll_id", "topic", "link", "thread_id", "created_at", "options", "proposed_by", "participants"])

def save_meetings(df):
    df.to_csv("meetings.csv", index=False)

def send_reminder(meeting):
    text = (
        f"🔔 **Напоминание о встрече!**\n"
        f"📌 **Тема:** {meeting['topic']}\n"
        f"🔗 **Ссылка:** {meeting['link']}"
    )
    for chat_id in CHAT_IDS:
        requests.post(
            f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
            json={"chat_id": chat_id, "text": text, "parse_mode": "Markdown"}
        )

# ================================================
# Функции для сбора статистики (stats)
# ================================================

def load_chat_activity():
    """Загружаем логи активности чатов, корректно парся CSV с кавычками."""
    try:
        with open("chat_activity.csv", "r", encoding="utf-8") as file:
            reader = csv.reader(file, quotechar='"', delimiter=',')
            return [row for row in reader if len(row) >= 3]  # 🔥 Фильтр на минимум 3 элемента
    except FileNotFoundError:
        return []

def escape_markdown(text):
    """Экранирует специальные символы Markdown для Telegram"""
    if not text:
        return "Нет данных"
    
    escape_chars = r'_*[]()~`>#+-=|{}.!'
    
    # Экранируем все проблемные символы
    return re.sub(r'([{}])'.format(re.escape(escape_chars)), r'\\\1', str(text))

def send_message(chat_id, text):
    """Отправляет сообщение в Telegram, экранируя Markdown"""
    if not text.strip():
        print("❌ Ошибка: Пустое сообщение. Отправка отменена.")
        return

    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "MarkdownV2"
    }

    try:
        response = requests.post(url, json=payload)
        response.raise_for_status()
        print(f"✅ Успешно отправлено в Telegram: {response.json()}")
    except requests.exceptions.HTTPError as e:
        print(f"❌ Ошибка HTTP при отправке: {e}")
        print(f"📩 Ответ сервера: {response.text}")  # Показываем ответ Telegram
    except requests.exceptions.RequestException as e:
        print(f"❌ Ошибка отправки в Telegram: {e}")

def load_meetings():
    try:
        return pd.read_csv("meetings.csv")
    except FileNotFoundError:
        return pd.DataFrame(columns=["poll_id", "topic", "link", "thread_id", "created_at", "options", "proposed_by", "participants"])

def load_chat_activity():
    try:
        with open("chat_activity.csv", "r", encoding="utf-8") as file:
            return [line.strip().split(",") for line in file.readlines()]
    except FileNotFoundError:
        return []

def send_stats_to_telegram():
    df = load_meetings()
    activity = load_chat_activity()

    # Подсчет встреч
    meeting_counts = df["proposed_by"].value_counts().to_dict() if not df.empty else {}
    top_meeting_creator = max(meeting_counts, key=meeting_counts.get, default="Никто")
    total_meetings = str(len(df))  # 🔥 Преобразуем в строку

    # Подсчет сообщений в чатах
    chat_activity_counts = Counter(row[2] for row in activity if len(row) >= 4)
    most_active_user = max(chat_activity_counts, key=chat_activity_counts.get, default="Нет данных")
    total_messages = str(sum(chat_activity_counts.values()))  # 🔥 Преобразуем в строку
    # # 🔥 Проверяем, есть ли вообще данные
    # if total_meetings == 0 and total_messages == 0:
    #     print("❌ Нет данных для отправки статистики.")
    #     return

    # 📌 Экранируем текст перед отправкой
    text = (
        f"📊 *Статистика активности*\n"
        f"📅 *Всего собраний:* {escape_markdown(total_meetings)}\n"
        f"👑 *Самый активный организатор:* {escape_markdown(str(top_meeting_creator))} \\- {escape_markdown(str(meeting_counts.get(top_meeting_creator, 0)))} встреч\n"
        f"💬 *Сообщений в чатах:* {escape_markdown(total_messages)}\n"
        f"🔥 *Самый активный участник:* {escape_markdown(str(most_active_user))} \\- {escape_markdown(str(chat_activity_counts.get(most_active_user, 0)))} сообщений"
    ).strip()

    print(f"📤 Отправляем сообщение в Telegram:\n{text}")

    for chat_id in CHAT_IDS:
        send_message(chat_id, text)
# ================================================
# Модуль логирования активности (опционально)
# ================================================
def log_chat_activity(user_id, username, message):
    if not username:
        username = f"User_{user_id}"
    with open("chat_activity.csv", "a", encoding="utf-8", newline="") as file:
        writer = csv.writer(file)
        writer.writerow([datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"), user_id, username, message])

# ================================================
# Streamlit навигация по страницам
# ================================================
st.sidebar.title("Меню")
page = st.sidebar.selectbox("Выберите раздел", ["Встречи", "Статистика", "GitHub Репозитории", "Тренды обсуждений"])

if page == "GitHub Репозитории":
    import github_stats

if page == "Тренды обсуждений":
    import chat_trends

if page == "Встречи":
    st.title("📅 Менеджер встреч")
    df = load_meetings()

    # Вывод списка встреч
    if df.empty:
        st.write("Нет запланированных встреч.")
    else:
        for index, meeting in df.iterrows():
            with st.expander(f"📌 {meeting['topic']}"):
                st.write(f"🔗 **Ссылка:** {meeting['link']}")
                st.write(f"📅 **Создано:** {meeting['created_at']}")
                col1, col2, col3 = st.columns(3)
                if col1.button("🔔 Напомнить", key=f"remind_{index}"):
                    send_reminder(meeting)
                    st.success("Напоминание отправлено!")
                if col2.button("🗑 Отменить", key=f"cancel_{index}"):
                    df.drop(index, inplace=True)
                    save_meetings(df)
                    st.rerun()
                with col3:
                    if st.button("⏳ Перенести", key=f"reschedule_{index}"):
                        st.session_state[f"reschedule_{index}"] = True
                if st.session_state.get(f"reschedule_{index}", False):
                    new_date = st.date_input("📅 Выберите новую дату", datetime.date.today(), key=f"date_{index}")
                    new_time = st.time_input("⏰ Выберите новое время", datetime.time(12, 0), key=f"time_{index}")
                    if st.button("✅ Подтвердить перенос", key=f"confirm_reschedule_{index}"):
                        df.at[index, "created_at"] = f"{new_date} {new_time}"
                        save_meetings(df)
                        st.session_state[f"reschedule_{index}"] = False
                        st.success("Время встречи изменено!")
                        st.rerun()

    # Добавление новой встречи
    st.subheader("➕ Запланировать новую встречу")
    topic = st.text_input("📌 Тема")
    link = st.text_input("🔗 Ссылка")
    date = st.date_input("📅 Выберите дату", datetime.date.today())
    time = st.time_input("⏰ Выберите время", datetime.time(12, 0))
    participants = st.text_input("👥 Участники (через запятую)")
    if st.button("✅ Создать встречу"):
        new_meeting = {
            "poll_id": len(df) + 1,
            "topic": topic,
            "link": link,
            "thread_id": "",
            "created_at": f"{date} {time}",
            "options": "",
            "proposed_by": "Streamlit",
            "participants": participants
        }
        df = pd.concat([df, pd.DataFrame([new_meeting])], ignore_index=True)
        save_meetings(df)
        st.success("Встреча добавлена!")
        st.rerun()

elif page == "Статистика":
    st.title("📊 Статистика собраний и активности")
    df = load_meetings()
    activity = load_chat_activity()

    st.subheader("📅 Статистика по собраниям")
    st.write(f"**Всего собраний:** {len(df)}")

    if not df.empty:
        st.dataframe(df[["topic", "created_at", "proposed_by"]])
        meeting_counts = df["proposed_by"].value_counts()
        fig, ax = plt.subplots()
        meeting_counts.plot(kind='bar', ax=ax, color='blue', alpha=0.7)
        ax.set_ylabel("Количество встреч")
        ax.set_xlabel("Организатор")
        ax.set_title("Активность организаторов")
        st.pyplot(fig)

    st.subheader("💬 Статистика активности в чатах")
    if activity:

        print(activity)
        chat_activity_counts = Counter(row[2] for row in activity if len(row) >= 4)


        chat_activity_df = pd.DataFrame(chat_activity_counts.items(), columns=["Пользователь", "Сообщений"])
        chat_activity_df = chat_activity_df.sort_values("Сообщений", ascending=False)

        st.dataframe(chat_activity_df)

        fig, ax = plt.subplots()
        chat_activity_df.set_index("Пользователь").plot(kind='bar', ax=ax, color='green', alpha=0.7)
        ax.set_ylabel("Количество сообщений")
        ax.set_xlabel("Пользователь")
        ax.set_title("Активность пользователей в чатах")
        st.pyplot(fig)
    else:
        st.write("Нет данных об активности в чатах.")

    if st.button("📤 Отправить статистику в Telegram"):
        send_stats_to_telegram()
        st.success("Статистика отправлена!")
