from aiogram import Router, F
from aiogram.filters import Command, or_f
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from bots.tg_bot.handlers.keyboards import construct_keyboards
from bots.tg_bot.config_bot import bot

from core.enums import StatusLoadExcel
from core.logic.teachers.print_excel_mark import get_date_marks, get_name_lessons_marks, get_student_marks, \
    load_msg_excel

print_excel_marks_router = Router()


class PrintExcelMarks(StatesGroup):
    choice_date_marks = State()
    choice_name_lessons = State()
    choice_groups = State()


@print_excel_marks_router.message(or_f(Command("excel"), F.text))
async def choice_date_marks(message: Message, state: FSMContext):
    print('aaa')
    await state.set_state(PrintExcelMarks.choice_date_marks)
    status, text, keyboards_data = await get_date_marks(message.from_user.id)
    if status == StatusLoadExcel.OK:
        keyboards = construct_keyboards(keyboards_data)
        await message.answer(text, reply_markup=keyboards)
    else:
        await message.answer(text)
        await state.clear()


@print_excel_marks_router.callback_query(F.data.startswith('date_'),
                                         PrintExcelMarks.choice_date_marks)
async def choice_name_lessons(callback: CallbackQuery, state: FSMContext):
    await state.set_state(PrintExcelMarks.choice_name_lessons)
    date = callback.data.removeprefix('date_')
    await state.update_data(date=date)
    status, text, keyboards_data = await get_name_lessons_marks(callback.from_user.id, date)
    if status == StatusLoadExcel.OK:
        keyboards = construct_keyboards(keyboards_data)
        await callback.message.edit_text(text, reply_markup=keyboards)
    else:
        await callback.message.edit_text(text)


async def send_document_msg(chat_id: int, document: str):
    await bot.send_document(chat_id=chat_id, document=document)

@print_excel_marks_router.callback_query(F.data.startswith('subject_'),
                                         PrintExcelMarks.choice_name_lessons)
async def print_excel_marks(callback: CallbackQuery, state: FSMContext):
    # TODO: вывести сколько людей отметилось на паре
    # TODO: сделать вывод inline кнопки с предложением вывести студентов
    #  прямо в телеграм
    data = await state.get_data()
    date = data.get("date")
    subject_id = callback.data.removeprefix('subject_')
    marks_data = await get_student_marks(int(subject_id))
    user_tg_id = callback.from_user.id
    await load_msg_excel(int(subject_id), date, user_tg_id, marks_data, send_document_msg)