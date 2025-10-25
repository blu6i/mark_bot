from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from core.enums import StatusRunMark, StatusValidCountStudent
from core.logic.teachers import started_mark
from core.logic.students import mark
from core.validators.validate_mark import validate_count_students

from bots.tg_bot.handlers.keyboards import construct_keyboards
from bots.tg_bot.config_bot import bot

start_mark_router = Router()


class StartMarkState(StatesGroup):
    prestart_mark_state = State()
    choice_type_lessons_state = State()
    choice_name_lessons_state = State()
    choice_groups_state = State()
    confirm_custom_mark = State()

    delete_random_student_state = State()
    insert_count_student_state = State()


@start_mark_router.message(Command("start_mark"))
async def prestart_mark(message: Message, state: FSMContext):
    # TODO: в prestart сделать обработку ошибку при автоматической паре, чтобы
    #  возвращала клавиатуру и текст, чтобы препод сам создавать пару
    await state.clear()
    user_tg_id = message.from_user.id
    status, text, keyboards_data, mark_data = await started_mark.prestart_mark(user_tg_id)
    await state.set_state(StartMarkState.prestart_mark_state)
    if status == StatusRunMark.OK:
        await message.answer(text, reply_markup=construct_keyboards(keyboards_data))
        await state.update_data(mark_data=mark_data)
    elif status == StatusRunMark.NO_PAIR_TEACHER:
        await message.answer(text, reply_markup=construct_keyboards(keyboards_data))
    elif status == StatusRunMark.IS_NO_TEACHER:
        await message.answer(text)
    else:
        await message.answer(text="Неизвестная ошибка")


async def message_mark_info(chat_id: int, text: str, keyboards_data: dict):
    await bot.send_message(chat_id=chat_id, text=text, reply_markup=construct_keyboards(keyboards_data))


@start_mark_router.callback_query(F.data == "start_mark",
                                  StartMarkState.prestart_mark_state)
async def start_mark(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    mark_data = data.get("mark_data")
    if not mark_data:
        await callback.answer("Неизвестная ошибка.")
        return
    await started_mark.started_mark(mark_data, callback.from_user.id, message_mark_info)
    text = ("Отметка успешно запущена.\n"
            "Ожидайте подтверждение о завершении.")
    await callback.message.edit_text(text)
    await state.clear()


@start_mark_router.callback_query((F.data == "create_custom_mark") | (F.data == 'back_type_lessons'),
                                  StateFilter(StartMarkState.prestart_mark_state,
                                              StartMarkState.choice_name_lessons_state))
async def choice_type_lessons(callback: CallbackQuery, state: FSMContext):
    user_tg_id = callback.from_user.id
    text, keyboards_data = await started_mark.get_type_lesson(user_tg_id)
    keyboards = construct_keyboards(keyboards_data)
    await callback.message.edit_text(text, reply_markup=keyboards)
    await state.set_state(StartMarkState.choice_type_lessons_state)


@start_mark_router.callback_query(F.data.startswith("type_") | (F.data == "back_name_lessons"),
                                  StateFilter(StartMarkState.choice_type_lessons_state,
                                              StartMarkState.choice_groups_state))
async def choice_name_lessons(callback: CallbackQuery, state: FSMContext):
    if callback.data.startswith("type_"):
        lesson_type = (callback.data.removeprefix('type_')).replace('-', ' ')
        await state.update_data(lesson_type=lesson_type)
    else:
        await state.update_data(set_group=[])
        data = await state.get_data()
        lesson_type = data.get('lesson_type')
    user_tg_id = callback.from_user.id
    text, keyboards_data = await started_mark.get_name_lesson(user_tg_id, lesson_type)
    keyboards = construct_keyboards(keyboards_data)
    await callback.message.edit_text(text, reply_markup=keyboards)
    await state.set_state(StartMarkState.choice_name_lessons_state)


@start_mark_router.callback_query(F.data.startswith("subject_") | F.data.startswith('group_') | (F.data == "back_group"),
                                  StateFilter(StartMarkState.choice_name_lessons_state,
                                              StartMarkState.confirm_custom_mark,
                                              StartMarkState.choice_groups_state))
async def choice_group(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    set_groups = set(data.get('set_group', []))
    lesson_type = data.get('lesson_type')

    if callback.data.startswith("subject_"):
        subject_id = int(callback.data.removeprefix('subject_'))
        await state.update_data(subject_id=subject_id)
    else:
        subject_id = data.get('subject_id')
        if callback.data.startswith('group_'):
            group_id = int(callback.data.removeprefix('group_'))
            if group_id in set_groups:
                set_groups.remove(group_id)
            else:
                set_groups.add(group_id)
            await state.update_data(set_group=list(set_groups))
    user_tg_id = callback.from_user.id
    text, keyboards_data = await started_mark.get_groups_teachers(subject_id, user_tg_id, lesson_type, set_groups)
    keyboards = construct_keyboards(keyboards_data)
    await callback.message.edit_text(text, reply_markup=keyboards)
    await state.set_state(StartMarkState.choice_groups_state)


@start_mark_router.callback_query(F.data.startswith("confirm_choice_group"),
                                  StateFilter(StartMarkState.choice_groups_state))
async def confirm_custom_mark(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    lesson_type = data.get('lesson_type')
    subject_id = data.get('subject_id')
    set_groups = data.get('set_group')
    user_tg_id = callback.from_user.id
    text, keyboards_data = await started_mark.get_custom_mark_info(lesson_type, subject_id, set_groups, user_tg_id)
    keyboards = construct_keyboards(keyboards_data)
    await callback.message.edit_text(text, reply_markup=keyboards)
    await state.set_state(StartMarkState.confirm_custom_mark)


@start_mark_router.callback_query(F.data.startswith("start_custom_mark"),
                                  StateFilter(StartMarkState.confirm_custom_mark))
async def start_custom_mark(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    lesson_type = data.get('lesson_type')
    subject_id = data.get('subject_id')
    set_groups = data.get('set_group')
    user_tg_id = callback.from_user.id
    text = await started_mark.start_custom_mark(lesson_type, subject_id, set_groups, user_tg_id, message_mark_info)
    await callback.message.edit_text(text)
    await state.clear()


@start_mark_router.callback_query(F.data.startswith("delete_random_student"))
async def delete_random_student(callback: CallbackQuery, state: FSMContext):
    await state.set_state(StartMarkState.delete_random_student_state)
    await callback.message.edit_text("Укажите количество студентов на паре.")


@start_mark_router.message(F.text,
                           StateFilter(StartMarkState.delete_random_student_state,
                                       StartMarkState.insert_count_student_state))
async def insert_count_student(message: Message, state: FSMContext):
    await state.set_state(StartMarkState.insert_count_student_state)
    text = message.text
    if not text.isdigit():
        await message.answer("Введите неотрицательное целое число.")
        return
    count_student = int(text)
    user_tg_id = message.from_user.id
    status, sum_count_student, text, keyboards_data = await validate_count_students(count_student, user_tg_id)
    if status == StatusValidCountStudent.OK:
        await state.update_data(sum_count_student=sum_count_student)
        keyboards = construct_keyboards(keyboards_data)
        await message.answer(text, reply_markup=keyboards)
    else:
        await message.answer(text)


@start_mark_router.callback_query(F.data.startswith("confirm_delete"),
                                  StateFilter(StartMarkState.insert_count_student_state))
async def confirm_delete(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    sum_count_student = data.get('sum_count_student')
    user_tg_id = callback.from_user.id
    text = await mark.delete_random_students(sum_count_student, user_tg_id)
    await callback.message.edit_text(text)
    await state.clear()