"""
1. Получаем клавиатуру с настройками списков (Добавить студента, удалить студента, перевести студента)
2. При выборе добавить студента:
- Выбор группы (Можно выбрать из клавиатуры или ввести самому (Валидатор делать))
- Ввод фио (Валидатор)
3. При удалении студента:
- Выбор из списка
- Ввод фио отдельно
4. При переводе студента
- выбрать студента из списка или ввод самому ФИО
- выбрать группу, куда переводить

5. Подтверждение каждого действия
"""
from core.enums import StatusSettingsList
from core.requests import group, students
from core.utils.loggers import log


def get_settings_list_keyboard():
    keyboards = {
        'type': 'inline',
        'buttons': [
            {
                'text': 'Добавить студента',
                'callback_data': 'action_add'
            },
            {
                'text': 'Удалить студента',
                'callback_data': 'action_delete'
            }
            # {
            #     'text': 'Перевести студента',
            #     'callback_data': 'action_transfer'
            # }
        ]
    }
    text = 'Выберите операцию:'
    return text, keyboards


async def get_course_list(user_id: int) -> tuple[StatusSettingsList, str, dict | None]:
    """
    Получает учебные курсы
    :param user_id: ид преподавателя для отладки
    :return: Статус ответа, текст для ответа, кнопки
    """
    course_list = await group.get_courses()
    if course_list:
        text = 'Выберите курс:'
        button = []
        for course in course_list:
            button.append({
                'text': f'{course} курс',
                'callback_data': f'course_{course}'
            })
        button.append({
            'text': 'Назад',
            'callback_data': 'back_settings_list'
        })
        keyboards = {
            'type': 'inline',
            'buttons': button
        }
        return StatusSettingsList.OK, text, keyboards
    text = 'Запрашиваемая информация не найдена =('
    log.warning(f'Преподаватель (id {user_id}) не получил курсы для выбора')
    return StatusSettingsList.NO_INFO, text, None


async def get_groups_list(course: int, user_id: int) -> tuple[StatusSettingsList, str, dict | None]:
    groups_list = await group.get_group_course(course)
    if groups_list:
        text = 'Выберите группу:'
        button = []
        for group_id, group_name in groups_list:
            button.append({
                'text': f'{group_name}',
                'callback_data': f'group_{group_id}'
            })
        button.append({
            'text': 'Назад',
            'callback_data': 'back_choice_course'
        })
        keyboards = {
            'type': 'inline',
            'buttons': button
        }
        return StatusSettingsList.OK, text, keyboards
    text = 'Запрашиваемая информация не найдена =('
    log.warning(f'Преподаватель (id {user_id}) не получил группы для вывода')
    return StatusSettingsList.NO_INFO, text, None

async def get_student_list(group_id: int, user_id: int, prefix: str = None) -> tuple[StatusSettingsList, str, dict | None]:
    student_list = await group.get_group_students(group_id)
    if student_list:
        text = "Выберите студента или введите ФИО студента вручную:"
        button = []
        for id_, last_name, first_name, middle_name in student_list:
            fullname = f"{last_name} {first_name[0]}."
            if middle_name:
                fullname += f"{middle_name[0]}."
            button.append({
                'text': fullname,
                'callback_data': f'{prefix}_student_{id_}' if prefix else f'student_{id_}'
            })
        button.append({
            'text': 'Назад',
            'callback_data': 'back_choice_groups'
        })
        keyboards = {
            'type': 'inline',
            'buttons': button
        }
        return StatusSettingsList.OK, text, keyboards
    text = 'Запрашиваемая информация не найдена =('
    log.warning(f'Преподаватель (id {user_id}) не получил студентов для вывода')
    return StatusSettingsList.NO_INFO, text, None

async def get_student_info(student_id: int, group_id: int) -> str:
    """
    Получает информацию по студенту:
    1) ФИО в бд
    2) Группа студента
    :param student_id: ид студента в бд
    :param group_id: ид группы в бд
    :return:
    """
    fullname_dict = await students.get_student_fullname(student_id)
    first_name = fullname_dict.get('first_name')
    last_name = fullname_dict.get('last_name')
    middle_name = fullname_dict.get('middle_name')
    fullname_str = f'{last_name} {first_name} {middle_name or ""}'
    group_name = await group.get_group_name(group_id)
    text = (f'ФИО студента: {fullname_str}\n'
            f'Группа: {group_name or "Неизвестно"}')
    return text

async def confirm_delete_student(student_id: int, group_id: int) -> tuple[StatusSettingsList, str, dict | None]:
    student_info = await get_student_info(student_id, group_id)
    text = (f"{student_info}\n"
            f"Подтвердите удаление студента или вернитесь назад")
    keyboards = {
        "type": "inline",
        "buttons": [
            {
                "text": "Удалить",
                "callback_data": "confirm_delete"
            },
            {
                "text": "Назад",
                "callback_data": "back_choice_students"
            }
        ]
    }
    return StatusSettingsList.OK, text, keyboards


async def delete_student(student_id: int) -> tuple[StatusSettingsList, str]:
    fullname_dict = await students.get_student_fullname(student_id)
    await students.delete_student(student_id)
    fullname_str = f'{fullname_dict.get("last_name")} {fullname_dict.get("first_name")} {fullname_dict.get("middle_name") or ""}'
    text = f'Студент {fullname_str} удален'
    return StatusSettingsList.OK, text


async def input_fullname_student() -> tuple[StatusSettingsList, str, dict | None]:
    text = (f"Введите ФИО студента в формате:\n"
            f"Фамилия Имя Отчество\n"
            f"Например: Иванов Иван Иванович")
    keyboards = {
        'type': 'inline',
        'buttons': [
            {
                'text': 'Назад',
                'callback_data': 'back_settings_list'
            }
        ]
    }
    return StatusSettingsList.OK, text, keyboards