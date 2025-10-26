from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

from bots.tg_bot.handlers.filters import IsAdmin

from core.logic.parser import pdf_parser

parser_router = Router()

@parser_router.message(Command('start_parser'),
                       IsAdmin())
async def start_parser(msg: Message):
    await msg.answer('Запуск парсер')
    await pdf_parser.start_parse()
    await msg.answer('Парсинг завершен')