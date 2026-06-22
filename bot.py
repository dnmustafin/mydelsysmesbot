import logging
import requests  # для работы с API намаза
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
        self.application.add_handler(CommandHandler("status", self.status_command))
        
        # Команды для намаза (без ввода города)
        self.application.add_handler(CommandHandler("prayer_mecca", self.prayer_mecca_command))
        self.application.add_handler(CommandHandler("prayer_medina", self.prayer_medina_command))
        
        # Команда /prayer с кнопками
        self.application.add_handler(CommandHandler("prayer", self.prayer_command))
        
        # Обработчик нажатий на кнопки
        self.application.add_handler(CallbackQueryHandler(self.button_callback))
        
        self.application.add_handler(MessageHandler(filters.ALL, self.handle_message))
    
    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик команды /start"""
        welcome_text = """
🤖 **Бот для очистки системных сообщений + время намаза**

Привет! Я умею две вещи:

**1. 🧹 Очистка чата от системных сообщений:**
• Сообщения о входе/выходе участников
• Изменения названия и фото чата
• Закрепленные сообщения
• И другие системные уведомления

**2. 🕌 Время намаза:**
• `/prayer_mecca` - время намаза в Мекке
• `/prayer_medina` - время намаза в Медине
• `/prayer` - выбрать город из кнопок

**Команды:**
/start - показать это сообщение
/help - подробная справка
/status - статус бота в чате
/prayer_mecca - время намаза в Мекке
/prayer_medina - время намаза в Медине
/prayer - выбрать город из кнопок

Для работы очистки добавьте меня в чат и дайте права администратора на удаление сообщений.
        """
        await update.message.reply_text(welcome_text, parse_mode='Markdown')
    
    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик команды /help"""
        help_text = """
📖 **Справка по использованию бота**

**🧹 Очистка системных сообщений:**
1. Добавьте бота в чат
2. Сделайте бота администратором с правом удаления сообщений
3. Бот автоматически начнет удалять системные сообщения

**🕌 Время намаза:**
• `/prayer_mecca` - время намаза в Мекке
• `/prayer_medina` - время намаза в Медине
• `/prayer` - выбрать город из кнопок

**📋 Команды:**
/start - главное меню
/help - эта справка
/status - статус работы
/prayer_mecca - время намаза в Мекке
/prayer_medina - время намаза в Медине
/prayer - выбрать город из кнопок

**Требования:**
• Бот должен быть администратором чата
• Права на удаление и просмотр сообщений
        """
        await update.message.reply_text(help_text, parse_mode='Markdown')
    
    async def status_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик команды /status"""
        chat = update.effective_chat
        
        try:
            bot_member = await chat.get_member(context.bot.id)
            
            status_text = f"""
📊 **Статус бота в чате**

**Чат:** {chat.title or chat.first_name}
**Тип чата:** {chat.type}
**ID чата:** {chat.id}

**Права бота:**
• Администратор: {'✅' if bot_member.status in ['administrator', 'creator'] else '❌'}
• Может удалять сообщения: {'✅' if bot_member.can_delete_messages else '❌'}
• Может просматривать сообщения: {'✅' if bot_member.can_read_messages else '❌'}

