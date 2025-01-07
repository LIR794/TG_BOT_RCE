from psycopg2 import pool
import requests
import json
from dotenv import load_dotenv
import os

load_dotenv("/app/.env")

connection_pool = pool.SimpleConnectionPool(
    minconn=1,  
    maxconn=100,
    user= os.getenv('user'),
    password= os.getenv('password'),
    host= os.getenv('host'),
    port= os.getenv('port'),
    database= os.getenv('database')
)

def check_changes(date, groups_to_send):
    

    # Заголовки для запроса
    header = {
        "Accept": "application/json",
    }

    # Запрос данных расписания
    response = requests.get(f"https://апи.пары.ркэ.рф/api/schedules/public?date={date}", headers=header)

    if response.status_code != 200:
        if (message := response.json().get('message')):
            print("Ошибка получения изменений в расписании:",message)
            return
        else:
            print(f"Ошибка при загрузке данных: {response.status_code}")
            return

    data = response.json()
    last_update_changed = data['last_updated']

    connection = None
    cursor = None

    try:
        # Получаем соединение из пула
        connection = connection_pool.getconn()
        cursor = connection.cursor()

        # Проверяем, есть ли уже данные на эту дату
        cursor.execute("SELECT date_request FROM schedule_table WHERE date_request = %s", (date, ))
        existing_date_request = cursor.fetchone()

        if not existing_date_request:
            # Если данных нет, добавляем новые
            for schedule in data['schedules']:
                group_name = schedule['group_name']
                schedule_type = schedule['type']
                schedule_data = schedule['lessons']
                if schedule_type == 'changes':
                    cursor.execute(
                        """
                        INSERT INTO schedule_table (last_updated, date_request, schedule, group_name)
                        VALUES (%s, %s, %s, %s)
                        """,
                        (last_update_changed, date, json.dumps(schedule_data, ensure_ascii=False), group_name)
                    )
                    groups_to_send.append(group_name)
            connection.commit()
            return

        # Если данные уже существуют, проверяем изменения
        for schedule in data['schedules']:
            group_name = schedule['group_name']
            schedule_type = schedule['type']
            schedule_data = schedule['lessons']

            serialized_schedule_data = json.dumps(schedule_data, ensure_ascii=False)

            # Проверяем расписание из базы данных
            cursor.execute(
                """
                SELECT schedule FROM schedule_table WHERE date_request = %s AND group_name = %s
                """,
                (date, group_name)
            )
            db_schedule = cursor.fetchone()
            #print(db_schedule)
            if schedule_type == 'changes':
                if not db_schedule:
                    # Группа не найдена в базе, добавляем новую
                    cursor.execute(
                        """
                        INSERT INTO schedule_table (last_updated, date_request, schedule, group_name)
                        VALUES (%s, %s, %s, %s)
                        """,
                        (last_update_changed, date, serialized_schedule_data, group_name)
                    )
                    groups_to_send.append(group_name)
                else:
                    # Группа найдена, сравниваем расписания
                    db_schedule_data = db_schedule[0]  # Извлекаем содержимое из первого элемента кортежа

                    if db_schedule_data != schedule_data:
                        # Обновляем расписание в базе данных
                        cursor.execute(
                            """
                            UPDATE schedule_table
                            SET schedule = %s, last_updated = %s
                            WHERE group_name = %s AND date_request = %s
                            """,
                            (serialized_schedule_data, last_update_changed, group_name, date)
                        )
                        groups_to_send.append(group_name)


            elif schedule_type == 'main':
                if db_schedule:
                    db_schedule_data = db_schedule[0]

                    if db_schedule_data != schedule_data:

                        cursor.execute(
                            """
                            UPDATE schedule_table
                            SET schedule = %s, last_updated = %s
                            WHERE group_name = %s AND date_request = %s
                            """,
                            (serialized_schedule_data, last_update_changed, group_name, date)
                        )
                        groups_to_send.append(group_name)

        connection.commit()

    except Exception as e:
        print(f"Ошибка при работе с базой данных: {e}")
        if connection:
            connection.rollback()
    finally:
        # Возвращаем соединение в пул
        if cursor:
            cursor.close()
        if connection:
            connection_pool.putconn(connection)

def bells_changes(date, builds):
    

    # Заголовки для запроса
    header = {
        "Accept": "application/json",
    }

    # Запрос данных расписания
    response = requests.get(f"https://апи.пары.ркэ.рф/api/bells/public?date={date}", headers=header)

    if response.status_code != 200:
        if (message := response.json().get('message')):
            print("Ошибка получения изменений в звонках:",message)
            return
        else:
            print(f"Ошибка при загрузке данных: {response.status_code}")
            return

    data = response.json()
    
    connection = None
    cursor = None

    try:
        # Получаем соединение из пула
        connection = connection_pool.getconn()
        cursor = connection.cursor()

        # Проверяем, есть ли уже данные на эту дату
        cursor.execute("SELECT date_request FROM bells_table WHERE date_request = %s", (date, ))
        existing_date_request = cursor.fetchone()

        if not existing_date_request:
            # Если данных нет, добавляем новые
            for struc in data:

                bells_type = struc['type']
                building = struc['building']
                periods = struc ['periods']
                if bells_type == "changes":
                    cursor.execute(
                        """
                        INSERT INTO bells_table (date_request, bells, building)
                        VALUES (%s, %s, %s)
                        """,
                        (date, json.dumps(periods, ensure_ascii=False), building)
                    )
                    builds.append(building)
                    connection.commit()
            return

        # Если данные уже существуют, проверяем изменения
        for struc in data:
            bells_type = struc['type']
            building = struc['building']
            periods = struc ['periods']
            
            serialized_bells_data = json.dumps(periods, ensure_ascii=False)

            # Проверяем расписание из базы данных
            cursor.execute(
                """
                SELECT bells FROM bells_table WHERE date_request = %s AND building = %s
                """,
                (date, building)
            )
            db_schedule = cursor.fetchone()

            if bells_type == 'changes':
                if not db_schedule:
                    # Группа не найдена в базе, добавляем новую
                    cursor.execute(
                        """
                        INSERT INTO bells_table (date_request, bells, building)
                        VALUES (%s, %s, %s)
                        """,
                        (date, serialized_bells_data, building)
                    )
                    builds.append(building)
                else:
                    # Группа найдена, сравниваем расписания
                    db_schedule_data = db_schedule[0]  # Извлекаем содержимое из первого элемента кортежа

                    if db_schedule_data != periods:
                        # Обновляем расписание в базе данных
                        cursor.execute(
                            """
                            UPDATE bells_table
                            SET bells = %s
                            WHERE building = %s AND date_request = %s
                            """,
                            (serialized_bells_data, building, date)
                        )
                        builds.append(building)

            elif bells_type == 'main':
                if db_schedule:
                    db_schedule_data = db_schedule[0]

                    if db_schedule_data != periods:

                        cursor.execute(
                            """
                            UPDATE bells_table
                            SET bells = %s
                            WHERE building = %s AND date_request = %s
                            """,
                            (serialized_bells_data, building, date)
                        )
                        builds.append(building)

        connection.commit()

    except Exception as e:
        print(f"Ошибка при работе с базой данных: {e}")
        if connection:
            connection.rollback()
    finally:
        # Возвращаем соединение в пул
        if cursor:
            cursor.close()
        if connection:
            connection_pool.putconn(connection)