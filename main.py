import telebot
import os
import datetime
import time
import schedule
import threading
import re
import logging
from functools import wraps
from dotenv import load_dotenv
from methods.messages import start_message, help_message, buildings
from methods.db import add_chat, set_group, set_notifications, get_active_group, get_notifications_status
from methods.pairs import get_groups, get_teachers, get_shedule, get_shed_by_teacher, get_bells, get_shed_by_cab
from notifications.db_matcher import check_changes, bells_changes
from notifications.get_schedule import get_chat_notify_by_group, get_chat_notify, get_change
from telebot import types
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from fuzzywuzzy import fuzz
from fuzzywuzzy import process

load_dotenv("/app/.env")

token = os.getenv('bot_token')
bot = telebot.TeleBot(token)

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')

# Функция для создания основного меню с обновленной кнопкой уведомлений
def get_main_menu(notifications_status):

    main_menu = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)

    btn_active = types.KeyboardButton('Активная группа')
    btn_notifications = types.KeyboardButton('Уведомления включены' if notifications_status else 'Уведомления выключены')
    btn_bells = types.KeyboardButton('Звонки')
    btn_pairs = types.KeyboardButton('Пары')
    btn_info = types.KeyboardButton('Информация')

    main_menu.add(btn_active, btn_info)
    main_menu.add(btn_notifications)
    main_menu.add(btn_bells, btn_pairs)
    return main_menu

# Кнопка назад
back_button = types.ReplyKeyboardMarkup(resize_keyboard=True)
btn_back = types.KeyboardButton('Назад')
back_button.add(btn_back)

# Кнопки пары
markup_pairs = types.ReplyKeyboardMarkup(resize_keyboard=True)
btn_today = types.KeyboardButton('Пары на сегодня')
btn_tommorow = types.KeyboardButton('Пары на завтра')
markup_pairs.add(btn_today,btn_tommorow)
markup_pairs.add(btn_back)

# Кнопки звонков
markup_bells = types.ReplyKeyboardMarkup(resize_keyboard=True)
btn_today_bells = types.KeyboardButton('Звонки на сегодня')
btn_tommorow_bells = types.KeyboardButton('Звонки на завтра')
markup_bells.add(btn_today_bells,btn_tommorow_bells)
markup_bells.add(btn_back)

# Кнопки информация
markup_info = types.ReplyKeyboardMarkup(resize_keyboard=True)
btn_buildings = types.KeyboardButton('Корпуса')
btn_certs = types.KeyboardButton('Справки')
markup_info.add(btn_certs,btn_buildings)
markup_info.add(btn_back)

# Inline-клавиатура для смены группы
markup_change_group = types.InlineKeyboardMarkup()
btn_change_group = types.InlineKeyboardButton(text='Сменить', callback_data="change_group")
inline_back = types.InlineKeyboardButton('Назад', callback_data="back_group")
markup_change_group.add(btn_change_group)
markup_change_group.add(inline_back)

# Inline-клавиатура для установки группы
markup_set_group = types.InlineKeyboardMarkup()
btn_set_group = types.InlineKeyboardButton(text='Установить', callback_data="change_group")
markup_set_group.add(btn_set_group)
markup_set_group.add(inline_back)

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
def start(message):

    chat_id = message.chat.id
    notifications_status = get_notifications_status(chat_id)
    if notifications_status is None:
        notifications_status= False
    bot.send_message(chat_id, start_message(), reply_markup=get_main_menu(notifications_status))

    add_chat(chat_id)

@bot.message_handler(commands=['help'])
@log_request
def help(message):

    chat_id = message.chat.id
    notifications_status = get_notifications_status(chat_id)

    if notifications_status is None:
        notifications_status= False

    bot.send_message(chat_id, help_message(), reply_markup=get_main_menu(notifications_status), parse_mode="HTML")

