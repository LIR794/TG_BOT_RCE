import re

from fuzzywuzzy import(
    process,
    fuzz
)

from methods.db import (
    set_group, 
    get_notifications_status
)


from logics.markups import (
    get_main_menu,
    markup_back,
)

from methods.pairs import (
    get_groups,
    get_shed_by_teacher,
)



def answer(bot, call):

    get_groups(group_list := [])
    
    if call.data == 'change_group':
        bot.delete_message(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id
            )

        sent_message = bot.send_message(call.message.chat.id, 
                         "Введите группу для отслеживания изменений или нажмите 'Назад' для выхода в меню.", 
                         reply_markup=markup_back)
        bot.register_next_step_handler(sent_message,    
                                       process_group_input,
                                       bot,
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

def process_group_input(message, bot, group_list, initial_message_id):

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
        bot.send_message(chat_id, "Вы вернулись в главное меню.", reply_markup=get_main_menu(chat_id, notifications_status))
        
        return
    
        # Проверяем сообщение на валидность
    if not is_valid_message(message):
        bot.send_message(chat_id, "Неправильая форма запроса.", reply_markup=markup_back)
        bot.register_next_step_handler(message, process_group_input, group_list, initial_message_id)
        return

    
    else:
        # Найдем наиболее похожую группу из списка
        best_match = process.extractOne(group_normalized, group_list, scorer=fuzz.ratio)

        if best_match:
            # Если схожесть достаточна, подтверждаем установку группы
            matched_group, similarity_score = best_match
            if similarity_score > 80:  # Порог схожести (можно настроить)
                bot.send_message(chat_id, f"Группа '{matched_group}' установлена как активная для вашего чата.", reply_markup=get_main_menu(chat_id, notifications_status))
                set_group(chat_id, matched_group)
            else:
                sent_message = bot.send_message(chat_id, f"Группа '{group}' не найдена в списке.", reply_markup=markup_back)
                bot.register_next_step_handler(message, process_group_input, group_list, sent_message.message_id)

def select_teacher(bot,call):

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