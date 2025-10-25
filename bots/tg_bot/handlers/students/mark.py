from aiogram import Router, F
from aiogram.filters import or_f, Command
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from core.logic.students import mark
from core.enums import StatusMarkStudent

from bots.tg_bot.handlers.keyboards import construct_keyboards

mark_students_router = Router()

class MarkStudents(StatesGroup):
    mark_students_state = State()

@mark_students_router.message(or_f(Command("mark"), F.text))
async def mark_students(message: Message, state: FSMContext):
    await state.clear()
    await state.set_state(MarkStudents.mark_students_state)
    user_tg_id = message.from_user.id
    status, text, keyboards_data = await mark.mark_student(user_tg_id)
    if status == StatusMarkStudent.MORE_MARK:
        keyboards = construct_keyboards(keyboards_data)
        await message.answer(text, reply_markup=keyboards)
    else:
        await message.answer(text)
        await state.clear()


@mark_students_router.callback_query(F.data.startswith('lesson_'),
MarkStudents.mark_students_state)
async def mark_students_callback(callback: CallbackQuery, state: FSMContext):
    instance_id = int(callback.data.removeprefix('lesson_'))
    user_tg_id = callback.from_user.id
    status, text, _ = await mark.mark_student(user_tg_id, instance_id)
    await callback.message.edit_text(text)
    await state.clear()