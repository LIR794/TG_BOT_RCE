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

# def bells_changes(date, buildings):
    

#     # Заголовки для запроса
#     header = {
#         "Accept": "application/json",
#     }

#     # Запрос данных расписания
#     response = requests.get(f"https://api.s.iswebdev.ru/api/bells/public?date={date}", headers=header)

#     if response.status_code != 200:
#         print(f"Ошибка при загрузке данных: {response.status_code}")
#         return

#     data = response.json()
#     last_update_changed = data['last_updated']

#     connection = None
#     cursor = None

#     try:
#         # Получаем соединение из пула
#         connection = connection_pool.getconn()
#         cursor = connection.cursor()

#         # Проверяем, есть ли уже данные на эту дату
#         cursor.execute("SELECT date_request FROM bells_table WHERE date_request = %s", (date, ))
#         existing_date_request = cursor.fetchone()

#         if not existing_date_request:
#             # Если данных нет, добавляем новые
#             for bells in data['periods']:
#                 group_name = bells['group_name']
#                 schedule_type = schedule['type']
#                 schedule_data = schedule['lessons']
#                 if schedule_type == 'changes':
#                     cursor.execute(
#                         """
#                         INSERT INTO schedule_table (last_updated, date_request, schedule, group_name)
#                         VALUES (%s, %s, %s, %s)
#                         """,
#                         (last_update_changed, date, json.dumps(schedule_data, ensure_ascii=False), group_name)
#                     )
#                     groups_to_send.append(group_name)
#             connection.commit()
#             return

        # Если данные уже существуют, проверяем изменения
    #     for schedule in data['schedules']:
    #         group_name = schedule['group_name']
    #         schedule_type = schedule['type']
    #         schedule_data = schedule['lessons']

    #         serialized_schedule_data = json.dumps(schedule_data, ensure_ascii=False)

    #         # Проверяем расписание из базы данных
    #         cursor.execute(
    #             """
    #             SELECT schedule FROM schedule_table WHERE date_request = %s AND group_name = %s
    #             """,
    #             (date, group_name)
    #         )
    #         db_schedule = cursor.fetchone()
    #         #print(db_schedule)
    #         if schedule_type == 'changes':
    #             if not db_schedule:
    #                 # Группа не найдена в базе, добавляем новую
    #                 cursor.execute(
    #                     """
    #                     INSERT INTO schedule_table (last_updated, date_request, schedule, group_name)
    #                     VALUES (%s, %s, %s, %s)
    #                     """,
    #                     (last_update_changed, date, serialized_schedule_data, group_name)
    #                 )
    #                 groups_to_send.append(group_name)
    #             else:
    #                 # Группа найдена, сравниваем расписания
    #                 db_schedule_data = db_schedule[0]  # Извлекаем содержимое из первого элемента кортежа

    #                 if db_schedule_data != schedule_data:
    #                     # Обновляем расписание в базе данных
    #                     cursor.execute(
    #                         """
    #                         UPDATE schedule_table
    #                         SET schedule = %s, last_updated = %s
    #                         WHERE group_name = %s AND date_request = %s
    #                         """,
    #                         (serialized_schedule_data, last_update_changed, group_name, date)
    #                     )
    #                     groups_to_send.append(group_name)


    #         elif schedule_type == 'main':
    #             if db_schedule:
    #                 db_schedule_data = db_schedule[0]

    #                 if db_schedule_data != schedule_data:

    #                     cursor.execute(
    #                         """
    #                         UPDATE schedule_table
    #                         SET schedule = %s, last_updated = %s
    #                         WHERE group_name = %s AND date_request = %s
    #                         """,
    #                         (serialized_schedule_data, last_update_changed, group_name, date)
    #                     )
    #                     groups_to_send.append(group_name)

    #     connection.commit()

    # except Exception as e:
    #     print(f"Ошибка при работе с базой данных: {e}")
    #     if connection:
    #         connection.rollback()
    # finally:
    #     # Возвращаем соединение в пул
    #     if cursor:
    #         cursor.close()
    #     if connection:
    #         connection_pool.putconn(connection)


    # for struc in data:
    #     schedule_type = struc.get('type', '')
    #     building = struc.get('building', 'Неизвестно')
    #     schedule_type = bells_to_ru.get(schedule_type, schedule_type)
        
    #     bell_list = []
    #     for bells in struc.get("periods", []):
    #         bell_index = str(bells.get('index', ''))
    #         period_from = bells.get('period_from', '')
    #         period_to = bells.get('period_to', '')
    #         period_from_after = bells.get('period_from_after', '')
    #         period_to_after = bells.get('period_to_after', '')

    #         if not period_from_after or period_from_after == "None":
    #             period_from_after = ""
    #             period_to_after = ""
            
    #         bell_index = index_to_emoji.get(bell_index, bell_index)

    #         bells_info = f"{bell_index} | {period_from} - {period_to} | {period_from_after} - {period_to_after}"
    #         bell_list.append(bells_info)

    #     if bell_list:
    #         schedule_key = "\n\n".join(bell_list)
    #         if schedule_key not in schedule_types[schedule_type]:
    #             schedule_types[schedule_type][schedule_key] = []
    #         schedule_types[schedule_type][schedule_key].append(building)

    # result = ""
    
    # if schedule_types["Основное"]:
    #     for schedule_key, buildings in schedule_types["Основное"].items():
    #         buildings_list = ", ".join(sorted(buildings))
    #         result += f"Основное: {buildings_list}\n\n{schedule_key}\n\n"
    #     result += f"<b>{date}</b>\n\n"

    # if schedule_types["Изменения"]:
    #     for schedule_key, buildings in schedule_types["Изменения"].items():
    #         buildings_list = ", ".join(sorted(buildings))
    #         result += f"Изменения: {buildings_list}\n\n{schedule_key}\n\n"

    # return result.strip()