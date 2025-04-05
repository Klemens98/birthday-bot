import psycopg2
import yaml
from datetime import datetime
import pytz
import logging

logger = logging.getLogger('DatabaseService')

def load_config():
    logger.debug("Loading configuration from config.yaml")
    try:
        with open('config.yaml', 'r') as file:
            config = yaml.safe_load(file)
            logger.debug("Configuration loaded successfully")
            return config
    except Exception as e:
        logger.error(f"Failed to load configuration: {e}")
        raise

class DatabaseService:
    def __init__(self):
        logger.info("Initializing DatabaseService")
        try:
            config = load_config()
            db_config = config['DATABASE']
            self.conn = psycopg2.connect(
                dbname=db_config['NAME'],
                user=db_config['USER'],
                password='********',  # Password hidden in logs
                host=db_config['HOST'],
                port=db_config['PORT']
            )
            logger.info(f"Connected to database {db_config['NAME']} at {db_config['HOST']}")
        except Exception as e:
            logger.error(f"Failed to connect to database: {e}")
            raise

    def get_todays_birthdays(self):
        tz = pytz.timezone('Europe/Berlin')
        now = datetime.now(tz)
        logger.info(f"Fetching birthdays for today ({now.strftime('%d.%m.%Y')})")
        
        try:
            with self.conn.cursor() as cur:
                cur.execute("""
                    SELECT user_id, username, firstname, lastname, birthday, dm_preference 
                    FROM birthdays 
                    WHERE EXTRACT(MONTH FROM birthday) = %s 
                    AND EXTRACT(DAY FROM birthday) = %s
                """, (now.month, now.day))
                results = cur.fetchall()
                logger.info(f"Found {len(results)} birthdays for today")
                logger.debug(f"Birthday results: {results}")
                return results
        except Exception as e:
            logger.error(f"Error fetching today's birthdays: {e}")
            raise

    def add_birthday(self, user_id: int, username: str, birthday: datetime, firstname: str = None, lastname: str = None, dm_preference: bool = False):
        logger.info(f"Adding/updating birthday for user {username} (ID: {user_id})")
        logger.debug(f"Details - Birthday: {birthday}, Firstname: {firstname}, Lastname: {lastname}, DM Preference: {dm_preference}")
        
        try:
            with self.conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO birthdays (user_id, username, firstname, lastname, birthday, dm_preference)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    ON CONFLICT (user_id) DO UPDATE 
                    SET username = EXCLUDED.username,
                        firstname = EXCLUDED.firstname,
                        lastname = EXCLUDED.lastname,
                        birthday = EXCLUDED.birthday,
                        dm_preference = EXCLUDED.dm_preference
                """, (user_id, username, firstname, lastname, birthday, dm_preference))
                self.conn.commit()
                logger.info(f"Successfully saved birthday data for user {username}")
        except Exception as e:
            logger.error(f"Error saving birthday for user {username}: {e}")
            self.conn.rollback()
            raise

    def update_dm_preference(self, user_id: int, dm_preference: bool):
        logger.info(f"Updating DM preference for user {user_id} to {dm_preference}")
        
        try:
            with self.conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO birthdays (user_id, dm_preference)
                    VALUES (%s, %s)
                    ON CONFLICT (user_id) DO UPDATE 
                    SET dm_preference = EXCLUDED.dm_preference
                """, (user_id, dm_preference))
                self.conn.commit()
                logger.info(f"Successfully updated DM preference for user {user_id}")
        except Exception as e:
            logger.error(f"Error updating DM preference for user {user_id}: {e}")
            self.conn.rollback()
            raise

    def get_users_with_dm_enabled(self):
        logger.info("Fetching users with DM notifications enabled")
        
        try:
            with self.conn.cursor() as cur:
                cur.execute("""
                    SELECT user_id, username, firstname, lastname, birthday
                    FROM birthdays
                    WHERE dm_preference = TRUE
                """)
                results = cur.fetchall()
                logger.info(f"Found {len(results)} users with DM notifications enabled")
                logger.debug(f"DM enabled users: {results}")
                return results
        except Exception as e:
            logger.error(f"Error fetching users with DM enabled: {e}")
            raise

    def get_next_birthday(self):
        tz = pytz.timezone('Europe/Berlin')
        now = datetime.now(tz)
        logger.info("Fetching next upcoming birthday")
        
        try:
            with self.conn.cursor() as cur:
                cur.execute("""
                    SELECT user_id, username, firstname, lastname, birthday
                    FROM birthdays
                    WHERE (EXTRACT(MONTH FROM birthday), EXTRACT(DAY FROM birthday)) >= 
                          (%s, %s)
                    ORDER BY EXTRACT(MONTH FROM birthday), EXTRACT(DAY FROM birthday)
                    LIMIT 1
                """, (now.month, now.day))
                result = cur.fetchone()
                if result:
                    logger.info(f"Next birthday found: {result[1]} on {result[4]}")
                else:
                    logger.info("No upcoming birthdays found")
                return result
        except Exception as e:
            logger.error(f"Error fetching next birthday: {e}")
            raise

    def search_birthday_by_username(self, search_term: str):
        logger.info(f"Searching birthdays for username containing: {search_term}")
        
        try:
            with self.conn.cursor() as cur:
                cur.execute("""
                    SELECT user_id, username, firstname, lastname, birthday
                    FROM birthdays
                    WHERE LOWER(username) LIKE LOWER(%s)
                    ORDER BY username
                """, (f'%{search_term}%',))
                results = cur.fetchall()
                logger.info(f"Found {len(results)} matches for search term '{search_term}'")
                logger.debug(f"Search results: {results}")
                return results
        except Exception as e:
            logger.error(f"Error searching birthdays by username: {e}")
            raise

    def get_upcoming_birthdays(self, limit=5):
        logger.info(f"Fetching next {limit} upcoming birthdays")
        
        try:
            with self.conn.cursor() as cur:
                cur.execute("""
                    WITH next_birthday AS (
                        SELECT 
                            user_id,
                            username,
                            firstname,
                            lastname,
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
                        firstname,
                        lastname,
                        birthday,
                        (next_occurrence - CURRENT_DATE) as days_until
                    FROM next_birthday
                    ORDER BY days_until ASC
                    LIMIT %s
                """, (limit,))
                results = cur.fetchall()
                logger.info(f"Found {len(results)} upcoming birthdays")
                logger.debug(f"Upcoming birthdays: {results}")
                return results
        except Exception as e:
            logger.error(f"Error fetching upcoming birthdays: {e}")
            raise

    def get_dm_preference(self, user_id: int) -> bool:
        logger.info(f"Fetching DM preference for user {user_id}")
        
        try:
            with self.conn.cursor() as cur:
                cur.execute("""
                    SELECT dm_preference
                    FROM birthdays
                    WHERE user_id = %s
                """, (user_id,))
                result = cur.fetchone()
                preference = result[0] if result else False
                logger.info(f"DM preference for user {user_id}: {preference}")
                return preference
        except Exception as e:
            logger.error(f"Error fetching DM preference for user {user_id}: {e}")
            raise