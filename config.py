import os
from dotenv import load_dotenv

# Загружаем переменные окружения
load_dotenv()

# Токен бота (приоритет переменной окружения, затем значение по умолчанию)
BOT_TOKEN = os.getenv('BOT_TOKEN', '8683124553:AAFcq_VmrQCPqLxMsDLgCkmnbdM7a22LBMo')

# Проверка наличия токена
if not BOT_TOKEN or BOT_TOKEN == 'your_bot_token_here':
    raise ValueError("Пожалуйста, настройте BOT_TOKEN в переменных окружения или в config.py")

# Список системных сообщений для удаления
SYSTEM_MESSAGE_TYPES = [
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
