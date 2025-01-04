import os
from datetime import datetime
from psycopg2 import pool
from dotenv import load_dotenv

load_dotenv("/app/.env")

db_pool = pool.SimpleConnectionPool(
    minconn=1,  
    maxconn=100,
    user= os.getenv('user'),
    password= os.getenv('password'),
    host= os.getenv('host'),
    port= os.getenv('port'),
    database= os.getenv('database')
)

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

day_to_ru = {
    "Monday": "Понедельник",
    "Tuesday": "Вторник",
    "Wednesday": "Среда",
    "Thursday": "Четверг",
    "Friday": "Пятница",
    "Saturday": "Суббота",
    "Sunday": "Воскресенье"
}


def get_chat_notify(chats):

    conn = db_pool.getconn()
    cur = conn.cursor()

    try:
        cur.execute(
            """
            SELECT chat_id FROM chat_data WHERE notifications = %s
            """,
            ("TRUE")
        )
        # Получаем все chat_id и добавляем их в список
        chats.extend(cur.fetchall())

    except Exception as e:
        print(f"Ошибка при получении данных: {e}")

    finally:
        # Освобождаем соединение обратно в пул
        cur.close()
        db_pool.putconn(conn)

def get_chat_notify_by_group(group, chats):
    
    conn = db_pool.getconn()
    cur = conn.cursor()

    try:
        cur.execute(
            """
            SELECT chat_id FROM chat_data WHERE active_group = %s AND notifications = %s
            """,
            (group, "TRUE")
        )
        # Получаем все chat_id и добавляем их в список
        chats.extend(cur.fetchall())

    except Exception as e:
        print(f"Ошибка при получении данных: {e}")

    finally:
        # Освобождаем соединение обратно в пул
        cur.close()
        db_pool.putconn(conn)

def get_schedule_change(date, group):

    # Получаем соединение из пула
    conn = db_pool.getconn()
    cur = conn.cursor()

    try:
        cur.execute(
            """
            SELECT schedule FROM schedule_table WHERE date_request = %s AND group_name = %s
            """,
            (date, group)
        )
        data = cur.fetchone()

        if not data:
            return f"Нет данных для группы {group} на {date}"

        # Преобразуем данные в структуру расписания
        lessons = data[0]  # data[0] содержит список словарей с расписанием

        day_name = datetime.strptime(date,"%d.%m.%Y").strftime("%A")

        day_name = day_to_ru.get(day_name, day_name)

        result = f"произошли изменения у группы {group}\n\n"

        # Формируем строку для каждого занятия
        for lesson in lessons:
            index = str(lesson.get('index', ''))
            subject = lesson.get('subject_name', 'Без названия')
            message = lesson.get('message', '')
            cabinet = lesson.get('cabinet', '—') or ""
            teachers = ", ".join(teacher.get('name', 'Неизвестно') for teacher in (lesson.get('teachers') or []))

            # Преобразуем индекс пары в эмодзи
            index = index_to_emoji.get(index, index)

            # Если subject пустой, заменяем на message
            if not subject and message:
                subject = message
                # Структура без кабинета и преподавателя
                result += f"{index} {subject}\n"
            elif subject:
                # Стандартная структура
                result += f"{index} {subject} | {cabinet} ({teachers})\n"
        result += f"\n<b>{date} ({day_name})</b>"
        return result.strip()

    except Exception as e:
        print(f"Ошибка при работе с базой данных: {e}")
    finally:
        # Освобождаем соединение обратно в пул
        cur.close()
        db_pool.putconn(conn)

def get_bells_change(date, building):

    # Получаем соединение из пула
    conn = db_pool.getconn()
    cur = conn.cursor()

    try:
        placeholders = ', '.join(['%s'] * len(building))
        cur.execute(
            f"""
            SELECT bells, building FROM bells_table WHERE date_request = %s AND building IN ({placeholders})
            """,
            (date, *building)
        )
        data = cur.fetchall()

        if not data:
            return
        
        day_name = datetime.strptime(date,"%d.%m.%Y").strftime("%A")
        day_name = day_to_ru.get(day_name, day_name)  

        bell_map = {}

        for struc in data:
            bells = struc[0]  # Список звонков
            building = struc[1]  # Здание

            # Преобразуем список звонков в неизменяемый тип для использования в качестве ключа
            bells_key = tuple(sorted(
                (
                    period.get('index', ''),
                    period.get('period_from', ''),
                    period.get('period_to', ''),
                    period.get('period_from_after', ''),
                    period.get('period_to_after', '')
                ) for period in bells
            ))

            # Группируем здания по одинаковому расписанию
            if bells_key not in bell_map:
                bell_map[bells_key] = []

            bell_map[bells_key].append(building)

        result_message = ""

        for bells_key, buildings in bell_map.items():
            # Формируем сообщение для зданий с одинаковым расписанием
            buildings_str = ', '.join(buildings)
            result_message += f"Произошли изменения в: {buildings_str}\n\n"

            for index, period in enumerate(bells_key, start=1):
                bell_index = index_to_emoji.get(str(period[0]), str(period[0]))
                period_from = period[1]
                period_to = period[2]
                period_from_after = period[3] if period[3] != "None" else ""
                period_to_after = period[4] if period[4] != "None" else ""

                result_message += f"{bell_index} | {period_from} - {period_to}"
                if period_from_after and period_to_after:
                    result_message += f" | {period_from_after} - {period_to_after}"
                result_message += "\n\n"

        result_message += f"<b>{date} ({day_name})</b>"

        return result_message.strip()
        

    except Exception as e:
        print(f"Ошибка при работе с базой данных: {e}")
    finally:
        cur.close()
        db_pool.putconn(conn)