**Статус:** {'🟢 Активен' if bot_member.status in ['administrator', 'creator'] else '🔴 Неактивен'}
            """
        except Exception as e:
            status_text = f"❌ Ошибка при получении статуса: {e}"
        
        await update.message.reply_text(status_text, parse_mode='Markdown')
    
    async def prayer_mecca_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обрабатывает команду /prayer_mecca"""
        await self.send_prayer_times(update.message, "Mecca", "Мекке")
    
    async def prayer_medina_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обрабатывает команду /prayer_medina"""
        await self.send_prayer_times(update.message, "Medina", "Медине")
    
    async def prayer_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обрабатывает команду /prayer и показывает кнопки для выбора города"""
        keyboard = [
            [
                InlineKeyboardButton("🕋 Мекка", callback_data="prayer_mecca"),
                InlineKeyboardButton("🕌 Медина", callback_data="prayer_medina"),
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            "🕌 Выберите город для получения времени намаза:\n\n"
            "Или используйте команды:\n"
            "/prayer_mecca - для Мекки\n"
            "/prayer_medina - для Медины",
            reply_markup=reply_markup
        )
    
    async def button_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обрабатывает нажатие на кнопки"""
        query = update.callback_query
        await query.answer()
        
        if query.data == "prayer_mecca":
            await self.send_prayer_times(query.message, "Mecca", "Мекке")
        elif query.data == "prayer_medina":
            await self.send_prayer_times(query.message, "Medina", "Медине")
        else:
            await query.edit_message_text("❌ Неизвестный город.")
    
    async def send_prayer_times(self, message, city, city_display=None):
        """Отправляет время намаза для указанного города"""
        if city_display is None:
            city_display = city
        
        # Показываем, что бот думает (если это не кнопка)
        if hasattr(message, 'edit_text'):
            await message.edit_text(f"🔄 Загружаю время намаза для {city_display}...")
        else:
            await message.reply_text(f"🔄 Загружаю время намаза для {city_display}...")
        
        try:
            response = requests.get(
                f"http://api.aladhan.com/v1/timingsByCity",
                params={
                    "city": city,
                    "country": "Saudi Arabia",
                    "method": 2
                },
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
                
                # Если это сообщение от кнопки — редактируем, иначе отправляем новое
                if hasattr(message, 'edit_text'):
                    await message.edit_text(prayer_times, parse_mode='Markdown')
                else:
                    await message.reply_text(prayer_times, parse_mode='Markdown')
            else:
                error_text = f"❌ Не удалось найти время намаза для {city_display}."
                if hasattr(message, 'edit_text'):
                    await message.edit_text(error_text)
                else:
                    await message.reply_text(error_text)
                
        except requests.exceptions.Timeout:
            error_text = "⏰ Сервер времени намаза не отвечает. Попробуйте позже."
            if hasattr(message, 'edit_text'):
                await message.edit_text(error_text)
            else:
                await message.reply_text(error_text)
        except requests.exceptions.RequestException as e:
            error_text = "🌐 Ошибка соединения с сервером времени намаза."
            if hasattr(message, 'edit_text'):
                await message.edit_text(error_text)
            else:
                await message.reply_text(error_text)
            logger.error(f"Ошибка запроса к API намаза: {e}")
        except Exception as e:
            error_text = "❌ Произошла ошибка при получении времени намаза."
            if hasattr(message, 'edit_text'):
                await message.edit_text(error_text)
            else:
                await message.reply_text(error_text)
            logger.error(f"Ошибка в send_prayer_times: {e}")
    
    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик всех сообщений для удаления системных"""
        message = update.message
        
        if self.is_system_message(message):
            try:
                await message.delete()
                logger.info(f"Удалено системное сообщение в чате {message.chat.id}")
                await self.notify_admins_privately(message, context)
                    
            except Exception as e:
                logger.error(f"Ошибка при удалении сообщения: {e}")
                try:
                    await self.notify_admins_privately(message, context, error=True)
                except:
                    pass
    
    async def notify_admins_privately(self, message, context, error=False):
        """Уведомляет администраторов в личные сообщения"""
        try:
            admins = await message.chat.get_administrators()
            for admin in admins:
                if admin.user.id != context.bot.id:
                    try:
                        if error:
                            notification_text = f"⚠️ Не удалось удалить системное сообщение в чате {message.chat.title}. Проверьте права бота."
                        else:
                            notification_text = f"🗑️ В чате {message.chat.title} удалено системное сообщение"
                        
                        await context.bot.send_message(
                            chat_id=admin.user.id,
                            text=notification_text
                        )
                    except:
                        pass
        except Exception as e:
            logger.error(f"Ошибка при уведомлении администраторов: {e}")
    
    def is_system_message(self, message) -> bool:
        """
        Проверяет, является ли сообщение системным.
        Удаляет ТОЛЬКО официальные системные поля Telegram.
        НЕ удаляет обычные сообщения НИ ПРИ КАКИХ условиях.
        """
        # Если у сообщения есть текст - это НЕ системное сообщение
        if message.text and len(message.text.strip()) > 0:
            return False
        
        # Если есть медиа — НЕ удаляем
        if any([
            message.photo, message.video, message.audio, message.document,
            message.voice, message.video_note, message.sticker, message.animation,
            message.contact, message.location, message.venue, message.poll
        ]):
            return False
        
        # Проверяем ТОЛЬКО официальные системные поля
        if hasattr(message, 'new_chat_members') and message.new_chat_members:
            return True
        
        if hasattr(message, 'left_chat_member') and message.left_chat_member is not None:
            return True
        
        system_fields = [
            'new_chat_title',
            'new_chat_photo',
            'delete_chat_photo',
            'group_chat_created',
            'supergroup_chat_created',
            'channel_chat_created',
            'message_auto_delete_timer_changed',
            'migrate_to_chat_id',
            'migrate_from_chat_id',
            'pinned_message',
            'invoice',
            'successful_payment',
            'connected_website',
            'write_access_allowed',
            'passport_data',
            'proximity_alert_triggered',
            'forum_topic_created',
            'forum_topic_edited',
            'forum_topic_closed',
            'forum_topic_reopened',
            'general_forum_topic_hidden',
            'general_forum_topic_unhidden',
            'video_chat_scheduled',
            'video_chat_started',
            'video_chat_ended',
            'video_chat_participants_invited',
            'web_app_data'
        ]
        
        for field in system_fields:
            if hasattr(message, field) and getattr(message, field) is not None:
                return True
        
        return False
    
    def run(self):
        """Запуск бота"""
        logger.info("Запуск бота для очистки системных сообщений...")
        self.application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    bot = SystemMessageCleanerBot()
    bot.run()
