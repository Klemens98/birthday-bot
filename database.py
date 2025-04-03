import psycopg2
import yaml
from datetime import datetime
import pytz

def load_config():
    with open('config.yaml', 'r') as file:
        return yaml.safe_load(file)

class DatabaseService:
    def __init__(self):
        config = load_config()
        db_config = config['DATABASE']
        self.conn = psycopg2.connect(
            dbname=db_config['NAME'],
            user=db_config['USER'],
            password=db_config['PASSWORD'],
            host=db_config['HOST'],
            port=db_config['PORT']
        )

    def get_todays_birthdays(self):
        tz = pytz.timezone('Europe/Berlin')
        now = datetime.now(tz)
        
        with self.conn.cursor() as cur:
            cur.execute("""
                SELECT user_id, username, birthday, dm_preference 
                FROM birthdays 
                WHERE EXTRACT(MONTH FROM birthday) = %s 
                AND EXTRACT(DAY FROM birthday) = %s
            """, (now.month, now.day))
            return cur.fetchall()

    def add_birthday(self, user_id: int, username: str, birthday: datetime, dm_preference: bool = False):
        with self.conn.cursor() as cur:
            cur.execute("""
                INSERT INTO birthdays (user_id, username, birthday, dm_preference)
                VALUES (%s, %s, %s, %s)
                ON CONFLICT (user_id) DO UPDATE 
                SET username = EXCLUDED.username, 
                    birthday = EXCLUDED.birthday,
                    dm_preference = EXCLUDED.dm_preference
            """, (user_id, username, birthday, dm_preference))
            self.conn.commit()

    def update_dm_preference(self, user_id: int, dm_preference: bool):
        with self.conn.cursor() as cur:
            cur.execute("""
                INSERT INTO birthdays (user_id, dm_preference)
                VALUES (%s, %s)
                ON CONFLICT (user_id) DO UPDATE 
                SET dm_preference = EXCLUDED.dm_preference
            """, (user_id, dm_preference))
            self.conn.commit()

    def get_users_with_dm_enabled(self):
        with self.conn.cursor() as cur:
            cur.execute("""
                SELECT user_id, username, birthday
                FROM birthdays
                WHERE dm_preference = TRUE
            """)
            return cur.fetchall()

    def get_next_birthday(self):
        tz = pytz.timezone('Europe/Berlin')
        now = datetime.now(tz)
        
        with self.conn.cursor() as cur:
            cur.execute("""
                SELECT user_id, username, birthday
                FROM birthdays
                WHERE (EXTRACT(MONTH FROM birthday), EXTRACT(DAY FROM birthday)) >= 
                      (%s, %s)
                ORDER BY EXTRACT(MONTH FROM birthday), EXTRACT(DAY FROM birthday)
                LIMIT 1
            """, (now.month, now.day))
            return cur.fetchone()

    def search_birthday_by_username(self, search_term: str):
        with self.conn.cursor() as cur:
            cur.execute("""
                SELECT user_id, username, birthday
                FROM birthdays
                WHERE LOWER(username) LIKE LOWER(%s)
                ORDER BY username
            """, (f'%{search_term}%',))
            return cur.fetchall()

    def get_upcoming_birthdays(self, limit=5):
        tz = pytz.timezone('Europe/Berlin')
        now = datetime.now(tz)
        
        with self.conn.cursor() as cur:
            cur.execute("""
                WITH next_birthday AS (
                    SELECT 
                        user_id,
                        username,
                        birthday,
                        CASE 
                            WHEN (DATE_PART('month', birthday), DATE_PART('day', birthday)) >= 
                                 (DATE_PART('month', CURRENT_DATE), DATE_PART('day', CURRENT_DATE))
                            THEN DATE(MAKE_DATE(DATE_PART('year', CURRENT_DATE)::INTEGER, 
                                              DATE_PART('month', birthday)::INTEGER, 
                                              DATE_PART('day', birthday)::INTEGER))
                            ELSE DATE(MAKE_DATE(DATE_PART('year', CURRENT_DATE)::INTEGER + 1, 
                                              DATE_PART('month', birthday)::INTEGER, 
                                              DATE_PART('day', birthday)::INTEGER))
                        END as next_occurrence
                    FROM birthdays
                )
                SELECT 
                    user_id,
                    username,
                    birthday,
                    (next_occurrence - CURRENT_DATE) as days_until
                FROM next_birthday
                ORDER BY days_until ASC
                LIMIT %s
            """, (limit,))
            return cur.fetchall()

    def get_dm_preference(self, user_id: int) -> bool:
        with self.conn.cursor() as cur:
            cur.execute("""
                SELECT dm_preference
                FROM birthdays
                WHERE user_id = %s
            """, (user_id,))
            result = cur.fetchone()
            return result[0] if result else False