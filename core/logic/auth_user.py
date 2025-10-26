from core.enums import StatusAuthUser, StatusNewUser, StatusRegisterStudent
from core.redis_config import redis_link_teacher
from core.requests import teachers, students
from core.requests.students import is_auth_student
from core.validators import validator_string


async def check_auth_user(user_tg_id: int):
    text = "Добро пожаловать обратно."
    if await teachers.is_auth_teacher(user_tg_id):
        return StatusNewUser.OLD_USER_TEACHER, text
    elif await is_auth_student(user_tg_id):
        return StatusNewUser.OLD_USER_STUDENT, text
    else:
        text = ("Вы не авторизованы в системе.\n"
                "Пожалуйста, введите ваше полное имя (Фамилия Имя Отчество).\n"
                "Например: Иванов Иван Иванович:")

        return StatusNewUser.NEW_USER, text


async def auth_teacher(key: str, user_tg_id: int) -> tuple[StatusAuthUser, str]:
    teacher_id = redis_link_teacher.get(key)
    if not teacher_id:
        text = ("Ссылка для авторизации устарела.\n"
                "Запросите новую.")
        return StatusAuthUser.TIMEOUT_LINK, text
    # Возможно нужно выбрасывать сообщение с подтверждением перепривязки
    teacher_old_id = await teachers.get_teacher_id_by_tg_id(user_tg_id)
    if teacher_old_id:
        await teachers.set_teacher_tg_id(int(teacher_old_id), None)

    await teachers.set_teacher_tg_id(int(teacher_id), user_tg_id)
    redis_link_teacher.delete(key)
    teacher_data = await teachers.get_teacher_fullname(int(teacher_id))
    text = (f"Вы успешно авторизовались как преподаватель:\n"
            f"{teacher_data["last_name"]} {teacher_data["first_name"]} {teacher_data["middle_name"]}")
    return StatusAuthUser.OK, text


def _split_fullname_to_dict(fullname: str) -> dict:
    fullname_split = fullname.split()
    return {
        "first_name": fullname_split[1],
        "last_name": fullname_split[0],
        "middle_name": fullname_split[2] if len(fullname_split) > 2 else None
    }


async def auth_student(user_tg_id: int, fullname: str) -> tuple[StatusRegisterStudent, str | None]:
    if not validator_string.is_valid_fullname(fullname):
        text = ("Некорректный формат имени.\n"
                "Пожалуйста, введите ваше полное имя (Фамилия Имя Отчество).\n"
                "Например: Иванов Иван Иванович")
        return StatusRegisterStudent.INVALID_FULLNAME, text
    fullname_split = _split_fullname_to_dict(fullname)
    student_id = await students.get_student_id_by_fullname(fullname_split)
    if not student_id:
        text = ("Введенное ФИО не найдено в базе.\n"
                "Проверьте правильность вводимых данных и повторите попытку.")
        return StatusRegisterStudent.NOT_FOUND, text
    if await students.is_registered_student(student_id):
        text = "Студент с таким ФИО уже авторизован в системе."
        return StatusRegisterStudent.BUSY_REGISTER, text
    await students.set_student_tg_id(student_id, user_tg_id)
    text = "Вы успешно авторизовались."
    return StatusRegisterStudent.OK, text
