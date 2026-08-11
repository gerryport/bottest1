import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ChatAction
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, ConversationHandler
from telegram.constants import ParseMode
import os
from datetime import datetime

# Включаем логирование
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Состояния для ConversationHandler
START, SELFIE, PASSPORT, UPLOAD_PROGRESS = range(4)

# ID админа для получения данных верификации (замените на свой ID)
ADMIN_ID = YOUR_ADMIN_ID_HERE

class VerificationBot:
    def __init__(self, token):
        self.token = token
        self.app = Application.builder().token(token).build()
        self.user_data_storage = {}  # Временное хранилище данных пользователя
        self.setup_handlers()

    def setup_handlers(self):
        """Настройка обработчиков команд и сообщений"""
        
        # Начальная команда
        self.app.add_handler(CommandHandler("start", self.start))
        
        # Conversation Handler для процесса верификации
        conv_handler = ConversationHandler(
            entry_points=[CallbackQueryHandler(self.start_verification, pattern="^verify$")],
            states={
                SELFIE: [MessageHandler(filters.PHOTO, self.receive_selfie)],
                PASSPORT: [MessageHandler(filters.PHOTO | filters.Document.PDF, self.receive_passport)],
                UPLOAD_PROGRESS: [MessageHandler(filters.PHOTO | filters.Document.PDF, self.process_upload)]
            },
            fallbacks=[CommandHandler("cancel", self.cancel_verification)]
        )
        
        self.app.add_handler(conv_handler)
        self.app.add_handler(MessageHandler(filters.COMMAND, self.unknown_command))

    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик команды /start"""
        user = update.effective_user
        
        welcome_text = (
            f"👋 Привет, {user.first_name}!\n\n"
            "Добро пожаловать в систему верификации.\n"
            "Для продолжения нужно пройти процесс верификации личности.\n\n"
            "⏱️ Процесс займет всего 2-3 минуты"
        )
        
        keyboard = [
            [InlineKeyboardButton("✅ Начать верификацию", callback_data="verify")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(welcome_text, reply_markup=reply_markup)

    async def start_verification(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Начало процесса верификации"""
        query = update.callback_query
        await query.answer()
        
        user_id = update.effective_user.id
        self.user_data_storage[user_id] = {
            'started_at': datetime.now(),
            'selfie': None,
            'passport': None
        }
        
        await query.edit_message_text(
            text="📸 Отлично! Начнем с селфи.\n\n"
                 "Пожалуйста, загрузите ваше фото (селфи):\n"
                 "• Хорошее освещение\n"
                 "• Четкое изображение лица\n"
                 "• Никаких фильтров"
        )
        
        return SELFIE

    async def receive_selfie(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Получение селфи"""
        user_id = update.effective_user.id
        
        # Показываем прогресс загрузки
        await update.message.chat.send_action(ChatAction.TYPING)
        
        # Сохраняем фото
        photo = update.message.photo[-1]
        file_id = photo.file_id
        self.user_data_storage[user_id]['selfie'] = file_id
        
        # Показываем прогресс
        progress_message = await update.message.reply_text(
            "📤 Загрузка селфи...\n"
            "▬▬▬▬▬▬▬▬▬▬ 0%"
        )
        
        # Имитация прогресса загрузки
        import asyncio
        for i in range(1, 11):
            await asyncio.sleep(0.2)
            progress = "█" * i + "▬" * (10 - i)
            try:
                await progress_message.edit_text(
                    f"📤 Загрузка селфи...\n"
                    f"{progress} {i * 10}%"
                )
            except:
                pass
        
        await progress_message.delete()
        await update.message.reply_text(
            "✅ Селфи успешно загружено!\n\n"
            "📄 Теперь загрузите фото вашего паспорта (любая страница с данными):"
        )
        
        return PASSPORT

    async def receive_passport(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Получение фото паспорта"""
        user_id = update.effective_user.id
        
        await update.message.chat.send_action(ChatAction.TYPING)
        
        # Сохраняем фото/документ паспорта
        if update.message.photo:
            file_id = update.message.photo[-1].file_id
        else:
            file_id = update.message.document.file_id
        
        self.user_data_storage[user_id]['passport'] = file_id
        
        # Показываем прогресс
        progress_message = await update.message.reply_text(
            "📤 Загрузка паспорта...\n"
            "▬▬▬▬▬▬▬▬▬▬ 0%"
        )
        
        import asyncio
        for i in range(1, 11):
            await asyncio.sleep(0.2)
            progress = "█" * i + "▬" * (10 - i)
            try:
                await progress_message.edit_text(
                    f"📤 Загрузка паспорта...\n"
                    f"{progress} {i * 10}%"
                )
            except:
                pass
        
        await progress_message.delete()
        
        # Отправляем статус "На проверке"
        await update.message.reply_photo(
            photo="https://via.placeholder.com/400x200/FFA500/FFFFFF?text=%F0%9F%94%84+%D0%9D%D0%90+%D0%9F%D0%A0%D0%9E%D0%92%D0%95%D0%A0%D0%9A%D0%95",
            caption="⏳ Ваша верификация на проверке\n\n"
                   "Наш модератор проверит документы в течение 24 часов.\n"
                   "Вам придет уведомление о результате."
        )
        
        # Отправляем данные админу
        await self.send_to_admin(update.effective_user, user_id)
        
        return ConversationHandler.END

    async def process_upload(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка загруженных файлов"""
        await update.message.reply_text(
            "Документ уже загружен. Спасибо за вашу информацию! ✅"
        )
        return ConversationHandler.END

    async def send_to_admin(self, user, user_id):
        """Отправка данных верификации админу"""
        try:
            if ADMIN_ID != "YOUR_ADMIN_ID_HERE":
                user_data = self.user_data_storage.get(user_id, {})
                
                message = (
                    f"📋 Новая заявка на верификацию\n\n"
                    f"👤 Пользователь: {user.first_name} {user.last_name or ''}\n"
                    f"🆔 ID: {user_id}\n"
                    f"⏰ Время: {datetime.now().strftime('%d.%m.%Y %H:%M')}\n\n"
                    f"📸 Селфи загружено: {'✅' if user_data.get('selfie') else '❌'}\n"
                    f"📄 Паспорт загружен: {'✅' if user_data.get('passport') else '❌'}"
                )
                
                # Здесь нужно отправить сообщение админу
                logger.info(f"Заявка на верификацию от пользователя {user_id}")
        except Exception as e:
            logger.error(f"Ошибка при отправке админу: {e}")

    async def cancel_verification(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Отмена процесса верификации"""
        user_id = update.effective_user.id
        
        if user_id in self.user_data_storage:
            del self.user_data_storage[user_id]
        
        await update.message.reply_text(
            "❌ Процесс верификации отменен.\n"
            "Вы можете начать заново командой /start"
        )
        
        return ConversationHandler.END

    async def unknown_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик неизвестных команд"""
        await update.message.reply_text(
            "❓ Неизвестная команда.\n\n"
            "Доступные команды:\n"
            "/start - Начало верификации\n"
            "/cancel - Отмена процесса"
        )

    def run(self):
        """Запуск бота"""
        logger.info("🤖 Бот запущен...")
        self.app.run_polling()


if __name__ == "__main__":
    # ВАЖНО: Замените на ваш токен от BotFather
    BOT_TOKEN = "YOUR_BOT_TOKEN_HERE"
    
    # Замените на ID вашего аккаунта Telegram (для получения заявок)
    # Узнать свой ID можно у бота @userinfobot
    ADMIN_ID = "YOUR_ADMIN_ID_HERE"
    
    if BOT_TOKEN == "YOUR_BOT_TOKEN_HERE":
        print("❌ Ошибка: Установите BOT_TOKEN!")
        print("1. Напишите @BotFather в Telegram")
        print("2. Создайте нового бота и скопируйте токен")
        print("3. Вставьте токен в переменную BOT_TOKEN")
        exit(1)
    
    bot = VerificationBot(BOT_TOKEN)
    bot.run()
