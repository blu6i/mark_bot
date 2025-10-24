from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage
import dotenv, os

dotenv.load_dotenv()

bot = Bot(
        token=os.getenv("BOT_TOKEN"),
        default=DefaultBotProperties(parse_mode=ParseMode.HTML)
    )
dp = Dispatcher(storage=MemoryStorage())