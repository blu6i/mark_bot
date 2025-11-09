import os

from aiogram.types import FSInputFile
from openpyxl import Workbook

from core.requests.lessons import get_date_instances, get_subject_schedule_for_teacher, get_subject_name_lesson
from core.enums import StatusLoadExcel
from core.requests.students import get_student_attendance

def _str_to_russian_date(date: str):
    return date[8:10] + '.' + date[5:7] + '.' + date[0:4]

async def get_date_marks(user_tg_id: int):
    date_list = await get_date_instances(user_tg_id)
    if not date_list:
        text = "Данные не найдены"
        return StatusLoadExcel.NO_DATA, text, None
    text = "Выберите дату"
    buttons_data = []
    for item in date_list:
        date = str(item[0])
        buttons_data.append({
            "text": _str_to_russian_date(date),
            "callback_data": f"date_{date}"
        })
    keyboards_data = {
        "type": "inline",
        "buttons": buttons_data
    }
    return StatusLoadExcel.OK, text, keyboards_data


def _get_short_name(text: str) -> str:
    return "".join(word[0].upper() for word in text.split() if word)


async def get_name_lessons_marks(user_tg_id: int, date: str):
    subject_schedule_list = await get_subject_schedule_for_teacher(user_tg_id, date)
    if not subject_schedule_list:
        text = "Данные не найдены"
        return StatusLoadExcel.NO_DATA, text, None
    text = "Выберите пару"
    buttons_data = []
    for item in subject_schedule_list:
        id_, lesson_type, subject_name = item
        lesson_type_short = _get_short_name(lesson_type)
        subject_name_short = subject_name[:63]
        buttons_data.append({
            "text": f"{lesson_type_short} | {subject_name_short}",
            "callback_data": f"subject_{id_}"
        })
    keyboards_data = {
        "type": "inline",
        "buttons": buttons_data
    }
    return StatusLoadExcel.OK, text, keyboards_data


def _sort_students_groups(students_attendance_list: list):
    result = {}
    for group_name, last_name, first_name, middle_name, status in students_attendance_list:
        fullname = f"{last_name} {first_name} {middle_name or ''}"
        if group_name not in result:
            result[group_name] = []
        result[group_name].append(fullname)
    return result


async def get_student_marks(instance_id: int):
    students_attendance_list = await get_student_attendance(instance_id)
    # sort_student_dict = _sort_students_groups(students_attendance_list)
    return students_attendance_list


async def load_msg_excel(instance_id: int, date: str, user_tg_id: int, func):
    """
    Создает Excel-файл со списком всех студентов по занятию.
    В колонке 'Посещение' отмечает '+' у тех, кто был на паре.

    :param instance_id: ID отметки
    :param date: Дата проведения занятия
    :param user_tg_id: Telegram ID пользователя
    :param func: Функция для отправки сообщения с документом
    """
    class_name = await get_subject_name_lesson(instance_id)
    attendance_data = await get_student_marks(instance_id)

    filename = f"{class_name}_{date}.xlsx"

    wb = Workbook()
    ws = wb.active
    ws.title = "Посещаемость"

    ws.append(["ФИО студента", "Группа", "Посещение"])
    for group_name, last_name, first_name, middle_name, status in attendance_data:
        full_name = " ".join(filter(None, [last_name, first_name, middle_name]))
        mark = "н" if not status else ""
        ws.append([full_name, group_name, mark])

    ws.column_dimensions['A'].width = 60
    ws.column_dimensions['B'].width = 30
    ws.column_dimensions['C'].width = 15

    wb.save(filename)
    document = FSInputFile(filename)
    await func(chat_id=user_tg_id, document=document)
    os.remove(filename)