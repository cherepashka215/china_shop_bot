from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
import os
from dotenv import dotenv_values
from datetime import datetime

config = {
    **dotenv_values(".env"),
    **os.environ,
}


class SDBot:
    token: str = config.get('BOT_TOKEN')

    def __init__(self):
        storage = MemoryStorage()
        self.bot = Bot(token=self.token)
        self.dispatcher = Dispatcher(bot=self.bot, storage=storage)
        self.dispatcher["started_at"] = datetime.now().strftime("%Y-%m-%d %H:%M")


sd_bot = SDBot()
