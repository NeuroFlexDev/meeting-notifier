import datetime
import logging
from telegram.ext import ContextTypes
from bot.logger import log_poll_result
from bot.meeting import send_meeting_notification

logger = logging.getLogger(__name__)

async def poll_handler(update, context: ContextTypes.DEFAULT_TYPE) -> None:
    poll = update.poll
    # Если опрос еще открыт, не обрабатываем
    if not poll.is_closed:
        return

    poll_id = poll.id
    pending_meetings = context.bot_data.get("pending_meetings", {})
    if poll_id not in pending_meetings:
        return

    meeting = pending_meetings.pop(poll_id)

    # Определяем вариант с максимальным числом голосов
    winning_option = None
    max_votes = -1
    for option in poll.options:
        if option.voter_count > max_votes:
            max_votes = option.voter_count
            winning_option = option.text

    # Если ни один вариант не получил голосов – выбираем первый
    if max_votes == 0:
        winning_option = meeting["options"].split(";")[0]

    try:
        final_time = datetime.datetime.strptime(winning_option, "%Y-%m-%d %H:%M")
    except ValueError:
        logger.error("Неверный формат финального времени из опроса.")
        return

    closed_at = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    poll_result = {
        "poll_id": poll_id,
        "winning_option": winning_option,
        "votes": max_votes,
        "final_time": final_time.strftime("%Y-%m-%d %H:%M"),
        "closed_at": closed_at,
    }
    log_poll_result(poll_result)

    now = datetime.datetime.now()
    if final_time < now:
        final_time += datetime.timedelta(days=1)
    delta = (final_time - now).total_seconds()

    # Планируем уведомление, передавая данные в job_queue, включая thread_id (если указан)
    context.job_queue.run_once(
        send_meeting_notification,
        when=delta,
        context={
            "chat_ids": context.bot_data.get("chat_ids"),
            "meeting_topic": meeting["topic"],
            "meeting_link": meeting["link"],
            "final_time": final_time.strftime("%Y-%m-%d %H:%M"),
            "thread_id": meeting.get("thread_id"),
        }
    )

    # Отправляем сообщение с итогом опроса в первый чат
    target_chat = context.bot_data.get("chat_ids")[0]
    await context.bot.send_message(
        chat_id=target_chat,
        text=f"Опрос завершён! Финальное время встречи: {final_time.strftime('%Y-%m-%d %H:%M')}\n"
             "Уведомление будет отправлено во все группы."
    )