@bot.message_handler(func=lambda message: True)
@log_request
def handle_message(message):

    chat_id = message.chat.id
    chat_group = get_active_group(chat_id)
    
    teacher = None
    target_date = None
    
    notifications_status = get_notifications_status(chat_id)

    group_list = []
    get_groups(group_list)

    teachers_list = []
    get_teachers(teachers_list)
    
    if message.text == "Назад":
        bot.send_message(chat_id, "Вы вернулись в главное меню.", reply_markup=get_main_menu(notifications_status))
  
#Преподаватель
    elif re.match(r'Преподаватель', message.text, re.IGNORECASE):
        
        date_now = datetime.datetime.now()
        current_date = date_now.strftime('%d.%m.%Y')
        tommorow = (date_now + datetime.timedelta(days=1)).strftime('%d.%m.%Y')
        
        teacher = None
        target_date = None 
        message_date = None

        teacher_match = re.search(r'Преподаватель\s+([а-яё]+)', message.text, re.IGNORECASE)
        message_date = re.search(r'(\d{2}\.\d{2})(?:\.(\d{4}))?', message.text, re.IGNORECASE)

        if teacher_match:
            teacher = teacher_match.group(1).strip()
        else:
            bot.send_message(chat_id, "Не удалось найти имя преподавателя в запросе.", reply_markup=back_button)
            return
    
        if re.search(r'сегодня', message.text, re.IGNORECASE):
            target_date = current_date
        elif re.search(r'завтра', message.text, re.IGNORECASE):
            target_date = tommorow
        elif message_date:
            target_date = message_date.group(1)
            if not message_date.group(2):
                year = datetime.datetime.now().year
                target_date = f"{target_date}.{year}"
            else:
                target_date = f"{target_date}.{message_date.group(2)}"

            try:
                datetime.datetime.strptime(target_date, '%d.%m.%Y')
            except ValueError:
                bot.send_message(chat_id, f"Ошибка: Некорректная дата {target_date}.", reply_markup=back_button)
                return

        # Если дата или преподаватель не указаны, выводим соответствующее сообщение
        if not teacher:
            bot.send_message(chat_id, "Пожалуйста, укажите фамилию преподавателя.")
            return

        if not target_date:
            bot.send_message(chat_id, "Пожалуйста, укажите дату (сегодня, завтра или конкретную).")
            return
        
        # Находим наиболее подходящую фамилию преподавателя
        all_matches = process.extract(teacher, teachers_list, scorer=fuzz.ratio)
        best_match = [match for match in all_matches if match[1] >= 70]

        if not best_match:
            bot.send_message(chat_id, f"Преподаватель '{teacher}' не найден.", reply_markup=back_button)
            return
        elif len(best_match) > 1:
            # Если найдено несколько совпадений, предлагаем уточнить
            markup = InlineKeyboardMarkup()
            for match in best_match:
                teacher_name = match[0]  # Имя преподавателя из списка
                similarity = match[1]   # Уровень схожести (процент)
                markup.add(InlineKeyboardButton(text=f"{teacher_name}", callback_data=f"select_teacher:{teacher_name}:{target_date}"))
            bot.send_message(chat_id, "Уточните, пожалуйста, преподавателя:", reply_markup=markup)
            return
        else:
            # Если найден только один преподаватель
            teacher = best_match[0][0]  # Имя единственного совпадения

        # Получаем расписание для преподавателя на указанную дату
        schedule = get_shed_by_teacher(target_date, teacher)
        if schedule:
            bot.send_message(chat_id, f"{schedule}", parse_mode='HTML')
            return

