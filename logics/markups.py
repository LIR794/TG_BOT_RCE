from telebot import types
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from methods.db import (
    get_active_group
)
inline_back = types.InlineKeyboardButton('Назад', callback_data="back_group")

# Функция для создания основного меню с обновленной кнопкой уведомлений
def get_main_menu(chat_id, notifications_status):
    
    active = get_active_group(chat_id)

    main_menu = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)

    btn_active = types.KeyboardButton('Активная группа')
    btn_notifications = types.KeyboardButton(f'Уведомления включены {active}' if notifications_status else 'Уведомления выключены')
    btn_bells = types.KeyboardButton('Звонки')
    btn_pairs = types.KeyboardButton('Пары')
    btn_info = types.KeyboardButton('Информация')

    main_menu.add(btn_active, btn_info)
    main_menu.add(btn_notifications)
    main_menu.add(btn_bells, btn_pairs)

    return main_menu

# Кнопка назад
btn_back = types.KeyboardButton('Назад')
markup_back = types.ReplyKeyboardMarkup(resize_keyboard=True)
markup_back.add(btn_back)

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
markup_change_group.add(btn_change_group)
markup_change_group.add(inline_back)

# Inline-клавиатура для установки группы
markup_set_group = types.InlineKeyboardMarkup()
btn_set_group = types.InlineKeyboardButton(text='Установить', callback_data="change_group")
markup_set_group.add(btn_set_group)
markup_set_group.add(inline_back)
