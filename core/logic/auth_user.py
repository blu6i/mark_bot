from core.enums import StatusAuthUser
from core.redis_config import RedisDatabase
from core.requests import teachers

redis_auth_user = RedisDatabase(use_pool=False, prefix="auth_user")

async def auth_teacher(key: str, user_tg_id: int) -> tuple[StatusAuthUser, str]:
    # TODO: адоптировать функцию для авторизации студента
    #  В редис будем хранить в значении тип авторизации (teacher, student) и тут будет проверять тип авторизации
    teacher_id = redis_auth_user.get(key)
    if not teacher_id:
        text = """
        Ссылка для авторизации устарела.\n
        Запросите новую.
        """
        return StatusAuthUser.TIMEOUT_LINK, text
    # Возможно нужно выбрасывать сообщение с подтверждением перепривязки
    teacher_old_id = await teachers.get_teacher_id_by_tg_id(user_tg_id)
    if teacher_old_id:
        await teachers.set_teacher_tg_id(teacher_old_id, None)

    await teachers.set_teacher_tg_id(teacher_id, user_tg_id)
    redis_auth_user.delete(key)
    teacher_data = await teachers.get_teacher_fullname(teacher_id)
    text = f"""
    Вы успешно авторизовали как преподаватель.\n
    ФИО: {teacher_data["last_name"]} {teacher_data["first_name"]} {teacher_data["middle_name"]}
    """
    return StatusAuthUser.OK, text