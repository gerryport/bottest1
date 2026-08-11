"""
🚀 РАСШИРЕННАЯ ВЕРСИЯ БОТА С ПОДДЕРЖКОЙ БД

Дополнительно:
- Сохранение данных в SQLite
- Хранение файлов на диске
- История верификаций
- Статистика
- Уведомления админу
"""

import logging
import sqlite3
import os
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ChatAction
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, ConversationHandler, CallbackQueryHandler
from telegram.constants import ParseMode

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Состояния
START, SELFIE, PASSPORT, UPLOAD_PROGRESS = range(4)

class DatabaseManager:
    """Управление базой данных SQLite"""
    
    def __init__(self, db_name='verification.db'):
        self.db_name = db_name
        self.create_tables()
    
    def create_tables(self):
        """Создание таблиц БД"""
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()
        
        # Таблица пользователей
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                first_name TEXT,
                last_name TEXT,
                username TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Таблица верификаций
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS verifications (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                selfie_file_id TEXT,
                passport_file_id TEXT,
                selfie_path TEXT,
                passport_path TEXT,
                status TEXT DEFAULT 'pending',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(user_id)
            )
        ''')
        
        # Таблица статистики
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS statistics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                metric TEXT,
                value INTEGER,
                date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def save_user(self, user_id, first_name, last_name, username):
        """Сохранение пользователя"""
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT OR REPLACE INTO users (user_id, first_name, last_name, username)
            VALUES (?, ?, ?, ?)
        ''', (user_id, first_name, last_name, username))
        
        conn.commit()
        conn.close()
    
    def save_verification(self, user_id, selfie_id, passport_id, selfie_path, passport_path):
        """Сохранение данных верификации"""
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO verifications 
            (user_id, selfie_file_id, passport_file_id, selfie_path, passport_path, status)
            VALUES (?, ?, ?, ?, ?, 'pending')
        ''', (user_id, selfie_id, passport_id, selfie_path, passport_path))
        
        conn.commit()
        conn.close()
    
    def get_verification_status(self, user_id):
        """Получение статуса верификации"""
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT status, created_at FROM verifications
            WHERE user_id = ? ORDER BY created_at DESC LIMIT 1
        ''', (user_id,))
        
        result = cursor.fetchone()
        conn.close()
        
        return result
    
    def get_statistics(self):
        """Получение статистики"""
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()
        
        cursor.execute('SELECT COUNT(*) FROM users')
        total_users = cursor.fetchone()[0]
        
        cursor.execute('SELECT COUNT(*) FROM verifications WHERE status = "pending"')
        pending_verifications = cursor.fetchone()[0]
        
        cursor.execute('SELECT COUNT(*) FROM verifications WHERE status = "approved"')
        approved_verifications = cursor.fetchone()[0]
        
        conn.close()
        
        return {
            'total_users': total_users,
            'pending': pending_verifications,
            'approved': approved_verifications
        }


