import logging
import os

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
)

# ---------------------------------------------------------------------------
# Логирование
# ---------------------------------------------------------------------------
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Токен бота берём из переменной окружения (задаётся в настройках Railway)
# ---------------------------------------------------------------------------
BOT_TOKEN = os.environ.get("BOT_TOKEN")


def build_main_menu() -> InlineKeyboardMarkup:
    """Клавиатура главного меню."""
    keyboard = [
        [InlineKeyboardButton("ℹ️ О нас", callback_data="about")],
        [InlineKeyboardButton("❓ Помощь", callback_data="help")],
    ]
    return InlineKeyboardMarkup(keyboard)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик команды /start — приветствие и кнопки."""
    user = update.effective_user

    welcome_text = (
        f"👋 Привет, {user.first_name}!\n\n"
        "Добро пожаловать в бота.\n"
        "Выберите действие ниже 👇"
    )

    await update.message.reply_text(welcome_text, reply_markup=build_main_menu())


async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик нажатий на inline-кнопки."""
    query = update.callback_query
    await query.answer()

    if query.data == "about":
        text = "ℹ️ Здесь будет текст о вашем проекте/сообществе."
    elif query.data == "help":
        text = (
            "❓ Доступные команды:\n"
            "/start — показать главное меню"
        )
    else:
        text = "Неизвестное действие."

    back_button = InlineKeyboardMarkup(
        [[InlineKeyboardButton("⬅️ Назад", callback_data="back")]]
    )

    if query.data == "back":
        await query.edit_message_text(
            f"👋 С возвращением, {query.from_user.first_name}!\n\n"
            "Выберите действие ниже 👇",
            reply_markup=build_main_menu(),
        )
    else:
        await query.edit_message_text(text, reply_markup=back_button)


async def unknown_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Ответ на неизвестные команды."""
    await update.message.reply_text(
        "❓ Неизвестная команда.\n\nДоступные команды:\n/start — главное меню"
    )


def main() -> None:
    if not BOT_TOKEN:
        raise RuntimeError(
            "Переменная окружения BOT_TOKEN не задана. "
            "Добавьте её в настройках Railway (Variables)."
        )

    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(CommandHandler("help", start))

    logger.info("🤖 Бот запущен...")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
