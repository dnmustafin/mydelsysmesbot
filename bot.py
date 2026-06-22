import logging
import requests  # для работы с API намаза
from telegram import Update
from telegram.ext import Application, MessageHandler, CommandHandler, filters, ContextTypes
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
        # Обработчик команды /start
        self.application.add_handler(CommandHandler("start", self.start_command))
        
        # Обработчик команды /help
        self.application.add_handler(CommandHandler("help", self.help_command))
        
        # Обработчик команды /status
        self.application.add_handler(CommandHandler("status", self.status_command))
        
        # Обработчик команды /prayer (время намаза)
        self.application.add_handler(CommandHandler("prayer", self.prayer_command))
        
        # Обработчик всех сообщений для проверки системных сообщений
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
• `/prayer Mecca` - время намаза в Мекке
• `/prayer Medina` - время намаза в Медине

**Команды:**
/start - показать это сообщение
/help - подробная справка
/status - статус бота в чате
/prayer [город] - время намаза

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
• `/prayer Mecca` - время намаза в Мекке
• `/prayer Medina` - время намаза в Медине

**📋 Команды:**
/start - главное меню
/help - эта справка
/status - статус работы
/prayer [город] - время намаза

**Требования:**
• Бот должен быть администратором чата
• Права на удаление и просмотр сообщений
        """
        await update.message.reply_text(help_text, parse_mode='Markdown')
    
    async def status_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик команды /status"""
        chat = update.effective_chat
        
        try:
            # Проверяем права бота
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
    
    async def prayer_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обрабатывает команду /prayer и показывает время намаза для указанного города."""
        try:
            # Получаем город из сообщения пользователя
            city = context.args[0] if context.args else None
            
            if city is None:
                await update.message.reply_text(
                    "🕌 Пожалуйста, укажите город.\n"
                    "Например: `/prayer Mecca` или `/prayer Medina`",
                    parse_mode='Markdown'
                )
                return
            
            # Запрос к AlAdhan API
            response = requests.get(
                f"http://api.aladhan.com/v1/timingsByCity",
                params={
                    "city": city,
                    "country": "Saudi Arabia",
                    "method": 2  # Метод ISNA (Исламское общество Северной Америки)
                },
                timeout=10
            )
            data = response.json()
            
            if data.get('code') == 200:
                timings = data['data']['timings']
                date_info = data['data']['date']['readable']
                
                prayer_times = (
                    f"🕌 **Время намаза для {city}**\n"
                    f"📅 {date_info}\n\n"
                    f"🌅 **Фаджр:** {timings['Fajr']}\n"
                    f"☀️ **Восход:** {timings['Sunrise']}\n"
                    f"🏙️ **Зухр:** {timings['Dhuhr']}\n"
                    f"🌇 **Аср:** {timings['Asr']}\n"
                    f"🌆 **Магриб:** {timings['Maghrib']}\n"
                    f"🌃 **Иша:** {timings['Isha']}"
                )
                await update.message.reply_text(prayer_times, parse_mode='Markdown')
            else:
                await update.message.reply_text(
                    f"❌ Не удалось найти время намаза для города '{city}'.\n"
                    "Проверьте написание (Mecca или Medina)."
                )
                
        except requests.exceptions.Timeout:
            await update.message.reply_text("⏰ Сервер времени намаза не отвечает. Попробуйте позже.")
        except requests.exceptions.RequestException as e:
            await update.message.reply_text("🌐 Ошибка соединения с сервером времени намаза.")
            logger.error(f"Ошибка запроса к API намаза: {e}")
        except Exception as e:
            await update.message.reply_text("❌ Произошла ошибка при получении времени намаза.")
            logger.error(f"Ошибка в prayer_command: {e}")
    
    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик всех сообщений для удаления системных"""
        message = update.message
        
        # Проверяем, является ли сообщение системным
        if self.is_system_message(message):
            try:
                # Удаляем системное сообщение
                await message.delete()
                logger.info(f"Удалено системное сообщение в чате {message.chat.id}")
                
                # Уведомляем только администраторов в личные сообщения
                await self.notify_admins_privately(message, context)
                    
            except Exception as e:
                logger.error(f"Ошибка при удалении сообщения: {e}")
                # Если не удалось удалить, отправляем уведомление только администраторам
                try:
                    await self.notify_admins_privately(message, context, error=True)
                except:
                    pass
    
    async def notify_admins_privately(self, message, context, error=False):
        """Уведомляет администраторов в личные сообщения"""
        try:
            admins = await message.chat.get_administrators()
            for admin in admins:
                if admin.user.id != context.bot.id:  # Не уведомляем самого бота
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
                        pass  # Игнорируем ошибки отправки в личные сообщения
        except Exception as e:
            logger.error(f"Ошибка при уведомлении администраторов: {e}")
    
    def is_system_message(self, message) -> bool:
        """
        Проверяет, является ли сообщение системным (служебным).
        Использует ТОЛЬКО официальные поля Telegram, без опасных эвристик.
        """
        # 1. Проверяем официальные системные поля (это безопасно!)
        system_fields = [
            'new_chat_members',
            'left_chat_member',
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
        
        # 2. Проверяем специальный тип: служебные сообщения о выходе участника
        if hasattr(message, 'left_chat_member') and message.left_chat_member is not None:
            return True
        
        # 3. Проверяем сообщения о присоединении
        if hasattr(message, 'new_chat_members') and message.new_chat_members:
            return True
        
        # 4. БЕЗОПАСНАЯ проверка текста: только если текст совпадает с шаблоном ТОЧНО
        if message.text:
            # Удаляем только если сообщение состоит ТОЛЬКО из служебной фразы
            system_phrases = [
                "присоединился к группе",
                "присоединилась к группе",
                "покинул группу",
                "покинула группу",
                "ушел из группы",
                "ушла из группы",
                "joined the group",
                "left the group"
            ]
            text_clean = message.text.strip().lower()
            for phrase in system_phrases:
                if text_clean == phrase.lower():
                    return True
        
        # 5. НЕ удаляем сообщения, если есть текст (даже если он короткий)
        if message.text and len(message.text.strip()) > 0:
            return False
        
        # 6. Если есть медиа (фото, видео, документ и т.д.) — НЕ удаляем
        if any([
            message.photo, message.video, message.audio, message.document,
            message.voice, message.video_note, message.sticker, message.animation,
            message.contact, message.location, message.venue, message.poll
        ]):
            return False
        
        # 7. ВСЕ остальные сообщения считаем НЕ системными
        return False
    
    def run(self):
        """Запуск бота"""
        logger.info("Запуск бота для очистки системных сообщений...")
        self.application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    bot = SystemMessageCleanerBot()
    bot.run()
