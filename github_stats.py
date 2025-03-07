import requests
import pandas as pd
import streamlit as st

# Конфигурация
ORG_NAME = "NeuroFlexDev"
GITHUB_API_URL = f"https://api.github.com/orgs/{ORG_NAME}/repos"

# Функция для загрузки статистики по репозиториям
def fetch_github_repos():
    response = requests.get(GITHUB_API_URL)
    if response.status_code == 200:
        return response.json()
    else:
        st.error(f"Ошибка загрузки данных: {response.status_code}")
        return []

# Функция для анализа статистики по репозиториям
def analyze_github_stats(repos):
    data = []
    for repo in repos:
        data.append({
            "Название": repo["name"],
            "Звезды": repo["stargazers_count"],
            "Форки": repo["forks_count"],
            "Открытые Issues": repo["open_issues_count"],
            "Последнее обновление": repo["updated_at"]
        })
    return pd.DataFrame(data)

# Streamlit UI
st.title("📊 Статистика репозиториев NeuroFlexDev")
repos = fetch_github_repos()
if repos:
    df = analyze_github_stats(repos)
    st.dataframe(df)
    
    # График популярности репозиториев по звездам
    st.subheader("⭐ Популярность по звездам")
    st.bar_chart(df.set_index("Название")["Звезды"])
    
    # График активности по Issues
    st.subheader("🐛 Количество открытых Issues")
    st.bar_chart(df.set_index("Название")["Открытые Issues"])
