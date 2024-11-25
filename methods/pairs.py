import requests

def get_groups(groups):    
    # Заголовки для запроса
    header = {
        "Accept": "application/json",
    }

    # Запрос данных расписания
    response = requests.get("https://апи.пары.ркэ.рф/api/groups/public?", headers=header)

    data = response.json()

    for subj in data:
        groups.append(subj["name"])

def get_bells(date,building):
    header = {
        "Accept": "application/json",
    }

    params = {
        "date": date,
        "building":building
    }

    response = requests.get("https://апи.пары.ркэ.рф/api/bells/public", headers=header, params=params)
    
    data = response.json()

    if isinstance(data, dict) and "message" in data:
        return "Выходной" 

    index_to_emoji = {
        "0": "0️⃣",
        "1": "1️⃣",
        "2": "2️⃣",
        "3": "3️⃣",
        "4": "4️⃣",
        "5": "5️⃣",
        "6": "6️⃣",
        "7": "7️⃣"
    }

    schedule_types = {
        "Основное": {},
        "Изменения": {}
    }

    bells_to_ru = {
        "main": "Основное",
        "changes": "Изменения"
    }

    for struc in data:
        schedule_type = struc.get('type', '')
        building = struc.get('building', 'Неизвестно')
        schedule_type = bells_to_ru.get(schedule_type, schedule_type)
        
        bell_list = []
        for bells in struc.get("periods", []):
            bell_index = str(bells.get('index', ''))
            period_from = bells.get('period_from', '')
            period_to = bells.get('period_to', '')
            period_from_after = bells.get('period_from_after', '')
            period_to_after = bells.get('period_to_after', '')

            if not period_from_after or period_from_after == "None":
                period_from_after = ""
                period_to_after = ""
            
            bell_index = index_to_emoji.get(bell_index, bell_index)

            bells_info = f"{bell_index} | {period_from} - {period_to} | {period_from_after} - {period_to_after}"
            bell_list.append(bells_info)

        if bell_list:
            schedule_key = "\n\n".join(bell_list)
            if schedule_key not in schedule_types[schedule_type]:
                schedule_types[schedule_type][schedule_key] = []
            schedule_types[schedule_type][schedule_key].append(building)

    result = ""
    
    if schedule_types["Основное"]:
        for schedule_key, buildings in schedule_types["Основное"].items():
            buildings_list = ", ".join(sorted(buildings))
            result += f"Основное: {buildings_list}\n\n{schedule_key}\n\n"
        result += f"<b>{date}</b>\n\n"

    if schedule_types["Изменения"]:
        for schedule_key, buildings in schedule_types["Изменения"].items():
            buildings_list = ", ".join(sorted(buildings))
            result += f"Изменения: {buildings_list}\n\n{schedule_key}\n\n"

    return result.strip()

def get_shedule(date,group):    

    header = {
        "Accept": "application/json",
    }
    
    params = {
        "date": date,
        "group": group
    }

    response = requests.get(f"https://апи.пары.ркэ.рф/api/schedules/public", headers=header, params=params)

    data = response.json()
    
    if not data.get('schedules'):
        return "Выходной" 
    
    group_data = {
        "Дата": date,
        "Группа": group,
        "Расписание": []
    }

    for schedule in data['schedules']:
        schedule_type = schedule.get('type', '')

        sched_to_ru ={
            "main": "Основное",
            "changes": "Изменения"
        }

        schedule_type = sched_to_ru.get(schedule_type, schedule_type)

        for lesson in schedule['lessons']:

            index = str(lesson.get('index', ''))
            subject = lesson.get('subject_name', '')
            cabinet = lesson.get('cabinet', '')
            message = lesson.get('message','')
            teachers = ", ".join(teacher.get('name', '') for teacher in (lesson.get('teachers') or []))
            
            index_to_emoji = {
                "0": "0️⃣",
                "1": "1️⃣",
                "2": "2️⃣",
                "3": "3️⃣",
                "4": "4️⃣",
                "5": "5️⃣",
                "6": "6️⃣",
                "7": "7️⃣"
            }
            
            index = index_to_emoji.get(index, index)

            if not subject and message:
                subject = message
                # Если subject заменён на message, создаём другую структуру
                group_data["Расписание"].append({
                    "Номер пары": index,
                    "Название пары": subject,
                    "Тип": schedule_type
                })
                continue

            lesson_info = {
                "Номер пары": index,
                "Название пары": subject,
                "Кабинет": cabinet,
                "Преподаватель": teachers,
                "Тип": schedule_type
            }
            group_data["Расписание"].append(lesson_info)

    result = f"<b>{group_data['Группа']}</b> {schedule_type}\n\n"
    for lesson in group_data["Расписание"]:
        if "Кабинет" in lesson and "Преподаватель" in lesson:
            result += f"{lesson['Номер пары']} {lesson['Название пары']} | {lesson['Кабинет']} (<i>{lesson['Преподаватель']}</i>)\n"
        else:
            result += f"{lesson['Номер пары']} {lesson['Название пары']}\n"
    result += f"\n<b>{group_data['Дата']}</b>"

    return result
