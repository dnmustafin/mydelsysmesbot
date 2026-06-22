import logging
import requests
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, MessageHandler, CommandHandler, CallbackQueryHandler, filters, ContextTypes
from config import BOT_TOKEN, SYSTEM_MESSAGE_TYPES

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

class SystemMessageCleanerBot:
    def __init__(self):
        self.application = Application.builder().token(BOT_TOKEN).build()
        self.setup_handlers()
    
    def setup_handlers(self):
        """Настройка обработчиков команд и сообщений"""
        self.application.add_handler(CommandHandler("start", self.start_command))
        self.application.add_handler(CommandHandler("help", self.help_command))
        self.application.add_handler(CommandHandler("prayer", self.prayer_command))
        self.application.add_handler(CallbackQueryHandler(self.button_callback))
        self.application.add_handler(MessageHandler(filters.ALL, self.handle_message))
    
    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        welcome_text = """
🤖 **Бот для очистки системных сообщений + время намаза**

Привет! Я умею две вещи:

**1. 🧹 Очистка чата от системных сообщений:**
• Сообщения о входе/выходе участников
• Изменения названия и фото чата
• Закрепленные сообщения
• И другие системные уведомления

**2. 🕌 Время намаза:**
• Напиши `/prayer` и выбери город из кнопок

**Команды:**
/start - показать это сообщение
/help - подробная справка
/prayer - время намаза (выбор города из кнопок)

Для работы очистки добавьте меня в чат и дайте права администратора на удаление сообщений.
        """
        await update.message.reply_text(welcome_text, parse_mode='Markdown')
    
    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        help_text = """
📖 **Справка по использованию бота**

**🧹 Очистка системных сообщений:**
1. Добавьте бота в чат
2. Сделайте бота администратором с правом удаления сообщений
3. Бот автоматически начнет удалять системные сообщения

**🕌 Время намаза:**
• Напиши `/prayer` и выбери город из кнопок

**📋 Команды:**
/start - главное меню
/help - эта справка
/prayer - время намаза (выбор города из кнопок)

**Требования:**
• Бот должен быть администратором чата
• Права на удаление и просмотр сообщений
        """
        await update.message.reply_text(help_text, parse_mode='Markdown')
    
    async def prayer_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Показывает кнопки для выбора города"""
        keyboard = [
            [
                InlineKeyboardButton("🕋 Мекка", callback_data="prayer_mecca"),
                InlineKeyboardButton("🕌 Медина", callback_data="prayer_medina"),
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(
            "🕌 Выберите город для получения времени намаза:",
            reply_markup=reply_markup
        )
    
    async def button_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обрабатывает нажатие на кнопки"""
        query = update.callback_query
        await query.answer()
        
        if query.data == "prayer_mecca":
            city = "Mecca"
            city_display = "Мекке"
        elif query.data == "prayer_medina":
            city = "Medina"
            city_display = "Медине"
        else:
            await query.edit_message_text("❌ Неизвестный город.")
            return
        
        await query.edit_message_text(f"🔄 Загружаю время намаза для {city_display}...")
        
        try:
            response = requests.get(
                "http://api.aladhan.com/v1/timingsByCity",
                params={"city": city, "country": "Saudi Arabia", "method": 2},
                timeout=10
            )
            data = response.json()
            
            if data.get('code') == 200:
                timings = data['data']['timings']
                date_info = data['data']['date']['readable']
                prayer_times = (
                    f"🕌 **Время намаза для {city_display}**\n"
                    f"📅 {date_info}\n\n"
                    f"🌅 **Фаджр:** {timings['Fajr']}\n"
                    f"☀️ **Восход:** {timings['Sunrise']}\n"
                    f"🏙️ **Зухр:** {timings['Dhuhr']}\n"
                    f"🌇 **Аср:** {timings['Asr']}\n"
                    f"🌆 **Магриб:** {timings['Maghrib']}\n"
                    f"🌃 **Иша:** {timings['Isha']}"
                )
                await query.edit_message_text(prayer_times, parse_mode='Markdown')
            else:
                await query.edit_message_text(f"❌ Не удалось найти время намаза для {city_display}.")
        except Exception as e:
            await query.edit_message_text("❌ Ошибка при получении времени намаза.")
            logger.error(f"Ошибка в button_callback: {e}")
    
    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик всех сообщений для удаления системных"""
        message = update.message
        
        if self.is_system_message(message):
            try:
                await message.delete()
                # Лог в терминал с типом
                message_type = self.get_message_type(message)
                logger.info(f"🗑️ Удалено системное сообщение типа: {message_type} в чате {message.chat.id}")
                
                # Уведомляем администраторов с типом
                await self.notify_admins_privately(message, context)
            except Exception as e:
                logger.error(f"❌ Ошибка при удалении: {e}")
                try:
                    await self.notify_admins_privately(message, context, error=True)
                except:
                    pass
    
    async def notify_admins_privately(self, message, context, error=False):
        """Уведомляет администраторов в личные сообщения с указанием типа"""
        try:
            admins = await message.chat.get_administrators()
            # Определяем тип сообщения
            message_type = self.get_message_type(message)
            
            for admin in admins:
                if admin.user.id != context.bot.id:
                    try:
                        if error:
                            notification_text = f"⚠️ Не удалось удалить системное сообщение в чате {message.chat.title}. Проверьте права бота."
                        else:
                            notification_text = f"🗑️ В чате {message.chat.title} удалено системное сообщение типа: {message_type}"
                        
                        await context.bot.send_message(
                            chat_id=admin.user.id,
                            text=notification_text
                        )
                        logger.info(f"📨 Уведомление отправлено администратору {admin.user.id}")
                    except Exception as e:
                        logger.error(f"❌ Не удалось отправить уведомление администратору {admin.user.id}: {e}")
        except Exception as e:
            logger.error(f"❌ Ошибка при получении списка администраторов: {e}")
    
    def is_system_message(self, message) -> bool:
        """Проверяет, является ли сообщение системным"""
        if message.text and len(message.text.strip()) > 0:
            return False
        
        if any([
            message.photo, message.video, message.audio, message.document,
            message.voice, message.video_note, message.sticker, message.animation,
            message.contact, message.location, message.venue, message.poll
        ]):
            return False
        
        if hasattr(message, 'new_chat_members') and message.new_chat_members:
            return True
        if hasattr(message, 'left_chat_member') and message.left_chat_member is not None:
            return True
        
        system_fields = [
            'new_chat_title', 'new_chat_photo', 'delete_chat_photo',
            'group_chat_created', 'supergroup_chat_created', 'channel_chat_created',
            'message_auto_delete_timer_changed', 'migrate_to_chat_id', 'migrate_from_chat_id',
            'pinned_message', 'invoice', 'successful_payment', 'connected_website',
            'write_access_allowed', 'passport_data', 'proximity_alert_triggered',
            'forum_topic_created', 'forum_topic_edited', 'forum_topic_closed',
            'forum_topic_reopened', 'general_forum_topic_hidden', 'general_forum_topic_unhidden',
            'video_chat_scheduled', 'video_chat_started', 'video_chat_ended',
            'video_chat_participants_invited', 'web_app_data'
        ]
        
        for field in system_fields:
            if hasattr(message, field) and getattr(message, field) is not None:
                return True
        return False
    
    def get_message_type(self, message) -> str:
        """Определяет тип системного сообщения"""
        if hasattr(message, 'new_chat_members') and message.new_chat_members:
            return 'new_chat_members (новые участники)'
        if hasattr(message, 'left_chat_member') and message.left_chat_member is not None:
            return 'left_chat_member (выход участника)'
        
        system_fields = {
            'new_chat_title': 'изменение названия чата',
            'new_chat_photo': 'изменение фото чата',
            'delete_chat_photo': 'удаление фото чата',
            'group_chat_created': 'создание группы',
            'supergroup_chat_created': 'создание супергруппы',
            'channel_chat_created': 'создание канала',
            'message_auto_delete_timer_changed': 'изменение таймера автоудаления',
            'migrate_to_chat_id': 'миграция чата',
            'migrate_from_chat_id': 'миграция чата',
            'pinned_message': 'закрепленное сообщение',
            'invoice': 'инвойс',
            'successful_payment': 'успешная оплата',
            'connected_website': 'подключенный сайт',
            'write_access_allowed': 'разрешение на запись',
            'passport_data': 'данные паспорта',
            'proximity_alert_triggered': 'сигнал приближения',
            'forum_topic_created': 'создание темы форума',
            'forum_topic_edited': 'изменение темы форума',
            'forum_topic_closed': 'закрытие темы форума',
            'forum_topic_reopened': 'открытие темы форума',
            'general_forum_topic_hidden': 'скрытие общей темы форума',
            'general_forum_topic_unhidden': 'показ общей темы форума',
            'video_chat_scheduled': 'запланированный видеозвонок',
            'video_chat_started': 'начало видеозвонка',
            'video_chat_ended': 'конец видеозвонка',
            'video_chat_participants_invited': 'приглашение в видеозвонок',
            'web_app_data': 'данные веб-приложения'
        }
        
        for field, description in system_fields.items():
            if hasattr(message, field) and getattr(message, field) is not None:
                return f"{field} ({description})"
        
        return "unknown (неизвестный тип)"
    
    def run(self):
        logger.info("🚀 Бот запущен и готов к работе!")
        self.application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    bot = SystemMessageCleanerBot()
    bot.run()
