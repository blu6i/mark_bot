from datetime import datetime, timedelta

from core.database_config import db_async
from core.enums import StatusLoadExcel, StatusRunMark
from core.requests.teachers import get_teacher_id_by_tg_id

async def get_date_instances(user_tg_id: int) -> tuple[str] | None:
    """
    Поиск дат, за которые были пары у преподавателя
    :param user_tg_id: телеграм id преподавателя
    :return: кортеж с датами или None, если пар не было
    """
    teacher_id = await get_teacher_id_by_tg_id(user_tg_id)
    sql = """
        SELECT DISTINCT l.date
        FROM mark_bot.lesson_instances li
        JOIN mark_bot.lessons l ON l.id = li.lesson_id
        JOIN mark_bot.lesson_instance_teachers lit ON lit.lesson_instance_id = li.id
        JOIN mark_bot.teacher_subjects ts ON lit.teacher_subject_id = ts.id
        WHERE ts.teacher_id = $1
    """
    results = await db_async.select(
        sql=sql,
        params=[teacher_id],
        fetchone=False
    )
    return results


async def get_subject_schedule_for_teacher(user_tg_id: int, date: str) -> tuple[StatusLoadExcel, list[tuple[int, str, str]] | None]:
    """
    Получение предметы и их тип, по которым запускались отметки у преподавателя
    :param user_tg_id: телеграм id преподавателя
    :param date: Дата, по которой нужно достать отметки
    :return: Кортеж из статуса выполнения и списка занятий в формате (id_занятия, тип_занятия, название_предмета)
             Если расписание не найдено, возвращается StatusLoadExcel.NOPE и None
    """
    teacher_id = await get_teacher_id_by_tg_id(user_tg_id)
    sql = """
        SELECT DISTINCT li.id, l.lesson_type, s.name
        FROM mark_bot.lesson_instances li
        JOIN mark_bot.lessons l ON l.id = li.lesson_id
        JOIN mark_bot.lesson_instance_groups lig ON li.id = lig.lesson_instance_id
        JOIN mark_bot.subjects s ON l.subject_id = s.id
        JOIN mark_bot.teacher_subjects ts ON ts.subject_id = s.id 
        AND ts.group_id = lig.group_id 
        AND ts.lesson_type = l.lesson_type
        WHERE ts.teacher_id = $1 AND l.date = $2
    """
    date_obj = datetime.strptime(date, "%Y-%m-%d").date()
    results = await db_async.select(
        sql=sql,
        params=[teacher_id, date_obj],
        fetchone=False
    )
    return results


async def get_actual_lesson_teacher(user_tg_id: int) -> tuple[StatusRunMark, list[dict] | None]:
    """
    Получает актуальную пару для преподавателя.
    Учитывает, что одна пара может идти у нескольких групп (поточная).
    """
    teacher_id = await get_teacher_id_by_tg_id(user_tg_id)
    if not teacher_id:
        return StatusRunMark.IS_NO_TEACHER, None

    now_date = datetime.now().date()
    now_time = datetime.now().time()

    # 1️⃣ Находим последнюю (по id) актуальную пару преподавателя
    sql_last_lesson = """
        SELECT l.id, l.subject_id, l.lesson_type, l.start_time, l.end_time
        FROM mark_bot.lessons l
        JOIN mark_bot.teacher_subjects ts
          ON ts.subject_id = l.subject_id
         AND ts.lesson_type = l.lesson_type
         AND ts.teacher_id = $1
        JOIN mark_bot.lesson_groups lg
          ON lg.lesson_id = l.id
         AND lg.group_id = ts.group_id
        WHERE l.date = $2
          AND l.start_time <= $3
          AND l.end_time >= $4
        ORDER BY l.id DESC
        LIMIT 1
    """
    latest_lesson = await db_async.select(
        sql=sql_last_lesson,
        params=[teacher_id, now_date, now_time, now_time],
        fetchone=True
    )

    if not latest_lesson:
        return StatusRunMark.NO_PAIR_TEACHER, None

    lesson_id, subject_id, lesson_type, start_time, end_time = latest_lesson

    # 2️⃣ Берём все группы, которые имеют такую же пару (по сути, поточные)
    sql_groups = """
        SELECT ts.id, ts.count, s.name AS subject_name, g.id AS group_id, g.name AS group_name, l.id AS lesson_id
        FROM mark_bot.lessons l
        JOIN mark_bot.lesson_groups lg ON lg.lesson_id = l.id
        JOIN mark_bot.groups g ON g.id = lg.group_id
        JOIN mark_bot.teacher_subjects ts
          ON ts.group_id = g.id
         AND ts.subject_id = l.subject_id
         AND ts.lesson_type = l.lesson_type
         AND ts.teacher_id = $1
        JOIN mark_bot.subjects s ON s.id = l.subject_id
        WHERE l.date = $2
          AND l.start_time = $3
          AND l.end_time = $4
          AND l.subject_id = $5
          AND l.lesson_type = $6
        ORDER BY g.name
    """
    results = await db_async.select(
        sql=sql_groups,
        params=[teacher_id, now_date, start_time, end_time, subject_id, lesson_type],
        fetchone=False
    )

    lesson_data_list = []
    for ts_id, count, subject_name, group_id, group_name, lesson_id in results:
        lesson_data_list.append({
            "lesson_id": lesson_id,
            "teacher_subject_id": ts_id,
            "pair_number": count,
            "group_id": group_id,
            "group_name": group_name,
            "subject_name": subject_name,
            "lesson_type": lesson_type,
            "date": now_date,
            "time": now_time
        })

    return StatusRunMark.OK, lesson_data_list


