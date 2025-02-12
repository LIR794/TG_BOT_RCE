import datetime
import re

from logics.supps_handlers import (
    process_group_input
)
from fuzzywuzzy import(
    process,
    fuzz
)
from telebot.types import (
    InlineKeyboardMarkup, 
    InlineKeyboardButton
)
from methods.db import (
    add_chat, 
    set_notifications, 
    get_active_group, 
    get_notifications_status
)

from methods.messages import ( 
    start_message, 
    help_message, 
    buildings
)

from logics.markups import (
    get_main_menu,
    markup_info,
    markup_back,
    markup_bells,
    markup_pairs,
    markup_set_group,
    markup_change_group
)

from methods.pairs import (
    get_groups, 
    get_teachers, 
    get_shedule, 
    get_shed_by_teacher, 
    get_bells, 
    get_shed_by_cab
)

get_teachers(teachers_list := [])

get_groups(group_list := [])

date_now = datetime.datetime.now()
current_date = date_now.strftime('%d.%m.%Y')
tommorow = (date_now + datetime.timedelta(days=1)).strftime('%d.%m.%Y')
    

def start_bot(bot,message):

    chat_id = message.chat.id
    notifications_status = get_notifications_status(chat_id)
    if notifications_status is None:
        notifications_status= False
    bot.send_message(chat_id, start_message(), reply_markup=get_main_menu(chat_id, notifications_status))

    add_chat(chat_id)

def help(bot,message):

    chat_id = message.chat.id
    notifications_status = get_notifications_status(chat_id)

    if notifications_status is None:
        notifications_status= False

    bot.send_message(chat_id, help_message(), reply_markup=get_main_menu(chat_id, notifications_status), parse_mode="HTML")

def back_request(bot, chat_id):

    notifications_status = get_notifications_status(chat_id)

    bot.send_message(chat_id, "Вы вернулись в главное меню.", reply_markup=get_main_menu(chat_id, notifications_status))

def teacher_request (bot,message,chat_id):
    

    teacher = None
    target_date = None 
    message_date = None

    teacher_match = re.search(r'Преподаватель\s+([а-яё]+)', message.text, re.IGNORECASE)
    message_date = re.search(r'(\d{2}\.\d{2})(?:\.(\d{4}))?', message.text, re.IGNORECASE)

    if teacher_match:
        teacher = teacher_match.group(1).strip()
    else:
        bot.send_message(chat_id, "Не удалось найти имя преподавателя в запросе.", reply_markup=markup_back)
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
            bot.send_message(chat_id, f"Ошибка: Некорректная дата {target_date}.", reply_markup=markup_back)
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
        bot.send_message(chat_id, f"Преподаватель '{teacher}' не найден.", reply_markup=markup_back)
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
def pairs_request (bot,message,chat_id):

    chat_group = get_active_group(chat_id)

    message_date = re.search(r'(\d{2}\.\d{2})(?:\.(\d{4}))?',message.text, re.IGNORECASE)

    if chat_group is None:
        bot.send_message(chat_id, f"У вас нет отслеживаемой группы.", reply_markup=markup_back)
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
            bot.send_message(chat_id, f"Ошибка: Некорректная дата {target_date}.", reply_markup=markup_back)
            target_date = None
            return

        group_match = re.search(rf'{message_date}\s*(?:для\s*)?([А-Яа-я0-9]+[\s\-]?[0-9]+)', message.text, re.IGNORECASE)
        
        if group_match:
            chat_group = group_match.group(1)
    else:
        bot.send_message(chat_id, "Выберите нужную дату", reply_markup=markup_pairs)
        return

    best_match = process.extractOne(chat_group, group_list, score_cutoff=80)
    if best_match:
        chat_group = best_match[0]  # Устанавливаем наиболее подходящую группу
    else:
        bot.send_message(chat_id, f"Группа '{chat_group}' не найдена в списке.", reply_markup=markup_back)
        return

    # Получаем расписание для указанной даты и группы
    schedule = get_shedule(target_date, chat_group)
    bot.send_message(chat_id, f"{schedule}", reply_markup=markup_pairs, parse_mode='HTML')  

#Кабинет 
def cab_request(bot,message,chat_id):

    message_date = re.search(r'(\d{2}\.\d{2})(?:\.(\d{4}))?', message.text, re.IGNORECASE)

    # Определяем кабинет из сообщения
    cabinet_match = re.search(r'\b(?:каб|кабинет|лаб)\b\s+(\S+)', message.text, re.IGNORECASE)

    if not cabinet_match:

        bot.send_message(chat_id, "Не удалось определить кабинет. Укажите корректный формат (например, 'кабинет 203').", reply_markup=markup_back)

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

            bot.send_message(chat_id, f"Ошибка: Некорректная дата {target_date}.", reply_markup=markup_back)
            
            target_date = None
            
            return
    else:
        target_date = current_date
        
    # Получаем расписание для указанной даты и группы
    schedule_cab = get_shed_by_cab(target_date, cabinet)
    
    bot.send_message(chat_id, f"{schedule_cab}", parse_mode='HTML')  

#Звонки
def bells_request(bot,message,chat_id):

    if re.findall(r'сегодня', message.text, re.IGNORECASE):

        bells = get_bells(current_date)

        bot.send_message(chat_id, f"{bells}", reply_markup=markup_bells, parse_mode='HTML')

    elif re.findall(r'завтра', message.text, re.IGNORECASE):

        bells = get_bells(tommorow)

        bot.send_message(chat_id, f"{bells}", reply_markup=markup_bells, parse_mode='HTML')    

    else:

        bot.send_message(chat_id, "Выберите нужную дату", reply_markup=markup_bells)

#Информация
def information_request(bot, chat_id):

    bot.send_message(chat_id,"Выберите интересуюший вас раздел.", reply_markup=markup_info, parse_mode="HTML")

#Здания
def buildings_request(bot, chat_id):

    bot.send_message(chat_id,buildings(),reply_markup=markup_info, parse_mode="HTML")

# #Уведомления 
# # Переключение уведомлений на основе текста кнопки
def notifications_request(bot,message,chat_id):
        
        bot.delete_message(
            chat_id=chat_id, 
            message_id=message.id
            )
        
        if re.findall('выключены', message.text, re.IGNORECASE):
            set_notifications(chat_id,True)
            new_status = "включены"
            notifications_status = True
        
            bot.send_message(chat_id, f"Уведомления {new_status}.", reply_markup=get_main_menu(chat_id, notifications_status))  # Обновляем меню
        
        if re.findall('включены', message.text, re.IGNORECASE):
            set_notifications(chat_id,False)
            new_status = "выключены"
            notifications_status = False
        
            bot.send_message(chat_id, f"Уведомления {new_status}.", reply_markup=get_main_menu(chat_id, notifications_status))  # Обновляем меню


def active_group_request(bot, message, chat_id):

    chat_group = get_active_group(chat_id)
    
    if chat_group is not None:
        bot.send_message(chat_id, f"У вас уже есть отслеживаемая группа: {chat_group}.\nВы хотите сменить её?", reply_markup=markup_change_group)
    else:
        sent_message = bot.send_message(chat_id, "Введите группу для отслеживания изменений или нажмите 'Назад' для выхода в меню.", reply_markup=markup_back)
        bot.register_next_step_handler(message, process_group_input, bot, group_list, sent_message.message_id)