#Пары   
    elif re.match(r'пары', message.text, re.IGNORECASE):

        date_now = datetime.datetime.now()
        current_date = date_now.strftime('%d.%m.%Y')
        tommorow = (date_now + datetime.timedelta(days=1)).strftime('%d.%m.%Y')

        message_date = re.search(r'(\d{2}\.\d{2})(?:\.(\d{4}))?',message.text, re.IGNORECASE)

        if chat_group is None:
            bot.send_message(chat_id, f"У вас нет отслеживаемой группы.", reply_markup=back_button)
            sent_message = bot.send_message(chat_id, f"Вы хотите установить её?", reply_markup=markup_set_group)
            bot.register_next_step_handler(message, process_group_input, group_list, sent_message.message_id)
            return
        
        if re.findall(r'сегодня', message.text, re.IGNORECASE):
            target_date = current_date
            group_match = re.search(r'сегодня\s*(?:для\s*)?([А-Яа-я0-9]+[\s\-]?[0-9]+)', message.text, re.IGNORECASE)
            if group_match:
                chat_group = group_match.group(1)
        elif re.findall(r'завтра', message.text, re.IGNORECASE):
            target_date = tommorow
            group_match = re.search(r'завтра\s*(?:для\s*)?([А-Яа-я0-9]+[\s\-]?[0-9]+)', message.text, re.IGNORECASE)
            if group_match:
                chat_group = group_match.group(1)
        elif message_date:
            target_date = message_date.group(1)

            if not message_date.group(2):
                year = datetime.datetime.now().year
                target_date = f"{target_date}.{year}"
            else:
                target_date = f"{target_date}.{message_date.group(2)}"        
            
            try:
                target_date_obj = datetime.datetime.strptime(target_date, '%d.%m.%Y')
            except ValueError:
                bot.send_message(chat_id, f"Ошибка: Некорректная дата {target_date}.", reply_markup=back_button)
                target_date = None
                return

            group_match = re.search(r'\d{2}\.\d{2}(?:\.\d{4})?\s*(?:для\s*)?([А-Яа-я0-9]+[\s\-]?[0-9]+)', message.text, re.IGNORECASE)
            if group_match:
                chat_group = group_match.group(1)
        else:
            bot.send_message(chat_id, "Выберите нужную дату", reply_markup=markup_pairs)
            return

        best_match = process.extractOne(chat_group, group_list, score_cutoff=80)
        if best_match:
            chat_group = best_match[0]  # Устанавливаем наиболее подходящую группу
        else:
            bot.send_message(chat_id, f"Группа '{chat_group}' не найдена в списке.", reply_markup=back_button)
            return

        # Получаем расписание для указанной даты и группы
        schedule = get_shedule(target_date, chat_group)
        bot.send_message(chat_id, f"{schedule}", reply_markup=markup_pairs, parse_mode='HTML')  
       
#Кабинет
    elif re.match(r'кабинет', message.text, re.IGNORECASE):

        date_now = datetime.datetime.now()
        current_date = date_now.strftime('%d.%m.%Y')
        tommorow = (date_now + datetime.timedelta(days=1)).strftime('%d.%m.%Y')      

        message_date = re.search(r'(\d{2}\.\d{2})(?:\.(\d{4}))?', message.text, re.IGNORECASE)

        # Определяем кабинет из сообщения
        cabinet_match = re.search(r'\b(?:каб|кабинет|лаб)\b\s+(\S+)', message.text, re.IGNORECASE)
        if not cabinet_match:
            bot.send_message(chat_id, "Не удалось определить кабинет. Укажите корректный формат (например, 'кабинет 203').", reply_markup=back_button)
            return
        
        cabinet = cabinet_match.group(1).strip()

        # Определяем дату
        if re.findall(r'сегодня', message.text, re.IGNORECASE):
            target_date = current_date
        elif re.findall(r'завтра', message.text, re.IGNORECASE):
            target_date = tommorow
        elif message_date:
            target_date = message_date.group(1)
            if not message_date.group(2):
                year = datetime.datetime.now().year
                target_date = f"{target_date}.{year}"
            else:
                target_date = f"{target_date}.{message_date.group(2)}"
            try:
                target_date_obj = datetime.datetime.strptime(target_date, '%d.%m.%Y')
            except ValueError:
                bot.send_message(chat_id, f"Ошибка: Некорректная дата {target_date}.", reply_markup=back_button)
                target_date = None
                return
        else:
            target_date = current_date
            
        # Получаем расписание для указанной даты и группы
        schedule_cab = get_shed_by_cab(target_date, cabinet)
        bot.send_message(chat_id, f"{schedule_cab}", reply_markup=markup_pairs, parse_mode='HTML')  


