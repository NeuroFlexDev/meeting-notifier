import csv
import os
import datetime

# Пути к CSV-файлам для логирования
MEETINGS_LOG = "meetings.csv"
POLL_RESULTS_LOG = "poll_results.csv"

# Функция логирования активности в чате
def log_chat_activity(user_id, username, message):
    if not username:
        username = f"User_{user_id}"  # Если username нет, используем ID с префиксом

    with open("chat_activity.csv", "a", encoding="utf-8", newline="") as file:
        writer = csv.writer(file)
        writer.writerow([datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"), user_id, username, message])


def log_meeting(meeting_data: dict):
    """Логирует информацию о встрече в meetings.csv."""
    file_exists = os.path.isfile(MEETINGS_LOG)
    with open(MEETINGS_LOG, mode="a", newline="", encoding="utf-8") as file:
        # Добавляем поле thread_id
        fieldnames = ["poll_id", "topic", "link", "thread_id", "created_at", "options", "proposed_by", "participants"]

        writer = csv.DictWriter(file, fieldnames=fieldnames)
        if not file_exists:
            writer.writeheader()
        writer.writerow(meeting_data)

def log_poll_result(poll_data: dict):
    """Логирует результаты опроса в poll_results.csv."""
    file_exists = os.path.isfile(POLL_RESULTS_LOG)
    with open(POLL_RESULTS_LOG, mode="a", newline="", encoding="utf-8") as file:
        fieldnames = ["poll_id", "winning_option", "votes", "final_time", "closed_at"]
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        if not file_exists:
            writer.writeheader()
        writer.writerow(poll_data)