class AdvancedVerificationBot:
    """Расширенный бот верификации"""
    
    def __init__(self, token, admin_id):
        self.token = token
        self.admin_id = admin_id
        self.app = Application.builder().token(token).build()
        self.db = DatabaseManager()
        
        # Создание папок для сохранения файлов
        os.makedirs('uploads/selfies', exist_ok=True)
        os.makedirs('uploads/passports', exist_ok=True)
        
        self.setup_handlers()
    
    def setup_handlers(self):
        """Настройка обработчиков"""
        
        self.app.add_handler(CommandHandler("start", self.start))
        self.app.add_handler(CommandHandler("stats", self.show_statistics))
        self.app.add_handler(CommandHandler("status", self.check_status))
        
        conv_handler = ConversationHandler(
            entry_points=[CallbackQueryHandler(self.start_verification, pattern="^verify$")],
            states={
                SELFIE: [MessageHandler(filters.PHOTO, self.receive_selfie)],
                PASSPORT: [MessageHandler(filters.PHOTO | filters.Document.PDF, self.receive_passport)]
            },
            fallbacks=[CommandHandler("cancel", self.cancel_verification)]
        )
        
        self.app.add_handler(conv_handler)
    
    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Начало"""
        user = update.effective_user
        
        # Сохраняем пользователя в БД
        self.db.save_user(user.id, user.first_name, user.last_name, user.username)
        
        keyboard = [[InlineKeyboardButton("✅ Начать верификацию", callback_data="verify")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            f"👋 Привет, {user.first_name}!\n\n"
            "Добро пожаловать в систему верификации.\n"
            "Это займет всего 2-3 минуты.",
            reply_markup=reply_markup
        )
    
    async def start_verification(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Начало верификации"""
        query = update.callback_query
        await query.answer()
        
        await query.edit_message_text(
            text="📸 Загрузите фото себя (селфи)\n\n"
                 "• Хорошее освещение\n"
                 "• Четкое лицо\n"
                 "• Никаких фильтров"
        )
        
        return SELFIE
    
    async def receive_selfie(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Получение селфи"""
        user_id = update.effective_user.id
        
        await update.message.chat.send_action(ChatAction.TYPING)
        
        # Скачиваем и сохраняем фото
        photo = update.message.photo[-1]
        file_id = photo.file_id
        
        selfie_path = f'uploads/selfies/{user_id}_{datetime.now().timestamp()}.jpg'
        file = await self.app.bot.get_file(file_id)
        await file.download_to_drive(selfie_path)
        
        # Сохраняем в контексте
        context.user_data['selfie_id'] = file_id
        context.user_data['selfie_path'] = selfie_path
        
        # Прогресс-бар
        progress_msg = await update.message.reply_text(
            "📤 Загрузка...\n▬▬▬▬▬▬▬▬▬▬ 0%"
        )
        
        import asyncio
        for i in range(1, 11):
            await asyncio.sleep(0.15)
            progress = "█" * i + "▬" * (10 - i)
            try:
                await progress_msg.edit_text(
                    f"📤 Загрузка...\n{progress} {i*10}%"
                )
            except:
                pass
        
        await progress_msg.delete()
        
        await update.message.reply_text(
            "✅ Селфи загружено!\n\n"
            "📄 Теперь загрузите паспорт"
        )
        
        return PASSPORT
    
    async def receive_passport(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Получение паспорта"""
        user_id = update.effective_user.id
        
        await update.message.chat.send_action(ChatAction.TYPING)
        
        # Скачиваем паспорт
        if update.message.photo:
            file_id = update.message.photo[-1].file_id
            ext = '.jpg'
        else:
            file_id = update.message.document.file_id
            ext = '.pdf'
        
        passport_path = f'uploads/passports/{user_id}_{datetime.now().timestamp()}{ext}'
        file = await self.app.bot.get_file(file_id)
        await file.download_to_drive(passport_path)
        
        context.user_data['passport_id'] = file_id
        context.user_data['passport_path'] = passport_path
        
        # Прогресс
        progress_msg = await update.message.reply_text(
            "📤 Загрузка паспорта...\n▬▬▬▬▬▬▬▬▬▬ 0%"
        )
        
        import asyncio
        for i in range(1, 11):
            await asyncio.sleep(0.15)
            progress = "█" * i + "▬" * (10 - i)
            try:
                await progress_msg.edit_text(
                    f"📤 Загрузка паспорта...\n{progress} {i*10}%"
                )
            except:
                pass
        
        await progress_msg.delete()
        
        # Сохраняем в БД
        self.db.save_verification(
            user_id,
            context.user_data['selfie_id'],
            file_id,
            context.user_data['selfie_path'],
            passport_path
        )
        
        # Статус сообщение
        await update.message.reply_photo(
            photo="https://via.placeholder.com/400x200/FFA500/FFFFFF?text=%F0%9F%94%84+%D0%9D%D0%90+%D0%9F%D0%A0%D0%9E%D0%92%D0%95%D0%A0%D0%9A%D0%95",
            caption="⏳ На проверке\n\nВы получите уведомление за 24 часа"
        )
        
        # Уведомляем админа
        await self.notify_admin(update.effective_user, user_id)
        
        return ConversationHandler.END
    
    async def cancel_verification(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Отмена"""
        await update.message.reply_text("❌ Отменено. Напишите /start чтобы начать заново")
        return ConversationHandler.END
    
    async def notify_admin(self, user, user_id):
        """Уведомление админу"""
        try:
            stats = self.db.get_statistics()
            
            message = (
                f"📋 Новая верификация\n\n"
                f"👤 {user.first_name} {user.last_name or ''}\n"
                f"🆔 {user_id}\n"
                f"⏰ {datetime.now().strftime('%d.%m.%Y %H:%M')}\n\n"
                f"📊 Всего:\n"
                f"• Пользователей: {stats['total_users']}\n"
                f"• На проверке: {stats['pending']}\n"
                f"• Одобренных: {stats['approved']}"
            )
            
            await self.app.bot.send_message(self.admin_id, message)
        except Exception as e:
            logger.error(f"Ошибка уведомления админа: {e}")
    
    async def show_statistics(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Показать статистику"""
        if update.effective_user.id != self.admin_id:
            await update.message.reply_text("❌ Недостаточно прав")
            return
        
        stats = self.db.get_statistics()
        
        message = (
            f"📊 Статистика верификации\n\n"
            f"👥 Всего пользователей: {stats['total_users']}\n"
            f"⏳ На проверке: {stats['pending']}\n"
            f"✅ Одобренных: {stats['approved']}"
        )
        
        await update.message.reply_text(message)
    
    async def check_status(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Проверить статус верификации"""
        user_id = update.effective_user.id
        result = self.db.get_verification_status(user_id)
        
        if result:
            status, created_at = result
            status_emoji = "⏳" if status == "pending" else "✅"
            status_text = "На проверке" if status == "pending" else "Одобрено"
            
            await update.message.reply_text(
                f"{status_emoji} Статус: {status_text}\n"
                f"⏰ Дата: {created_at}"
            )
        else:
            await update.message.reply_text(
                "❌ Вы еще не проходили верификацию.\n"
                "Напишите /start чтобы начать"
            )
    
    def run(self):
        """Запуск"""
        logger.info("🤖 Расширенный бот запущен...")
        self.app.run_polling()


if __name__ == "__main__":
    BOT_TOKEN = "YOUR_BOT_TOKEN_HERE"
    ADMIN_ID = 123456789  # Замените на свой ID
    
    if BOT_TOKEN == "YOUR_BOT_TOKEN_HERE":
        print("❌ Установите BOT_TOKEN!")
        exit(1)
    
    bot = AdvancedVerificationBot(BOT_TOKEN, ADMIN_ID)
    bot.run()
