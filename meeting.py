import configparser
import datetime
import logging
from telegram import ReplyKeyboardMarkup, ReplyKeyboardRemove, Update
from telegram.ext import ContextTypes, ConversationHandler
from logger import log_meeting

logger = logging.getLogger(__name__)

# Состояния диалога:
# 0 - TOPIC: ввод темы встречи
# 1 - LINK: ввод ссылки на встречу
# 2 - THREAD: ввод ID топика (опционально)
# 3 - POLL_DURATION: выбор длительности опроса (в секундах)
# 4 - TIME_OPTION: ввод одного варианта времени встречи
# 5 - PARTICIPANTS: выбор участников для упоминания
# 6 - CREATE_POLL: финальное создание опроса
TOPIC, LINK, THREAD, POLL_DURATION, TIME_OPTION, PARTICIPANTS, CREATE_POLL = range(7)

# Предустановленные варианты длительности опроса (в секундах)
POLL_DURATION_OPTIONS = [["30", "60", "120"], ["300", "600"]]

async def schedule_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text("Введите тему встречи:")
    return TOPIC

async def schedule_topic(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data['meeting_topic'] = update.message.text
    await update.message.reply_text("Введите ссылку на встречу (например, на Яндекс.Телемост):")
    return LINK

async def schedule_link(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data['meeting_link'] = update.message.text
    await update.message.reply_text(
        "Введите ID топика для уведомления (если нужно отправлять в конкретный топик, иначе оставьте пустым):"
    )
    return THREAD

async def schedule_thread(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    text = update.message.text.strip()
    context.user_data['thread_id'] = text if text else None
    reply_markup = ReplyKeyboardMarkup(POLL_DURATION_OPTIONS, one_time_keyboard=True, resize_keyboard=True)
    await update.message.reply_text(
        "Выберите длительность опроса (в секундах):",
        reply_markup=reply_markup,
    )
    return POLL_DURATION

async def schedule_poll_duration(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    duration_str = update.message.text.strip()
    try:
        duration = int(duration_str)
    except ValueError:
        await update.message.reply_text("Неверное значение. Введите число (в секундах).")
        return POLL_DURATION

    context.user_data['poll_duration'] = duration
    context.user_data['time_options'] = []  # инициализируем список вариантов времени
    await update.message.reply_text(
        "Введите вариант времени встречи в формате YYYY-MM-DD HH:MM.\n"
        "После ввода выберите 'Добавить ещё' или 'Готово' для завершения.",
        reply_markup=ReplyKeyboardMarkup([["Добавить ещё", "Готово"]], one_time_keyboard=True, resize_keyboard=True)
    )
    return TIME_OPTION

async def add_time_option(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if update.message.text.strip().lower() == "готово":
        if not context.user_data.get('time_options'):
            await update.message.reply_text("Вы не ввели ни одного варианта времени. Попробуйте снова.")
            return TIME_OPTION

        chat_ids = context.bot_data.get("chat_ids", [])
        if not chat_ids:
            await update.message.reply_text("Нет заданных чатов для получения участников.")
            return ConversationHandler.END
        
        group_chat_id = chat_ids[0]  # Можно использовать первый чат из списка
        try:
            admins = await context.bot.get_chat_administrators(chat_id=group_chat_id)
            participants = []
            for admin in admins:
                user = admin.user
                if user.username:
                    participants.append(f"@{user.username}")
                else:
                    participants.append(user.full_name)

            if not participants:
                await update.message.reply_text("Не удалось получить участников чата.")
                return ConversationHandler.END
            
            context.user_data['available_participants'] = participants
            options_str = ", ".join(participants)
            await update.message.reply_text(
                f"Доступные участники:\n{options_str}\n\n"
                "Выберите участников для уведомления, отправив через запятую их имена (например, @ivanov, @petrov).\n"
                "Если хотите уведомить всех, оставьте поле пустым."
            )
            return PARTICIPANTS

        except Exception as e:
            await update.message.reply_text("Не удалось получить участников группы.")
            logger.error(f"Ошибка получения администраторов: {e}")
            return ConversationHandler.END
    else:
        option_text = update.message.text.strip()
        try:
            datetime.datetime.strptime(option_text, "%Y-%m-%d %H:%M")
            context.user_data['time_options'].append(option_text)
        except ValueError:
            await update.message.reply_text("Неверный формат времени. Введите время в формате YYYY-MM-DD HH:MM.")
            return TIME_OPTION

        await update.message.reply_text(
            "Вариант добавлен. Добавьте ещё вариант или выберите 'Готово'.",
            reply_markup=ReplyKeyboardMarkup([["Добавить ещё", "Готово"]], one_time_keyboard=True, resize_keyboard=True)
        )
        return TIME_OPTION

async def choose_participants(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    text = update.message.text.strip()
    if text:
        # Разбиваем введённую строку по запятым и очищаем пробелы
        chosen = [name.strip() for name in text.split(",") if name.strip()]
        # Фильтруем по доступным участникам
        available = context.user_data.get('available_participants', [])
        valid = [name for name in chosen if name in available]
        context.user_data['participants'] = valid
    else:
        context.user_data['participants'] = []  # пустой список означает уведомить всех (или никого)
    return await create_poll(update, context)

async def create_poll(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    valid_options = context.user_data.get('time_options', [])
    poll_duration = context.user_data.get('poll_duration', 60)

    # 🔥 Проверяем, есть ли минимум 2 варианта для опроса
    if len(valid_options) < 2:
        await update.message.reply_text(
            "Ошибка: нужно добавить как минимум 2 варианта времени встречи! Введите еще одно время."
        )
        return TIME_OPTION  # Возвращаемся к вводу вариантов времени

    config = configparser.ConfigParser()
    config.read('config.ini')
    chat_ids_raw = config['TELEGRAM']['CHAT_IDS']
    chat_ids = [chat.strip() for chat in chat_ids_raw.split(",") if chat.strip()]
    context.bot_data["chat_ids"] = chat_ids

    target_chat = chat_ids[0]
    thread_id = context.user_data.get("thread_id")

    if thread_id is not None:
        try:
            thread_id = int(thread_id)
        except ValueError:
            logger.warning(f"⚠️ Ошибка преобразования thread_id: {thread_id}. Пропускаем.")
            thread_id = None  

    # Отправляем опрос
    if thread_id:
        poll_message = await context.bot.send_poll(
            chat_id=target_chat,
            message_thread_id=thread_id,
            question="Выберите удобное время для встречи",
            options=valid_options,
            is_anonymous=False,
            open_period=poll_duration
        )
    else:
        poll_message = await context.bot.send_poll(
            chat_id=target_chat,
            question="Выберите удобное время для встречи",
            options=valid_options,
            is_anonymous=False,
            open_period=poll_duration
        )

    poll_id = poll_message.poll.id

    meeting_data = {
        "poll_id": poll_id,
        "topic": context.user_data.get("meeting_topic"),
        "link": context.user_data.get("meeting_link"),
        "thread_id": thread_id,
        "created_at": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "options": ";".join(valid_options),
        "proposed_by": update.effective_user.id,
        "participants": ", ".join(context.user_data.get("participants", []))
    }
    context.bot_data.setdefault("pending_meetings", {})[poll_id] = meeting_data
    log_meeting(meeting_data)

    if meeting_data["participants"]:
        await context.bot.send_message(
            chat_id=target_chat,
            text=f"Приглашенные участники: {meeting_data['participants']}"
        )

    await update.message.reply_text(
        "Ваши данные сохранены. Опрос запущен, и после его закрытия будет выбрано финальное время встречи.",
        reply_markup=ReplyKeyboardRemove()
    )
    return ConversationHandler.END

async def send_meeting_notification(context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Отправляет уведомление о встрече по расписанию.
    Ожидается, что в context.job.context переданы:
      - chat_ids: список чатов,
      - meeting_topic: тема встречи,
      - meeting_link: ссылка,
      - final_time: финальное время встречи,
      - thread_id: (опционально) ID топика,
      - participants: строка с выбранными участниками (для упоминания).
    """
    job_context = context.job.context
    meeting_topic = job_context.get("meeting_topic")
    meeting_link = job_context.get("meeting_link")
    final_time = job_context.get("final_time")
    chat_ids = job_context.get("chat_ids", [])
    thread_id = job_context.get("thread_id")
    participants = job_context.get("participants", "")
    text = (
        f"Напоминаем о встрече!\n"
        f"Тема: {meeting_topic}\n"
        f"Ссылка: {meeting_link}\n"
        f"Время встречи: {final_time}"
    )
    if participants:
        text += f"\nПриглашены: {participants}"
    
    for chat_id in chat_ids:
        if thread_id:
            await context.bot.send_message(chat_id=chat_id, text=text, message_thread_id=int(thread_id))
            logger.info(f"Уведомление отправлено в чат {chat_id} в топике {thread_id}")
        else:
            await context.bot.send_message(chat_id=chat_id, text=text)
            logger.info(f"Уведомление отправлено в чат {chat_id}")
