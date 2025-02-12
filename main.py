import telebot
import os
import time
import schedule
import threading
import re
import logging
from functools import wraps
from dotenv import load_dotenv

from notifications.jobs import (
    job_notify_tommorow,
    job_bells_tommorow
)
from logics.body import (
    start_bot,
    help,
    back_request,
    teacher_request,
    pairs_request,
    bells_request,
    information_request,
    buildings_request,
    cab_request,
    notifications_request,
    active_group_request
)
from logics.supps_handlers import(
    select_teacher,
    answer,
)

load_dotenv("/app/.env")

token = os.getenv('bot_token')
bot = telebot.TeleBot(token)

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')

'''
main_bot
'''
def log_request(func):
    @wraps(func)
    def wrapper(message, *args, **kwargs):
        start_time = time.time()  # Начало отсчёта времени

        # Проверяем, является ли сообщение обычным или callback-запросом
        if isinstance(message, telebot.types.Message):
            user_action = message.text  # Действие пользователя (текст сообщения)
        elif isinstance(message, telebot.types.CallbackQuery):
            user_action = message.data  # Действие пользователя (данные callback-кнопки)

        # Вызов оригинальной функции
        response = func(message, *args, **kwargs)

        # Время, прошедшее с момента получения сообщения
        elapsed_time = time.time() - start_time
        user_name = message.from_user.full_name
        user_id = message.from_user.id

        # Логирование запроса
        logging.info(f"Запрос от {user_name} (ID: {user_id}) | Действие: '{user_action}' | Время на обработку: {elapsed_time:.2f} секунд")
        
        return response
    return wrapper


@bot.message_handler(commands=['start'])
@log_request
def start_handle(message):
    start_bot(bot,message)

@bot.message_handler(commands=['help'])
@log_request
def help_handle(message):
    help(bot,message)

@bot.message_handler(func=lambda message: True)
@log_request
def handle_message(message):

    chat_id = message.chat.id
    
    if message.text == "Назад":
        back_request(bot,chat_id)
    
#Преподаватель
    elif re.match(r'Преподаватель', message.text, re.IGNORECASE):
        teacher_request(bot,message,chat_id)

#Пары   
    elif re.match(r'пары', message.text, re.IGNORECASE):
        pairs_request(bot,message,chat_id)
       
#Кабинет
    elif re.match(r'кабинет', message.text, re.IGNORECASE):
       cab_request(bot,message,chat_id)

#Звонки
    
    elif re.match(r'^\s*звонки\s*', message.text, re.IGNORECASE):
       bells_request(bot,message,chat_id)

#Уведомления 
# Переключение уведомлений на основе текста кнопки

    elif re.match(r'Уведомления', message.text, re.IGNORECASE):
        notifications_request(bot,message,chat_id)
    
    #Информация
    elif message.text == "Информация":
        information_request(bot,chat_id)

    elif message.text == "Корпуса":
        buildings_request(bot,chat_id)
    
    #Активная группа + handler

    elif message.text == "Активная группа":
        active_group_request(bot, message, chat_id)

# Обработка одинаковых преподавателей
@bot.callback_query_handler(func=lambda call: call.data.startswith("select_teacher:"))
def handle_select_teacher(call):
    select_teacher(bot,call)

# Обработка ввода группы
@bot.callback_query_handler(func=lambda call: True)
@log_request
def handle_answer(call):
    answer(bot,call)

# Задачи уведомлений
def run_scheduler():
    schedule.every(30).minutes.do(job_notify_tommorow,bot)
    schedule.every(30).minutes.do(job_bells_tommorow,bot)
    while True:
        schedule.run_pending()
        time.sleep(1)

if __name__ == "__main__":
    # Запуск планировщика в отдельном потоке
    scheduler_thread = threading.Thread(target=run_scheduler, daemon=True)
    scheduler_thread.start()            

# Запуск бота
bot.polling(none_stop=True)