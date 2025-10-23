import json

from core.enums import StatusValidCountStudent
from core.requests import group, students
from core.redis_config import redis_attendance


async def validate_count_students(count_student: int, chat_id: int):
    lesson_instances_ids = [int(i) for i in json.loads(redis_attendance.get(chat_id))]
    if not lesson_instances_ids:
        return StatusValidCountStudent.NO_DATA, None

    sum_count = 0
    for lesson_instances_id in lesson_instances_ids:
        groups_id = await group.get_groups_id_by_instance_id(lesson_instances_id)
        for group_id, _ in groups_id:
            sum_count += await students.get_count_students_instance(lesson_instances_id, group_id)
    extra_marks = sum_count - count_student

    if extra_marks == 0:
        # Кол-во отметившихся = кол-во присутствующих
        return StatusValidCountStudent.EQUALLY, sum_count
    elif extra_marks < 0:
        # Кол-во отметившихся < кол-во присутствующих. Сказать о проблеме с отметкой
        return StatusValidCountStudent.OVER, sum_count
    else:
        # При случайно удалении останутся отметки
        return StatusValidCountStudent.OK, sum_count