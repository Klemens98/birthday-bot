"""Database service module for managing PostgreSQL database operations."""
import logging
from datetime import datetime
from typing import Optional
import psycopg2
from psycopg2.extras import DictCursor
from config.config_manager import ConfigManager

logger = logging.getLogger('BirthdayBot.DatabaseService')

class DatabaseService:
    def __init__(self):
        """Initialize the database service with PostgreSQL connection."""
        self.config = ConfigManager()
        self.table_name = self.config._config.get('DATABASE', {}).get('TABLE_NAME', 'birthdays')
        logger.info(f"Initializing DatabaseService with table: {self.table_name}")
        self._setup_database()

    def _get_connection(self):
        """Create a new database connection.
        
        Returns:
            psycopg2.connection: Database connection
        """
        db_config = self.config._config['DATABASE']
        logger.info(f"Connecting to database: {db_config['NAME']} with table: {self.table_name}")
        return psycopg2.connect(
            dbname=db_config['NAME'],
            user=db_config['USER'],
            password=db_config['PASSWORD'],
            host=db_config['HOST'],
            port=db_config['PORT']
        )

    def _setup_database(self):
        """Set up the database tables if they don't exist."""
        with self._get_connection() as conn:
            with conn.cursor() as cur:
                # Create birthdays table if it doesn't exist
                cur.execute(f"""
                    CREATE TABLE IF NOT EXISTS {self.table_name} (
                        user_id BIGINT PRIMARY KEY,
                        username VARCHAR(255) NOT NULL,
                        birthday DATE,
                        firstname VARCHAR(255),
                        lastname VARCHAR(255),
                        dm_preference BOOLEAN DEFAULT FALSE
                    )
                """)
                logger.info(f"Database table {self.table_name} initialized")

    def get_upcoming_birthdays(self, limit: int = 5):
        """Get upcoming birthdays ordered by date.
        
        Args:
            limit (int): Maximum number of birthdays to return
            
        Returns:
            list: List of tuples (user_id, username, firstname, lastname, birthday, dm_preference)
        """
        with self._get_connection() as conn:
            with conn.cursor() as cur:
                logger.info(f"Querying upcoming {limit} birthdays from table: {self.table_name}")
                cur.execute(f"""
                    WITH birthday_this_year AS (
                        SELECT 
                            user_id, 
                            username, 
                            firstname, 
                            lastname, 
                            birthday,
                            dm_preference,
                            DATE(EXTRACT(YEAR FROM CURRENT_DATE) || '-' || 
                                 LPAD(EXTRACT(MONTH FROM birthday)::text, 2, '0') || '-' || 
                                 LPAD(EXTRACT(DAY FROM birthday)::text, 2, '0')) as this_year_birthday,
                            CASE 
                                WHEN DATE(EXTRACT(YEAR FROM CURRENT_DATE) || '-' || 
                                         LPAD(EXTRACT(MONTH FROM birthday)::text, 2, '0') || '-' || 
                                         LPAD(EXTRACT(DAY FROM birthday)::text, 2, '0')) >= CURRENT_DATE
                                THEN DATE(EXTRACT(YEAR FROM CURRENT_DATE) || '-' || 
                                         LPAD(EXTRACT(MONTH FROM birthday)::text, 2, '0') || '-' || 
                                         LPAD(EXTRACT(DAY FROM birthday)::text, 2, '0'))
                                ELSE DATE((EXTRACT(YEAR FROM CURRENT_DATE) + 1) || '-' || 
                                         LPAD(EXTRACT(MONTH FROM birthday)::text, 2, '0') || '-' || 
                                         LPAD(EXTRACT(DAY FROM birthday)::text, 2, '0'))
                            END as next_birthday
                        FROM {self.table_name} 
                        WHERE birthday IS NOT NULL
                    )
                    SELECT user_id, username, firstname, lastname, birthday, dm_preference
                    FROM birthday_this_year
                    ORDER BY next_birthday ASC
                    LIMIT %s
                """, (limit,))
                results = cur.fetchall()
                logger.info(f"Found {len(results)} upcoming birthdays")
                return results

    def set_birthday(self, user_id: int, username: str, birthday: datetime, 
                    firstname: Optional[str] = None, lastname: Optional[str] = None, 
                    dm_enabled: bool = False):
        """Add or update a birthday entry.
        
        Args:
            user_id (int): Discord user ID
            username (str): Discord username
            birthday (datetime): User's birthday
            firstname (str, optional): User's first name
            lastname (str, optional): User's last name
            dm_enabled (bool, optional): Whether user wants DM notifications
        """
        with self._get_connection() as conn:
            with conn.cursor() as cur:
                logger.info(f"Adding/updating birthday for user {user_id} in table: {self.table_name}")
                cur.execute(f"""
                    INSERT INTO {self.table_name} 
                        (user_id, username, birthday, firstname, lastname, dm_preference)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    ON CONFLICT (user_id) 
                    DO UPDATE SET 
                        username = EXCLUDED.username,
                        birthday = EXCLUDED.birthday,
                        firstname = EXCLUDED.firstname,
                        lastname = EXCLUDED.lastname,
                        dm_preference = EXCLUDED.dm_preference
                """, (user_id, username, birthday.date(), firstname, lastname, dm_enabled))
                logger.info(f"Birthday saved for user {username} (ID: {user_id})")

    def get_todays_birthdays(self):
        """Get all birthdays for today.
        
        Returns:
            list: List of tuples (user_id, username, firstname, lastname, birthday, dm_preference)
        """
        with self._get_connection() as conn:
            with conn.cursor() as cur:
                logger.info(f"Querying today's birthdays from table: {self.table_name}")
                cur.execute(f"""
                    SELECT user_id, username, firstname, lastname, birthday, dm_preference 
                    FROM {self.table_name} 
                    WHERE EXTRACT(MONTH FROM birthday) = EXTRACT(MONTH FROM CURRENT_DATE)
                    AND EXTRACT(DAY FROM birthday) = EXTRACT(DAY FROM CURRENT_DATE)
                    AND birthday IS NOT NULL
                """)
                results = cur.fetchall()
                logger.info(f"Found {len(results)} birthdays for today")
                return results

    def get_users_with_dm_enabled(self):
        """Get all users who have DM notifications enabled.
        
        Returns:
            list: List of tuples (user_id,)
        """
        with self._get_connection() as conn:
            with conn.cursor() as cur:
                logger.info(f"Querying users with DM enabled from table: {self.table_name}")
                cur.execute(f"SELECT user_id FROM {self.table_name} WHERE dm_preference = TRUE")
                results = cur.fetchall()
                logger.info(f"Found {len(results)} users with DM enabled")
                return results

    def update_dm_preference(self, user_id: int, enabled: bool):
        """Update DM notification preference for a user.
        
        Args:
            user_id (int): Discord user ID
            enabled (bool): Whether to enable DM notifications
        """
        with self._get_connection() as conn:
            with conn.cursor() as cur:
                logger.info(f"Updating DM preference for user {user_id} in table: {self.table_name}")
                cur.execute(f"""
                    UPDATE {self.table_name} 
                    SET dm_preference = %s 
                    WHERE user_id = %s
                """, (enabled, user_id))
                logger.info(f"Updated DM preference for user {user_id} to {enabled}")

    def update_username(self, user_id: int, username: str):
        """Update only the username for a user.
        
        Args:
            user_id (int): Discord user ID
            username (str): New username
        """
        with self._get_connection() as conn:
            with conn.cursor() as cur:
                logger.info(f"Updating username for user {user_id} in table: {self.table_name}")
                cur.execute(f"""
                    UPDATE {self.table_name} 
                    SET username = %s 
                    WHERE user_id = %s
                """, (username, user_id))
                logger.info(f"Updated username for user {user_id} to {username}")

    def get_all_users(self):
        """Get all users from the database for fuzzy matching.
        
        Returns:
            list: List of tuples (user_id, username, firstname, lastname)
        """
        with self._get_connection() as conn:
            with conn.cursor() as cur:
                logger.info(f"Querying all users from table: {self.table_name}")
                cur.execute(f"""
                    SELECT user_id, username, firstname, lastname 
                    FROM {self.table_name}
                    ORDER BY username
                """)
                results = cur.fetchall()
                logger.info(f"Found {len(results)} users in database")
                return results