#Звонки
    
    elif re.match(r'^\s*звонки\s*$', message.text, re.IGNORECASE):
            bot.send_message(chat_id, "Выберите нужную дату", reply_markup=markup_bells)
    
    elif re.match(r'звонки\s*(на?\s*)?сегодня', message.text, re.IGNORECASE):
        date_now = datetime.datetime.now()
        current_date = date_now.strftime('%d.%m.%Y')
        bells = get_bells(current_date)
        bot.send_message(chat_id, f"{bells}", reply_markup=markup_bells, parse_mode='HTML')
    
    elif re.match(r'звонки\s*(на?\s*)?завтра', message.text, re.IGNORECASE):
        date_now = datetime.datetime.now()
        tommorow = (date_now + datetime.timedelta(days=1)).strftime('%d.%m.%Y')
        bells = get_bells(tommorow)
        bot.send_message(chat_id, f"{bells}", reply_markup=markup_bells, parse_mode='HTML')    

    #Уведомления

    elif message.text == "Уведомления":
        bot.send_message(chat_id, "Включить уведомления о изменениях в расписании?", reply_markup=back_button)
    
    # Переключение уведомлений на основе текста кнопки
    elif re.match(r'Уведомления (выключены)', message.text, re.IGNORECASE):
        set_notifications(chat_id,True)
        new_status = "включены"
        notifications_status = True
        bot.send_message(chat_id, f"Уведомления {new_status}.", reply_markup=get_main_menu(notifications_status))  # Обновляем меню
    
    elif re.match(r'Уведомления (включены)', message.text, re.IGNORECASE):
        set_notifications(chat_id,False)
        notifications_status = False
        new_status = "выключены"
        bot.send_message(chat_id, f"Уведомления {new_status}.", reply_markup=get_main_menu(notifications_status))  # Обновляем меню

    #Информация
    elif message.text == "Информация":
        bot.send_message(chat_id,"Выберите интересуюший вас раздел.", reply_markup=markup_info, parse_mode="HTML")
    elif message.text == "Корпуса":
        bot.send_message(chat_id,buildings(),reply_markup=markup_info, parse_mode="HTML")
    

    #Активная группа + handler

    elif message.text == "Активная группа":
        if chat_group is not None:
            bot.send_message(chat_id, f"У вас уже есть отслеживаемая группа: {chat_group}.\nВы хотите сменить её?", reply_markup=markup_change_group)
        else:
            sent_message = bot.send_message(chat_id, "Введите группу для отслеживания изменений или нажмите 'Назад' для выхода в меню.", reply_markup=back_button)
            bot.register_next_step_handler(message, process_group_input, group_list, sent_message.message_id)


@bot.callback_query_handler(func=lambda call: call.data.startswith("select_teacher:"))
def handle_select_teacher(call):

    chat_id = call.message.chat.id
    message_id = call.message.message_id

    data = call.data.split(":")  # Разделяем callback_data
    teacher_name = data[1]       # Имя преподавателя
    target_date = data[2]        # Дата из callback_data

    bot.delete_message(chat_id, message_id)

    # Получаем расписание для выбранного преподавателя
    schedule = get_shed_by_teacher(target_date, teacher_name)
    if schedule:
        bot.send_message(chat_id,schedule, parse_mode='HTML')
        return

@bot.callback_query_handler(func=lambda call: True)
@log_request
def answer(call):
    group_list = []
    get_groups(group_list)
    
    if call.data == 'change_group':
        bot.delete_message(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id
            )

        sent_message = bot.send_message(call.message.chat.id, 
                         "Введите группу для отслеживания изменений или нажмите 'Назад' для выхода в меню.", 
                         reply_markup=back_button)
        bot.register_next_step_handler(call.message, 
                                       process_group_input, 
                                       group_list,
                                       sent_message.message_id
                                       )
    elif call.data == "back_group":

        bot.edit_message_text(
            text="Действие отменено",
            chat_id=call.message.chat.id,  # Указан chat_id
            message_id=call.message.message_id,  # Указан message_id
            reply_markup= None
        ) 

        return
