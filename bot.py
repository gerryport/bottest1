import logging
import os

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    filters,
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
# Настройки из переменных окружения (задаются в Railway → Variables)
# ---------------------------------------------------------------------------
BOT_TOKEN = os.environ.get("BOT_TOKEN")

# Числовой Telegram ID менеджера/админа, которому будут пересылаться документы.
# Узнать свой ID можно у @userinfobot. Бот и админ должны хотя бы раз
# написать друг другу /start, иначе Telegram не даст боту написать первым.
ADMIN_ID = os.environ.get("ADMIN_ID")

# Ссылка на чат с менеджером для кнопки "Контакты"
MANAGER_CHAT_URL = os.environ.get("MANAGER_CHAT_URL", "https://t.me/your_manager")

# Состояния диалога верификации
SELFIE, PASSPORT = range(2)


def build_main_menu() -> InlineKeyboardMarkup:
    """Клавиатура главного меню."""
    keyboard = [
        [InlineKeyboardButton("🪪 Пройти верификацию", callback_data="verify")],
        [InlineKeyboardButton("📇 Контакты", url=MANAGER_CHAT_URL)],
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
    """Обработчик нажатий на inline-кнопки, не относящиеся к верификации."""
    query = update.callback_query
    await query.answer()

    if query.data == "help":
        text = (
            "❓ Доступные команды:\n"
            "/start — показать главное меню\n"
            "/cancel — отменить верификацию"
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


# ---------------------------------------------------------------------------
# Верификация: бот принимает селфи и паспорт и пересылает их админу вручную
# ---------------------------------------------------------------------------

async def start_verification(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Начало верификации — честно объясняем, что будет с документами."""
    query = update.callback_query
    await query.answer()

    await query.edit_message_text(
        "🪪 Верификация\n\n"
        "Для верификации потребуется:\n"
        "1) Селфи;\n"
        "2) Фото паспорта (разворот с фото и данными).\n\n"
        "Документы проходят проверку  через лицензированный KYC-провайдер "
        "Фотографии документов должны быть четкими, качественными и не размытыми.\n\n"
        "Пришлите, пожалуйста, селфи. Отменить — /cancel"
    )
    return SELFIE


async def receive_selfie(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Получаем селфи и просим паспорт."""
    context.user_data["selfie_file_id"] = update.message.photo[-1].file_id

    await update.message.reply_text(
        "✅ Селфи получено.\n\n"
        "Теперь пришлите фото паспорта (разворот с фото и данными)."
    )
    return PASSPORT


async def receive_passport(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Получаем паспорт, пересылаем оба документа админу, завершаем диалог."""
    if update.message.photo:
        passport_file_id = update.message.photo[-1].file_id
        passport_is_photo = True
    else:
        passport_file_id = update.message.document.file_id
        passport_is_photo = False

    user = update.effective_user
    selfie_file_id = context.user_data.get("selfie_file_id")

    if not ADMIN_ID:
        logger.error("ADMIN_ID не задан — некому переслать документы верификации")
        await update.message.reply_text(
            "⚠️ Извините, сейчас верификация недоступна. Попробуйте позже "
            "или напишите менеджеру напрямую."
        )
        context.user_data.clear()
        return ConversationHandler.END

    caption = (
        f"📋 Заявка на верификацию\n"
        f"👤 {user.first_name} {user.last_name or ''}\n"
        f"🆔 Telegram ID: {user.id}\n"
        f"🔗 Username: @{user.username or '—'}"
    )

    try:
        await context.bot.send_photo(
            chat_id=ADMIN_ID, photo=selfie_file_id, caption=f"{caption}\n\n📸 Селфи"
        )
        if passport_is_photo:
            await context.bot.send_photo(
                chat_id=ADMIN_ID, photo=passport_file_id, caption="📄 Паспорт"
            )
        else:
            await context.bot.send_document(
                chat_id=ADMIN_ID, document=passport_file_id, caption="📄 Паспорт"
            )
    except Exception as e:
        logger.error(f"Не удалось переслать документы админу: {e}")
        await update.message.reply_text(
            "⚠️ Не получилось отправить документы менеджеру. "
            "Попробуйте ещё раз позже или напишите в поддержку."
        )
        context.user_data.clear()
        return ConversationHandler.END

    await update.message.reply_text(
        "✅ Документы отправлены менеджеру на проверку.\n"
        "Как только верификация пройдёт, мы вам сообщим."
    )

    context.user_data.clear()
    return ConversationHandler.END


async def cancel_verification(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Отмена верификации."""
    context.user_data.clear()
    await update.message.reply_text(
        "❌ Верификация отменена. Начать заново — /start"
    )
    return ConversationHandler.END


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

    verification_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(start_verification, pattern="^verify$")],
        states={
            SELFIE: [MessageHandler(filters.PHOTO, receive_selfie)],
            PASSPORT: [
                MessageHandler(filters.PHOTO | filters.Document.PDF, receive_passport)
            ],
        },
        fallbacks=[CommandHandler("cancel", cancel_verification)],
    )

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", start))
    app.add_handler(verification_conv)
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(filters.COMMAND, unknown_command))

    logger.info("🤖 Бот запущен...")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
