from aiogram import Router, F
from aiogram.filters import Command, or_f, StateFilter
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from bots.tg_bot.handlers.keyboards import construct_keyboards
from bots.tg_bot.config_bot import bot
from bots.tg_bot.handlers.filters import IsTeacher, CorrectWordCommand

from core.enums import StatusLoadExcel, StatusValidCountStudent
from core.logic.teachers.print_excel_mark import get_date_marks, get_name_lessons_marks, \
    load_msg_excel, get_keyboard_option, validate_count_students, delete_random_instance_student, \
    start_delete_random_student, get_info_delete_student

print_excel_marks_router = Router()


class PrintExcelMarks(StatesGroup):
    choice_date_marks = State()
    choice_name_lessons = State()
    choice_groups = State()
    choice_option = State()

    delete_random_student = State()
    confirm_rerun_delete = State()
    insert_count_student = State()
    confirm_delete = State()


@print_excel_marks_router.message(or_f(Command("excel"), F.text),
                                  CorrectWordCommand(['мои отметки', '/excel']),
                                  IsTeacher())
async def choice_date_marks(message: Message, state: FSMContext):
    await state.clear()
    await state.set_state(PrintExcelMarks.choice_date_marks)
    status, text, keyboards_data = await get_date_marks(message.from_user.id)
    if status == StatusLoadExcel.OK:
        keyboards = construct_keyboards(keyboards_data)
        await message.answer(text, reply_markup=keyboards)
    else:
        await message.answer(text)
        await state.clear()


@print_excel_marks_router.callback_query(F.data.startswith('back'),
                                         PrintExcelMarks.choice_name_lessons,
                                         IsTeacher())
async def choice_date_marks(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await state.set_state(PrintExcelMarks.choice_date_marks)
    status, text, keyboards_data = await get_date_marks(callback.from_user.id)
    if status == StatusLoadExcel.OK:
        keyboards = construct_keyboards(keyboards_data)
        await callback.message.edit_text(text, reply_markup=keyboards)
    else:
        await callback.message.edit_text(text)
        await state.clear()


@print_excel_marks_router.callback_query(F.data.startswith('date_') | F.data.startswith('back'),
                                         StateFilter(
                                             PrintExcelMarks.choice_date_marks,
                                             PrintExcelMarks.choice_option
                                         ))
async def choice_name_lessons(callback: CallbackQuery, state: FSMContext):
    await state.set_state(PrintExcelMarks.choice_name_lessons)
    if callback.data == 'back':
        data = await state.get_data()
        date = data.get('date')
    else:
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


@print_excel_marks_router.callback_query(F.data.startswith('subject_') | F.data.startswith('back'),
                                         StateFilter(PrintExcelMarks.choice_name_lessons,
                                                     PrintExcelMarks.delete_random_student,
                                                     PrintExcelMarks.confirm_rerun_delete))
async def choice_option(callback: CallbackQuery, state: FSMContext):
    """
    Вывод опций для выбранного предмета
    :param callback:
    :param state:
    :return:
    """
    if callback.data != 'back':
        instance_id = callback.data.removeprefix('subject_')
        await state.update_data(instance_id=instance_id)
    text, keyboard_data = get_keyboard_option()
    keyboards = construct_keyboards(keyboard_data)
    await callback.message.edit_text(text=text, reply_markup=keyboards)
    await state.set_state(PrintExcelMarks.choice_option)


@print_excel_marks_router.callback_query(F.data.startswith('remove_random_student'),
                                         PrintExcelMarks.choice_option)
async def delete_random_student(callback: CallbackQuery, state: FSMContext):
    """
    Обработка для кнопки со случайным удалением
    Также идет проверка была ли уже запущена случайное удаление
    :param callback:
    :param state:
    :return:
    """
    data = await state.get_data()
    instance_id = int(data.get('instance_id'))
    text, keyboards_data, status = await start_delete_random_student(instance_id)
    keyboards = construct_keyboards(keyboards_data)
    await callback.message.edit_text(text=text, reply_markup=keyboards)
    if status == StatusLoadExcel.HAVE_DELETE:
        await state.set_state(PrintExcelMarks.confirm_rerun_delete)
    else:
        await state.set_state(PrintExcelMarks.delete_random_student)


@print_excel_marks_router.callback_query(F.data.startswith('confirm_rerun_delete'),
                                         PrintExcelMarks.confirm_rerun_delete)
async def delete_rerun_student(callback: CallbackQuery, state: FSMContext):
    """
    На случай, если уже было случайное удаление
    :param callback:
    :param state:
    :return:
    """
    data = await state.get_data()
    instance_id = int(data.get('instance_id'))
    text, keyboards_data = await get_info_delete_student(instance_id)
    keyboards = construct_keyboards(keyboards_data)
    await callback.message.edit_text(text=text, reply_markup=keyboards)
    await state.set_state(PrintExcelMarks.delete_random_student)


@print_excel_marks_router.message(F.text,
                                  PrintExcelMarks.delete_random_student)
async def insert_count_student(message: Message, state: FSMContext):
    """
    Ввод количество студентов на паре
    :param message:
    :param state:
    :return:
    """
    # TODO: убрать валидатор для цифр в validate_count_students
    data = await state.get_data()
    instance_id = int(data.get('instance_id'))
    text = message.text
    if not text.isdigit():
        text = "Введите неотрицательное целое число."
        keyboards_data = {
            "type": "inline",
            "buttons": [{
                'text': 'Назад',
                'callback_data': 'back'
            }]
        }
        keyboards = construct_keyboards(keyboards_data)
        await message.answer(text=text, reply_markup=keyboards)
        return
    count_student = int(text)
    status, extra_marks, text, keyboards_data = await validate_count_students(count_student, instance_id)
    if status == StatusValidCountStudent.OK:
        await state.update_data(extra_marks=extra_marks)
        keyboards = construct_keyboards(keyboards_data)
        await message.answer(text, reply_markup=keyboards)
        await state.set_state(PrintExcelMarks.insert_count_student)
    else:
        keyboards = construct_keyboards(keyboards_data)
        await message.answer(text, reply_markup=keyboards)


@print_excel_marks_router.callback_query(F.data.startswith('confirm_delete'),
                                         PrintExcelMarks.insert_count_student,
                                         IsTeacher())
async def confirm_delete(callback: CallbackQuery, state: FSMContext):
    """
    Подтверждение удаление
    :param callback:
    :param state:
    :return:
    """
    data = await state.get_data()
    instance_id = int(data.get('instance_id'))
    extra_marks = int(data.get('extra_marks'))
    text = await delete_random_instance_student(instance_id, extra_marks)
    await callback.message.edit_text(text=text)


@print_excel_marks_router.callback_query(F.data.startswith('get_student_list'),
                                         PrintExcelMarks.choice_option,
                                         IsTeacher())
async def print_excel_marks(callback: CallbackQuery, state: FSMContext):
    """
    Вывод списков отметок. Выводит всех студентов, в доп. столбце выводит +, если была отметка
    :param callback:
    :param state:
    :return:
    """
    # TODO: вывести сколько людей отметилось на паре
    # TODO: сделать вывод inline кнопки с предложением вывести студентов
    #  прямо в телеграм
    data = await state.get_data()
    date = data.get("date")
    instance_id = data.get('instance_id')
    user_tg_id = callback.from_user.id
    await load_msg_excel(int(instance_id), date, user_tg_id, send_document_msg)