# Обработка ввода группы
def is_valid_message(message):
    # Проверяем, что сообщение не пустое и не состоит только из символов, стикеров, ссылок или файлов
    if message.text:
        # Если сообщение состоит только из пробелов или знаков препинания, игнорируем его
        if not message.text.strip() or re.match(r'^[\W_]+$', message.text.strip()):
            return False
        
        # Проверка на наличие только ссылок (регулярное выражение для URL)
        if re.match(r'http[s]?://', message.text):
            return False
        
        # Проверка на стикеры и файлы
        if message.sticker or message.document or message.photo:
            return False
        
        return True
    return False

def process_group_input(message, group_list, initial_message_id):
    
    chat_id = message.chat.id
    group = message.text.strip()

    notifications_status = get_notifications_status(chat_id)

    group_normalized = group.replace(" ", "").replace("-", "").upper() 

    if group == "Назад" :
        # Изменяем изначальное сообщение

        bot.delete_message(
            chat_id=chat_id, 
            message_id=initial_message_id
            )

        # Отправляем новое сообщение с главным меню
        bot.send_message(chat_id, "Вы вернулись в главное меню.", reply_markup=get_main_menu(notifications_status))
        
        return
    
        # Проверяем сообщение на валидность
    if not is_valid_message(message):
        bot.send_message(chat_id, "Неправильая форма запроса.", reply_markup=back_button)
        bot.register_next_step_handler(message, process_group_input, group_list, initial_message_id)
        return

    
    else:
        # Найдем наиболее похожую группу из списка
        best_match = process.extractOne(group_normalized, group_list, scorer=fuzz.ratio)

        if best_match:
            # Если схожесть достаточна, подтверждаем установку группы
            matched_group, similarity_score = best_match
            if similarity_score > 80:  # Порог схожести (можно настроить)
                bot.send_message(chat_id, f"Группа '{matched_group}' установлена как активная для вашего чата.", reply_markup=get_main_menu(notifications_status))
                set_group(chat_id, matched_group)
            else:
                sent_message = bot.send_message(chat_id, f"Группа '{group}' не найдена в списке.", reply_markup=back_button)
                bot.register_next_step_handler(message, process_group_input, group_list, sent_message.message_id)

# Задачи уведомлений


def job_notify_tommorow():
    date_now = datetime.datetime.now()

    start_hour = 9
    end_hour = 21
    if not (start_hour <= date_now.hour < end_hour):
        return
    
    tommorow = (date_now + datetime.timedelta(days=1)).strftime('%d.%m.%Y')  
    groups = []

    check_changes(tommorow,groups)

    for group in groups:
        chats = []
        get_chat_notify_by_group(group, chats)

        if not chats or any(chat is None for chat in chats):
            continue
        schedule = get_change(tommorow,group) 

        for chat in chats:
            chat_id = chat[0]
            bot.send_message(chat_id, f"На завтра {schedule}", parse_mode='HTML')

def job_bells_tommorow():
    
    date_now = datetime.datetime.now()
    tommorow = (date_now + datetime.timedelta(days=1)).strftime('%d.%m.%Y')

    start_hour = 9
    end_hour = 21

    if not (start_hour <= date_now.hour < end_hour):
        return

    buildings = []
    bells_changes(tommorow,buildings)

    chats = []
    get_chat_notify(chats)
    for chat in chats:
        if buildings is not None:
            chat_id = chat[0]
            bells = get_bells(tommorow)
            bot.send_message(chat_id, f"Произошли изменения в расписании.\n{bells}", parse_mode='HTML')



def run_scheduler():
    schedule.every(30).minutes.do(job_notify_tommorow)
    schedule.every(30).minutes.do(job_bells_tommorow)
    while True:
        schedule.run_pending()
        time.sleep(1)

if __name__ == "__main__":
    # Запуск планировщика в отдельном потоке
    scheduler_thread = threading.Thread(target=run_scheduler, daemon=True)
    scheduler_thread.start()            

# Запуск бота
bot.polling(none_stop=True)