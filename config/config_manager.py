"""Configuration management module for the Birthday Bot."""
import yaml
import logging
from typing import Dict, Any

logger = logging.getLogger('BirthdayBot.ConfigManager')

class ConfigManager:
    def __init__(self, config_path: str = 'config/config.yaml'):
        """Initialize the configuration manager.
        
        Args:
            config_path (str): Path to the YAML configuration file
        """
        self.config_path = config_path
        self._config = self._load_config()

    def _load_config(self) -> Dict[str, Any]:
        """Load configuration from YAML file.
        
        Returns:
            dict: Configuration dictionary
            
        Raises:
            FileNotFoundError: If config file doesn't exist
            yaml.YAMLError: If config file is invalid
        """
        try:
            with open(self.config_path, 'r') as file:
                config = yaml.safe_load(file)
                logger.info("Configuration loaded successfully")
                return config
        except FileNotFoundError:
            logger.error(f"Configuration file not found: {self.config_path}")
            raise
        except yaml.YAMLError as e:
            logger.error(f"Error parsing configuration file: {e}")
            raise

    @property
    def discord_token(self) -> str:
        """Get Discord bot token.
        
        Returns:
            str: Discord bot token
        """
        return self._config['DISCORD']['TOKEN']

    @property
    def application_id(self) -> int:
        """Get Discord application ID.
        
        Returns:
            int: Discord application ID
        """
        return int(self._config['DISCORD']['APPLICATION_ID'])

    @property
    def channel_id(self) -> int:
        """Get Discord channel ID for birthday announcements.
        
        Returns:
            int: Discord channel ID
        """
        return int(self._config['DISCORD']['CHANNEL_ID'])

    @property
    def guild_id(self) -> int:
        """Get Discord guild ID for command syncing.
        
        Returns:
            int: Discord guild ID
        """
        return int(self._config['DISCORD']['GUILD_ID'])

    @property
    def timezone(self) -> str:
        """Get timezone for birthday checks.
        
        Returns:
            str: Timezone string (default: 'Europe/Berlin')
        """
        return self._config.get('TIMEZONE', 'Europe/Berlin')