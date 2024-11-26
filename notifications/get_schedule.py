from psycopg2 import pool
from dotenv import load_dotenv
import os

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

def get_chat_notify(group, chats):
    
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

def get_change(date, group):

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

        result = f"Произошли изменения у группы {group}\n\n"

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

        return result.strip()

    except Exception as e:
        print(f"Ошибка при работе с базой данных: {e}")
    finally:
        # Освобождаем соединение обратно в пул
        cur.close()
        db_pool.putconn(conn)