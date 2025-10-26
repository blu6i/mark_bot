from core.database_config import db_async
from core.enums import StatusAttendanceMark


async def is_auth_student(user_tg_id: int) -> bool:
    """
    Проверяет, авторизован ли пользователь как студент в базе данных
    :param user_tg_id: id пользователя в телеграме
    :return: True если пользователь зарегистрирован, False если нет
    """
    sql = """
        SELECT 1 
        FROM mark_bot.students 
        WHERE tg_id = $1
    """
    result = await db_async.select(
        sql=sql,
        params=[user_tg_id],
        fetchone=True
    )
    return result is not None


async def set_student_tg_id(student_id: int, user_tg_id: int | None):
    """
    Устанавливает id телеграма для студента
    :param student_id: id студента в базе данных
    :param user_tg_id: id студента в телеграме
    """
    sql = """
        UPDATE mark_bot.students 
        SET tg_id = $1 
        WHERE id = $2
    """
    await db_async.update(
        sql=sql,
        params=[user_tg_id, student_id]
    )


async def get_student_id_by_tg_id(user_tg_id: int) -> int | None:
    """
    Получает id телеграма для студента
    :param user_tg_id: id телеграм студента
    :return: id студента в базе данных
    """
    sql = """
        SELECT id 
        FROM mark_bot.students 
        WHERE tg_id = $1
    """
    result = await db_async.select(
        sql=sql,
        params=[user_tg_id],
        fetchone=True
    )
    return result[0] if result else None


async def get_student_group_id(student_id: int) -> int | None:
    """
    Полуает id группы студента
    :param student_id: id студента в базе данных
    :return: id группы студента
    """
    sql = """
        SELECT group_id 
        FROM mark_bot.students 
        WHERE id = $1
    """
    result = await db_async.select(
        sql=sql,
        params=[student_id],
        fetchone=True
    )
    return result[0] if result else None


async def get_count_students_instance(lesson_instance_id: int, group_id: int) -> int | None:
    """
    Получает количество студентов, которые отметились на занятии
    :param lesson_instance_id: id занятия
    :param group_id: id группы
    :return: количество студентов
    """
    sql = """
        SELECT COUNT(a.id) FROM mark_bot.attendance a
        JOIN mark_bot.students s ON s.id = a.student_id
        WHERE a.lesson_instance_id = $1 AND s.group_id = $2
    """
    result = await db_async.select(
        sql=sql,
        params=[lesson_instance_id, group_id],
        fetchone=True
    )
    return result[0] if result else None


async def get_students_id_instance(lesson_instance_id: int, group_id: int) -> list[int]:
    """
    Получает ид студентов и ид отметки
    :param lesson_instance_id: id занятия
    :param group_id: id группы
    :return: количество студентов
    """
    sql = """
        SELECT a.id, s.id FROM mark_bot.attendance a
        JOIN mark_bot.students s ON s.id = a.student_id
        WHERE a.lesson_instance_id = $1 AND s.group_id = $2
    """
    result = await db_async.select(
        sql=sql,
        params=[lesson_instance_id, group_id],
        fetchone=False
    )
    return result if result else []


async def delete_attendance_student(attendance_id: int):
    """
    Удаляет отметку студента
    :param attendance_id: id отметки
    """
    sql = """
        DELETE FROM mark_bot.attendance 
        WHERE id = $1
    """
    await db_async.delete(
        sql=sql,
        params=[attendance_id]
    )


async def get_student_id_by_fullname(fullname: dict) -> int | None:
    """
    Полуает id студента по ФИО
    :param fullname: ФИО студента
    :return: id студента в базе данных
    """
    sql = """
        SELECT id FROM mark_bot.students
        WHERE first_name = $1
        AND last_name = $2
        AND middle_name IS NOT DISTINCT FROM $3
    """
    result = await db_async.select(
        sql=sql,
        params=[fullname["first_name"], fullname["last_name"], fullname.get("middle_name")],
        fetchone=True
    )
    return result[0] if result else None


async def get_student_last_name(student_id: int) -> str | None:
    """
    Полуает фамилию студента по его id
    :param student_id: id студента в базе данных
    :return: фамилия студента
    """
    sql = """
        SELECT last_name 
        FROM mark_bot.students
        WHERE id = $1
    """
    result = await db_async.select(
        sql=sql,
        params=[student_id],
        fetchone=True
    )
    return result[0] if result else None


async def is_registered_student(student_id: int) -> bool:
    """
    Проверяет, зарегистрирован ли студент с ФИО в базе данных
    :param student_id: id студента в базе данных
    :return: True если студент зарегистрирован, False если нет
    """
    sql = """
        SELECT 1 
        FROM mark_bot.students 
        WHERE id = $1 AND tg_id IS NOT NULL
    """
    result = await db_async.select(
        sql=sql,
        params=[student_id],
        fetchone=True
    )
    return result is not None


async def get_student_attendance(instance_id: int) -> list[tuple[str, str, str, str]] | list:
    """
    Получает отметки студента по id занятия
    :param instance_id: id занятия
    :return: Список кортежей с информацией о студентах в формате
             (название_группы, фамилия, имя, отчество)
             Отсортировано по названию группы, фамилии, имени и отчеству студентов
    """
    sql = """
        SELECT g.name, s.last_name, s.first_name, s.middle_name
        FROM mark_bot.students s
        JOIN mark_bot.attendance a ON a.student_id = s.id
        JOIN mark_bot.groups g ON g.id = s.group_id
        WHERE a.lesson_instance_id = $1
        ORDER BY g.name, s.last_name, s.first_name, s.middle_name
    """
    results = await db_async.select(
        sql=sql,
        params=[instance_id],
        fetchone=False
    )
    return results if results else []


async def insert_student_attendance(student_id: int, lesson_instance_id: int) -> StatusAttendanceMark:
    """
    Добавляет отметку студента
    :param lesson_instance_id: id занятия
    :param student_id: id студента
    :return: id отметки
    """
    sql = """
        INSERT INTO mark_bot.attendance (student_id, lesson_instance_id)
        VALUES ($1, $2)
        ON CONFLICT (student_id, lesson_instance_id) DO NOTHING
        RETURNING id;
    """
    result = await db_async.insert(
        sql=sql,
        params=[student_id, lesson_instance_id],
        returning=True
    )
    if result:
        return StatusAttendanceMark.OK
    sql = """
        SELECT id FROM mark_bot.attendance
        WHERE student_id = $1 AND lesson_instance_id = $2
    """
    result = await db_async.select(
        sql=sql,
        params=[student_id, lesson_instance_id],
        fetchone=True
    )
    if result:
        return StatusAttendanceMark.ALREADY
    return StatusAttendanceMark.ERROR


async def is_instance_group_student(instance_id: int, student_id: int) -> bool:
    """
    Проверяет, относится ли студент к группе занятия
    :param instance_id: id занятия
    :param student_id: id студента
    :return: True если студент относится к группе занятия, False если нет
    """
    sql = """
        SELECT 1 FROM mark_bot.lesson_instance_groups
        WHERE lesson_instance_id = $1 AND group_id = (
            SELECT group_id FROM mark_bot.students
            WHERE id = $2
        )
    """
    result = await db_async.select(
        sql=sql,
        params=[instance_id, student_id],
        fetchone=True
    )
    return result is not None
