"""Bot configuration"""
import os
from dataclasses import dataclass
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

@dataclass
class BotConfig:
    """Bot configuration"""
    token: str = os.getenv("BOT_TOKEN")
    
    def __post_init__(self):
        if not self.token:
            raise ValueError("Bot token not found. Please set BOT_TOKEN in .env file")
