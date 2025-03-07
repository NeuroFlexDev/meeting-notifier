# Используем официальный базовый образ Python
FROM python:3.10

# Устанавливаем рабочую директорию
WORKDIR /app

# Копируем все файлы проекта в контейнер
COPY . /app

# Обновляем pip и устанавливаем зависимости из requirements.txt
RUN pip install --upgrade pip && \
    pip install -r requirements.txt

# Устанавливаем Supervisor
RUN apt-get update && apt-get install -y supervisor && rm -rf /var/lib/apt/lists/*

# Копируем файл конфигурации Supervisor
COPY supervisord.conf /etc/supervisor/conf.d/supervisord.conf

# Открываем порт для Streamlit (по умолчанию 8501)
EXPOSE 8501

# Запускаем Supervisor, который будет управлять обоими процессами
CMD ["/usr/bin/supervisord", "-c", "/etc/supervisor/conf.d/supervisord.conf"]
