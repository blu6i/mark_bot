from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command, or_f, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from bots.tg_bot.handlers import filters
from bots.tg_bot.handlers.filters import CorrectWordCommand
from bots.tg_bot.handlers.keyboards import construct_keyboards

from core.logic.admins import settings_list as sl
from core.enums import StatusSettingsList

settings_list_router = Router()


class SettingsList(StatesGroup):
    """
    Состояния для настроек списков
    """
    choice_settings = State()
    choice_course = State()
    choice_group = State()
    choice_student = State()
    confirm_delete = State()
    confirm_transfer = State()


@settings_list_router.message(or_f(F.text),
                              CorrectWordCommand(['управление списками']),
                              filters.IsAdmin())
async def settings_list(message: Message, state: FSMContext):
    await state.clear()
    text, keyboards_data = sl.get_settings_list_keyboard()
    keyboards = construct_keyboards(keyboards_data)
    await message.answer(text, reply_markup=keyboards)
    await state.set_state(SettingsList.choice_settings)


@settings_list_router.callback_query(F.data.startswith('back_settings_list'),
                              filters.IsAdmin(),
                              SettingsList.choice_course)
async def settings_list(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    text, keyboards_data = sl.get_settings_list_keyboard()
    keyboards = construct_keyboards(keyboards_data)
    await callback.message.edit_text(text, reply_markup=keyboards)
    await state.set_state(SettingsList.choice_settings)


@settings_list_router.callback_query(or_f(F.data.startswith('action'), F.data.startswith('back_choice_course')),
                                     SettingsList.choice_settings)
async def choice_course(callback: CallbackQuery, state: FSMContext):
    if callback.data.startswith('action'):
        action = callback.data.removeprefix('action_')
        await state.update_data(action=action)
    status, text, keyboards_data = await sl.get_course_list(callback.from_user.id)
    if status != StatusSettingsList.OK:
        await callback.message.edit_text(text)
        await state.clear()
    else:
        keyboards = construct_keyboards(keyboards_data)
        await callback.message.edit_text(text, reply_markup=keyboards)
        await state.set_state(SettingsList.choice_course)


@settings_list_router.callback_query(or_f(F.data.startswith('course_'), F.data.startswith('back_choice_groups')),
                                     StateFilter(SettingsList.choice_course, SettingsList.choice_group))
async def choice_group(callback: CallbackQuery, state: FSMContext):
    if callback.data.startswith('course_'):
        course = int(callback.data.removeprefix('course_'))
        await state.update_data(course=course)
    else:
        data = await state.get_data()
        course = data.get('course')
    status, text, keyboards_data = await sl.get_groups_list(course, callback.from_user.id)
    if status != StatusSettingsList.OK:
        await callback.message.edit_text(text)
        await state.clear()
    else:
        keyboards = construct_keyboards(keyboards_data)
        await callback.message.edit_text(text, reply_markup=keyboards)
        await state.set_state(SettingsList.choice_group)


@settings_list_router.callback_query(or_f(F.data.startswith('group_'), F.data.startswith('back_choice_students')),
                                     StateFilter(SettingsList.choice_group, SettingsList.choice_student))
async def choice_student(callback: CallbackQuery, state: FSMContext):
    if callback.data.startswith('group_'):
        group_id = int(callback.data.removeprefix('group_'))
        await state.update_data(group_id=group_id)
    else:
        data = await state.get_data()
        group_id = data.get('group_id')
    data = await state.get_data()
    action = data.get('action')
    status, text, keyboards_data = await sl.get_student_list(group_id, callback.from_user.id, action)
    if status != StatusSettingsList.OK:
        await callback.message.edit_text(text)
        await state.clear()
    else:
        keyboards = construct_keyboards(keyboards_data)
        await callback.message.edit_text(text, reply_markup=keyboards)
        await state.set_state(SettingsList.choice_student)


@settings_list_router.callback_query(F.data.startswith('delete_student_'),
                                     SettingsList.choice_student)
async def confirm_delete(callback: CallbackQuery, state: FSMContext):
    student_id = int(callback.data.removeprefix('delete_student_'))
    data = await state.get_data()
    group_id = data.get('group_id')
    status, text, keyboards_data = await sl.confirm_delete_student(student_id, group_id)
    if status != StatusSettingsList.OK:
        await callback.message.edit_text(text)
        await state.clear()
    else:
        keyboards = construct_keyboards(keyboards_data)
        await callback.message.edit_text(text, reply_markup=keyboards)
        await state.update_data(student_id=student_id)
        await state.set_state(SettingsList.confirm_delete)


@settings_list_router.callback_query(F.data.startswith('confirm_delete'),
                                     SettingsList.confirm_delete)
async def delete_student(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    student_id = data.get('student_id')
    status, text = await sl.delete_student(student_id)
    await callback.message.edit_text(text)
    await state.clear()
