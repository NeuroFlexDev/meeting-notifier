# Meeting Notifier

Этот репозиторий содержит пример автоматизации уведомлений о встречах, проводимых в Яндекс.Телемост, с отправкой уведомлений в Telegram и сбором базовой статистики.

## Функционал
- Отправка уведомлений о предстоящих встречах в заданный Telegram-чат.
- Планировщик задач для автоматической рассылки уведомлений.
- Пример конфигурации через файл `config.ini`.

## Требования
- Python 3.10+
- Библиотеки: python-telegram-bot, configparser

## Установка
1. Клонируйте репозиторий:
    ```bash
    git clone https://github.com/yourusername/meeting-notifier.git
    cd meeting-notifier
    ```

2. Создайте виртуальное окружение и активируйте его:
    ```bash
    python -m venv venv
    source venv/bin/activate  # для Linux/macOS
    venv\Scripts\activate     # для Windows
    ```

3. Установите зависимости:
    ```bash
    pip install -r requirements.txt
    ```

4. Создайте файл конфигурации, скопировав `config.example.ini` в `config.ini` и заполнив необходимые поля:
    ```bash
    cp config.example.ini config.ini
    ```

5. Запустите бота:
    ```bash
    python bot.py
    ```

## Настройка уведомлений
Уведомления отправляются ежедневно в заданное время (по умолчанию 09:00). В файле `bot.py` можно изменить логику отправки или добавить загрузку расписания встреч из базы данных или файла.

## Статистика
В данном примере базовая логика уведомлений. Для сбора статистики можно расширить функционал:
- Записывать в лог факт отправки уведомлений.
- Реализовать редирект-ссылку для отслеживания кликов.
- При наличии API Яндекс.Телемоста автоматизировать сбор данных о посещаемости встречи.
