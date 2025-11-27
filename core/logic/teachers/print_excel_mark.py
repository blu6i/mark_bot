import os

from aiogram.types import FSInputFile
from openpyxl import Workbook

from core.requests.lessons import get_date_instances, get_subject_schedule_for_teacher, get_subject_name_lesson, \
    update_clear_lesson_instance, get_status_clear_instance
from core.enums import StatusLoadExcel, StatusValidCountStudent
from core.requests.students import get_student_attendance, get_count_students_instance, get_random_student_instance, \
    delete_instance_student, get_count_student_id_instance


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
    buttons_data.append({
        "text": "Назад",
        "callback_data": "back"
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


def get_keyboard_option():
    text = "Выберите действие:"
    keyboards_data = {
        'type': 'inline',
        'buttons': [
            {
                "text": f"Удалить случайно",
                "callback_data": f"remove_random_student"
            },
            {
                'text': 'Получить таблицу',
                'callback_data': 'get_student_list'
            },
            {
                'text': 'Назад',
                'callback_data': 'back'
            }
        ]
    }
    return text, keyboards_data


# ===[Рандомное удаление]===
async def get_info_delete_student(instance_id: int):
    count_student = await get_count_student_id_instance(instance_id)
    text = (f'Отмечено студентов: {count_student}\n'
            f'Укажите количество студентов на паре:')
    keyboards_data = {
        "type": "inline",
        "buttons": [{
            'text': 'Назад',
            'callback_data': 'back'
        }]
    }
    return text, keyboards_data

async def start_delete_random_student(instance_id: int):
    status_clear = await get_status_clear_instance(instance_id)
    if status_clear:
        text = ('Внимание! Вы уже выбирали случайное удаление.\n'
                'Подтвердите свое действие или вернитесь назад.')
        keyboards_data = {
            'type': 'inline',
            'buttons': [{
                'text': 'Подтвердить',
                'callback_data': 'confirm_rerun_delete'
            },
                {
                    'text': 'Назад',
                    'callback_data': 'back'
                }
            ]
        }
        return text, keyboards_data, StatusLoadExcel.HAVE_DELETE
    else:
        text, keyboards_data = await get_info_delete_student(instance_id)
        return text, keyboards_data, StatusLoadExcel.OK


async def validate_count_students(count_student: int, instance_id: int) -> tuple[StatusValidCountStudent, int | None, str | None, dict | None]:
    count_student_instance = await get_count_student_id_instance(instance_id)
    extra_marks = count_student_instance - count_student
    if extra_marks == 0:
        # Кол-во отметившихся = кол-во присутствующих
        text = (f'Количество отмеченных студентов: {count_student_instance}\n'
                '\n'
                f'Вы ввели: {count_student}\n'
                'Введенное количество студентов совпадает с отмеченными.\n'
                'Введите другое число')
        return StatusValidCountStudent.EQUALLY, None, text, None
    elif extra_marks < 0:
        # Кол-во отметившихся < кол-во присутствующих. Сказать о проблеме с отметкой
        text = (f'Количество отмеченных студентов: {count_student_instance}\n'
                '\n'
                f'Вы ввели: {count_student}\n'
                '\n'
                'Введенное количество студентов превышает отмеченных.\n'
                'Введите другое количество студентов')
        keyboards = {
            "type": "inline",
            "buttons": [{
                "text": "Назад",
                "callback_data": "back",
            }]
        }
        return StatusValidCountStudent.OVER, None, text, keyboards
    else:
        # При случайно удалении останутся отметки
        text = (f'Количество отмеченных студентов: {count_student_instance}\n'
                '\n'
                f'Вы ввели: {count_student}\n'
                f'\n'
                f'Подтвердите ввод или введите другое количество студентов')
        buttons_data = [
            {
                "callback_data": "confirm_delete",
                "text": 'Удалить',
            },
            {
                "text": "Назад",
                "callback_data": "back",
            }
        ]
        keyboards = {
            "type": "inline",
            "buttons": buttons_data
        }
        return StatusValidCountStudent.OK, extra_marks, text, keyboards


async def delete_random_instance_student(instance_id: int, extra_marks: int):
    list_student_for_delete = await get_random_student_instance(instance_id, extra_marks)
    await update_clear_lesson_instance(instance_id)
    list_name = []
    for id_, l_name in list_student_for_delete:
        await delete_instance_student(instance_id, id_)
        list_name.append(l_name)
    list_name.sort()
    text = (f'Удалены студенты:\n'
            f'{', '.join(list_name)}')
    return text

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