import datetime

from notifications.db_matcher import (
    check_changes,
    bells_changes
)

from notifications.get_schedule import (
    get_chat_notify_by_group, 
    get_chat_notify,
    get_schedule_change,
    get_bells_change
)

def job_notify_tommorow(bot):
    
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
        schedule = get_schedule_change(tommorow,group) 

        for chat in chats:
            chat_id = chat[0]
            bot.send_message(chat_id, f"На завтра {schedule}", parse_mode='HTML')

def job_bells_tommorow(bot):
    
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
    if buildings:
        bells = get_bells_change(tommorow,buildings)
        for chat in chats:
            chat_id = chat[0]
            bot.send_message(chat_id, bells, parse_mode='HTML')