async def increment_stay_count_subject(teacher_subject_ids: list[int]):
    """
    Увеличивает количество прошедших пар по предмету у групп
    :param teacher_subject_ids: id предметов, которые нужно увеличить
    """
    for teacher_subject_id in teacher_subject_ids:
        sql = """
            SELECT count 
            FROM mark_bot.teacher_subjects 
            WHERE id = $1
        """
        result = await db_async.select(
            sql=sql,
            params=[teacher_subject_id],
            fetchone=True
        )
        count = result[0]
        sql = """
            UPDATE mark_bot.teacher_subjects 
            SET count = $1 
            WHERE id = $2
        """
        await db_async.update(
            sql=sql,
            params=[count + 1, teacher_subject_id]
        )


async def insert_lesson_instance(mark_data: list[dict]) -> list[int]:
    """
    Создает отметку для каждой группы, если её еще нет.
    :param mark_data: данные для пары
    :return: id созданных отметок
    """
    lesson_instance_ids = []
    teacher_subjects_to_decrement = set()
    for item in mark_data:
        lesson_id = item.get("lesson_id")
        ts_id = item.get("teacher_subject_id")
        pair_number = item.get("pair_number")
        group_id = item.get("group_id")

        # 1. Проверка на уже созданную пару для отметки
        sql = """
            SELECT id FROM mark_bot.lesson_instances
            WHERE lesson_id = $1
        """
        result = await db_async.select(
            sql=sql,
            params=[lesson_id],
            fetchone=True
        )
        if result:
            lesson_instance_id = result[0]
        else:
            # 2. Создание новой отметки
            sql = """
                INSERT INTO mark_bot.lesson_instances (lesson_id, pair_number)
                VALUES ($1, $2)
                RETURNING id
            """
            lesson_instance_id = await db_async.insert(
                sql=sql,
                params=[lesson_id, pair_number],
                returning=True
            )

        # 3. Связь с группой
        sql = """
            INSERT INTO mark_bot.lesson_instance_groups (lesson_instance_id, group_id)
            VALUES ($1, $2)
            ON CONFLICT DO NOTHING
        """
        await db_async.insert(
            sql=sql,
            params=[lesson_instance_id, group_id]
        )

        # 4. Связь с преподавателем через lesson_instance_teachers
        sql = """
            INSERT INTO mark_bot.lesson_instance_teachers (lesson_instance_id, teacher_subject_id)
            VALUES ($1, $2)
            ON CONFLICT DO NOTHING
        """
        await db_async.insert(
            sql=sql,
            params=[lesson_instance_id, ts_id]
        )
        lesson_instance_ids.append(lesson_instance_id)
        teacher_subjects_to_decrement.add(ts_id)

    if teacher_subjects_to_decrement:
        await increment_stay_count_subject(list(teacher_subjects_to_decrement))
    return lesson_instance_ids


async def insert_custom_lesson(type_: str, subject_id: int, groups: list[int], user_tg_id: int) -> list[dict]:
    """
    Создает новую пару
    :param type_: тип пары
    :param subject_id: id предмета
    :param groups: список групп
    :param user_tg_id: id телеграм преподавателя
    :return: данные пары
    """
    teacher_id = await get_teacher_id_by_tg_id(user_tg_id)
    date = datetime.now().date()
    start_time = datetime.now().time().replace(microsecond=0)
    end_time = (datetime.now() + timedelta(minutes=5)).time().replace(microsecond=0)
    sql = """
        INSERT INTO mark_bot.lessons
            (subject_id, date, start_time, end_time, lesson_type)
        VALUES ($1, $2, $3, $4, $5)
        RETURNING id
    """
    lesson_id = await db_async.insert(
        sql=sql,
        params=[subject_id, date, start_time, end_time, type_],
        returning=True
    )

    data = []
    for group_id in groups:
        sql = """
            INSERT INTO mark_bot.lesson_groups (lesson_id, group_id)
            VALUES ($1, $2)
        """
        await db_async.insert(
            sql=sql,
            params=[lesson_id, group_id]
        )
        sql = """
            SELECT id, count
            FROM mark_bot.teacher_subjects
            WHERE teacher_id = $1 
            AND subject_id = $2 
            AND group_id = $3 
            AND lesson_type = $4
        """
        result = await db_async.select(
            sql=sql,
            params=[teacher_id, subject_id, group_id, type_],
            fetchone=True
        )
        ts_id, count = result
        data.append({
            'teacher_subject_id': ts_id,
            'pair_number': count,
            'group_id': group_id,
            'lesson_id': lesson_id
        })
    return data


async def get_subject_name(subject_id: int) -> str | None:
    """
    Получает название предмета по его id
    :param subject_id: id предмета
    :return: название предмета
    """
    sql = """
        SELECT name
        FROM mark_bot.subjects
        WHERE id = $1
    """
    result = await db_async.select(
        sql=sql,
        params=[subject_id],
        fetchone=True
    )
    return result[0] if result else None


async def get_subject_name_lesson(lesson_instance_id: int) -> str:
    """
    Получает название предмета по id отметки
    :param lesson_instance_id: id пары
    :return: название предмета
    """
    sql = """
        SELECT s.name FROM mark_bot.subjects s
        JOIN mark_bot.lessons l ON s.id = l.subject_id
        JOIN mark_bot.lesson_instances li ON l.id = li.lesson_id
        WHERE li.id = $1
    """
    result = await db_async.select(
        sql=sql,
        params=[lesson_instance_id],
        fetchone=True
    )
    return result[0] if result else None
