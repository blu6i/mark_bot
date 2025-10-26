from aiogram import Router, F
from aiogram.filters import or_f, Command, StateFilter
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State

from bots.tg_bot.handlers.filters import CorrectWordCommand, IsAdmin, BlackListWord, IsNotCommand
from bots.tg_bot.handlers.keyboards import construct_keyboards

from core.enums import StatusInviteLink
from core.logic.admins.create_invite_link import create_invite_link_teacher, create_invite_link
from core.validators.validator_string import is_valid_fullname

generate_invite_link_router = Router()


class GenerateInviteLink(StatesGroup):
    read_fullname_teacher_state = State()
    generate_invite_link_state = State()


@generate_invite_link_router.message(or_f(Command("invite_teacher"), F.text),
                                    CorrectWordCommand(['пригласить преподавателя', '/invite_teacher']),
                                    IsAdmin())
async def invite_teacher(message: Message, state: FSMContext):
    await state.clear()
    await state.set_state(GenerateInviteLink.read_fullname_teacher_state)
    text = ("Введите ФИО преподавателя для приглашения.\n"
            "Например: Иванов Иван Иванович")
    await message.answer(text)


@generate_invite_link_router.message(F.text,
                                     BlackListWord(),
                                     IsNotCommand(),
                                     StateFilter(GenerateInviteLink.read_fullname_teacher_state,
                                                 GenerateInviteLink.generate_invite_link_state))
async def read_fullname_teacher(message: Message, state: FSMContext):
    await state.set_state(GenerateInviteLink.generate_invite_link_state)
    read_text = message.text
    if not is_valid_fullname(read_text):
        text = """
        Некорректный формат ввода.\n
        Введите данные корректно (Фамилия Имя Отчество).\n
        Например: Иванов Иван Иванович
        """
        await message.answer(text)
        return
    else:
        status, text, keyboards_data = await create_invite_link_teacher(read_text)
        if status == StatusInviteLink.ALREADY_TG:
            keyboards = construct_keyboards(keyboards_data)
            await message.answer(text, reply_markup=keyboards)
        else:
            await message.answer(text)
            await state.clear()


@generate_invite_link_router.callback_query(F.data.startswith("yes_rebind_"),
                                     GenerateInviteLink.generate_invite_link_state)
async def yes_rebind_teacher(callback: CallbackQuery, state: FSMContext):
    teacher_id = callback.data.removeprefix("yes_rebind_")
    invite_link = create_invite_link(int(teacher_id))
    text = (f"Ссылка для приглашения:\n"
            f"{invite_link}\n"
            f"\n"
            f"Активна в течении 5 минут")
    await callback.message.edit_text(text)
    await state.clear()


@generate_invite_link_router.callback_query(F.data.startswith("no_rebind"),
                                     GenerateInviteLink.generate_invite_link_state)
async def no_rebind_teacher(callback: CallbackQuery, state: FSMContext):
    await callback.message.edit_text("Отмена")
    await state.clear()

