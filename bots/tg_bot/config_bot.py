import dotenv
import os
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.redis import RedisStorage
from redis.asyncio import Redis

dotenv.load_dotenv()

redis_client = Redis(
    host=os.getenv("RD_HOST"),
    port=int(os.getenv("RD_PORT")),
    password=os.getenv("RD_PASSWORD"),
    decode_responses=True
)

bot = Bot(
        token=os.getenv("BOT_TOKEN"),
        default=DefaultBotProperties(parse_mode=ParseMode.HTML)
    )

STATE_TTL = os.getenv("RD_LIFE_STATE", 3600)
DATA_TTL = os.getenv("RD_LIFE_DATA", 3600)

dp = Dispatcher(storage=RedisStorage(redis=redis_client, state_ttl=STATE_TTL, data_ttl=DATA_TTL))