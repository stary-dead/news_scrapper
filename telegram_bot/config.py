"""Bot configuration"""
import os
from dataclasses import dataclass
from dotenv import load_dotenv
from typing import Optional

# Load environment variables from .env file if it exists
env_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), '.env')
if os.path.exists(env_path):
    load_dotenv(env_path)

@dataclass
class BotConfig:
    """Bot configuration"""
    token: str = os.getenv("BOT_TOKEN", "")
    channel_id: int = int(os.getenv("TELEGRAM_CHANNEL_ID", "0"))
    rabbitmq_host: str = os.getenv("RABBITMQ_HOST", "localhost")
    
    def __post_init__(self):
        if not self.token:
            raise ValueError("Bot token not found. Please set BOT_TOKEN in environment variables or .env file")
        if not self.channel_id:
            raise ValueError("Channel ID not found. Please set TELEGRAM_CHANNEL_ID in environment variables or .env file")
