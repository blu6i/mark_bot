from aiogram import Router, F
from aiogram.filters import Command, CommandObject
from aiogram.types import Message
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State

from core.enums import StatusNewUser, StatusRegisterStudent
from core.logic.auth_user import auth_teacher, check_auth_user, auth_student
from core.logic.keyboards_data import get_keyboard_commands

from bots.tg_bot.handlers.keyboards import construct_keyboards

started_router = Router()


class AuthUser(StatesGroup):
    """
    Состояния для авторизации пользователя
    """
    waiting_fullname = State()


@started_router.message(Command('start'))
async def cmd_start(message: Message, state: FSMContext, command: CommandObject):
    """
    Обработка команды start (запуск бота)
    """
    await state.clear()
    user_tg_id = message.from_user.id

    if command.args:
        key = command.args
        status, text = await auth_teacher(key, user_tg_id)
    else:
        status, text = await check_auth_user(user_tg_id)
        if status == StatusNewUser.NEW_USER:
            await state.set_state(AuthUser.waiting_fullname)
    keyboards_data = await get_keyboard_commands(user_tg_id)
    keyboards = construct_keyboards(keyboards_data)
    await message.answer(text=text,
                         reply_markup=keyboards)


@started_router.message(Command('kb'))
async def cmd_kb(message: Message):
    """
    Создание reply клавиатуры
    """
    user_tg_id = message.from_user.id
    text = "⌨"
    keyboards_data = await get_keyboard_commands(user_tg_id)
    keyboards = construct_keyboards(keyboards_data)
    await message.answer(text=text,
                         reply_markup=keyboards)

@started_router.message(F.text,
                        AuthUser.waiting_fullname)
async def process_fullname(message: Message, state: FSMContext):
    """
    Обработка ввода ФИО
    """
    user_tg_id = message.from_user.id
    text = message.text
    status, text = await auth_student(user_tg_id, text)
    await message.answer(text=text)
    if status == StatusRegisterStudent.OK:
        await state.clear()
