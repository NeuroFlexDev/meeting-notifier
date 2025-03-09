import logging
from telegram import Update
from telegram.ext import ContextTypes, CommandHandler

logger = logging.getLogger(__name__)

async def help_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Отправляет меню с описанием всех доступных команд.
    """
    help_text = "Доступные команды:\n\n"
    commands = {}

    try:
        # Проходим по всем группам хендлеров, зарегистрированных в приложении
        for group in context.application.handlers.values():
            for handler in group:
                # Если хендлер является экземпляром CommandHandler
                if isinstance(handler, CommandHandler):
                    # Используем атрибут commands (во множественном числе)
                    for cmd in handler.commands:
                        description = handler.callback.__doc__
                        if description:
                            description = description.strip().splitlines()[0]
                        else:
                            description = "Нет описания"
                        commands[cmd] = description

        if not commands:
            help_text += "Команды не найдены."
        else:
            for cmd in sorted(commands.keys()):
                help_text += f"/{cmd} - {commands[cmd]}\n"
    except Exception as e:
        logger.error("Ошибка при сборе команд для /help: %s", e)
        help_text = "Ошибка при сборе команд для помощи."

    await update.message.reply_text(help_text)
