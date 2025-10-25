import json

from core.enums import StatusValidCountStudent
from core.requests import group, students
from core.redis_config import redis_attendance


async def validate_count_students(count_student: int, chat_id: int) -> tuple[StatusValidCountStudent, int | None, str | None, dict | None]:
    lesson_instances_ids = [int(i) for i in json.loads(redis_attendance.get(chat_id))]
    if not lesson_instances_ids:
        text = 'Время для случайного удаления студентов уже прошло.'
        return StatusValidCountStudent.NO_DATA, None, text, None

    sum_count = 0
    for lesson_instances_id in lesson_instances_ids:
        groups_id = await group.get_groups_id_by_instance_id(lesson_instances_id)
        for group_id, _ in groups_id:
            sum_count += await students.get_count_students_instance(lesson_instances_id, group_id)
    extra_marks = sum_count - count_student

    if extra_marks == 0:
        # Кол-во отметившихся = кол-во присутствующих
        text = (f'Количество отмеченных студентов: {sum_count}\n'
                '\n'
                f'Вы ввели: {count_student}\n'
                'Введенное количество студентов совпадает с отмеченными.\n'
                'Введите другое число')
        return StatusValidCountStudent.EQUALLY, extra_marks, text, None
    elif extra_marks < 0:
        # Кол-во отметившихся < кол-во присутствующих. Сказать о проблеме с отметкой
        text = (f'Количество отмеченных студентов: {sum_count}\n'
                '\n'
                f'Вы ввели: {count_student}\n'
                '\n'
                'Введенное количество студентов превышает отмеченных.\n'
                'Введите другое количество студентов')
        return StatusValidCountStudent.OVER, extra_marks, text, None
    else:
        # При случайно удалении останутся отметки
        text = (f'Количество отмеченных студентов: {sum_count}\n'
                '\n'
                f'Вы ввели: {count_student}\n'
                f'\n'
                f'Подтвердите ввод или введите другое количество студентов')
        buttons_data = [
            {
                "text": "Удалить",
                "callback_data": "confirm_delete"
            }
        ]
        keyboards = {
            "type": "inline",
            "buttons": buttons_data
        }
        return StatusValidCountStudent.OK, extra_marks, text, keyboards