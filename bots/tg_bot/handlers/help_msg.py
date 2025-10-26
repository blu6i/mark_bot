from os import getenv
from dotenv import load_dotenv

from aiogram import Router, F
from aiogram.filters import or_f, Command

from bots.tg_bot.handlers.filters import CorrectWordCommand
from core.enums import StatusNewUser

from core.logic.auth_user import check_auth_user

load_dotenv()
ADMINS = list(map(int, (getenv("ADMINS").split(","))))


help_msg_router = Router()


@help_msg_router.message(or_f(Command("help"), F.text),
                         CorrectWordCommand(['/help', 'помощь']))
async def help_msg(message):
    status, text = await check_auth_user(message.from_user.id)
    user_tg_id = message.from_user.id
    if status == StatusNewUser.NEW_USER:
        text = ("Доброго времени суток, я бот для автоматизации отметки на парах.\n"
                "Чтобы я мог с тобой взаимодействовать, нужно зарегистрироваться.\n"
                "Для этого нужно ввести /start и следовать инструкции.")
    elif status == StatusNewUser.OLD_USER_TEACHER:
        text = ("Краткая справка для взаимодействия с ботом:\n"
                "/start_mark или \"запустить отметку\" - запускает отметку на паре. Отметка может сгенерироваться "
                "автоматически или, при неизвестной проблеме, вам придется создать ее самостоятельно.\n"
                "\n"
                "/excel или \"список отметившихся\" - получаете таблицу excel со списком студентов, который посещали "
                "выбранную пару.\n")
    elif status == StatusNewUser.OLD_USER_STUDENT:
        text = ("Краткая справка для взаимодействия с ботом:\n"
                "/mark или \"Отметиться\" - запустить процесс отметки на паре.\n")

    if user_tg_id in ADMINS:
        text += ("\n"
                 "/invite_teacher или \"Пригласить преподавателя\" - запустить процесс генерации пригласительной ссылки "
                 "для преподавателя\n"
                 "\n"
                 "/start_parser - запустить парсинг расписания (!!!Весь бот замораживается во время парсинга!!!)")
    await message.answer(text)
