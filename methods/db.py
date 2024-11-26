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

#TAKE
def get_active_group(chat_id):


    conn = db_pool.getconn()
    cur = conn.cursor()

    try:
        cur.execute(f"SELECT active_group FROM chat_data WHERE chat_id = %s", (chat_id,))
        result = cur.fetchone()
        if result:
            return result[0]
        
    except Exception as e:
        print(f"Ошибка при получении активной группы: {e}")

    finally:
        cur.close()
        db_pool.putconn(conn)

def get_notifications_status(chat_id):

    conn = db_pool.getconn()
    cur = conn.cursor()

    try:
        cur.execute(f"SELECT notifications FROM chat_data WHERE chat_id = %s", (chat_id,))
        result = cur.fetchone()
        if result:
            return result[0]
        
    except Exception as e:
        print(f"Ошибка при получении статуса уведомлений: {e}")

    finally:
        cur.close()
        db_pool.putconn(conn)

#SET
def set_notifications(chat_id, type):

    conn = db_pool.getconn()
    cur = conn.cursor()

    try:
        cur.execute(
            """
            INSERT INTO chat_data (chat_id, notifications)
            VALUES (%s, %s)
            ON CONFLICT (chat_id) 
            DO UPDATE SET notifications = EXCLUDED.notifications
            """,
            (chat_id, type)
        )
        conn.commit()

    except Exception as e:
        print(f"Ошибка при установке уведомлений: {e}")

    finally:
        cur.close()
        db_pool.putconn(conn)

def set_group(chat_id,active_group):

    conn = db_pool.getconn()
    cur = conn.cursor()

    try:
        cur.execute(
            """
            INSERT INTO chat_data (chat_id, active_group)
            VALUES (%s, %s)
            ON CONFLICT (chat_id) 
            DO UPDATE SET active_group = EXCLUDED.active_group
            """,
            (chat_id, active_group)
        )
        conn.commit()

    except Exception as e:
        print(f"Ошибка при установке активной группы: {e}")

    finally:
        cur.close()
        db_pool.putconn(conn)

def add_chat(chat_id):

    conn = db_pool.getconn()
    cur = conn.cursor()

    try:
        cur.execute(
            '''
            INSERT INTO chat_data (chat_id) 
            VALUES (%s)
            ON CONFLICT (chat_id)
            DO NOTHING;
            ''', 
            (chat_id,)
        )
        conn.commit()

    except Exception as e:
        print(f"Ошибка при добавлении чата: {e}")

    finally:
        cur.close()
        db_pool.putconn(conn)
