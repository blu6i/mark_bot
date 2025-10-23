from core.validators import validator_string
from core.enums import StatusRegisterStudent
from core.requests import students

def _split_fullname_to_dict(fullname: str) -> dict:
    fullname_split = fullname.split()
    return {
        "first_name": fullname_split[1],
        "last_name": fullname_split[0],
        "middle_name": fullname_split[2] if len(fullname_split) > 2 else None
    }

async def register_student(user_tg_id: int, fullname: str) -> tuple[StatusRegisterStudent, str | None]:
    if not validator_string.is_valid_fullname(fullname):
        text = """
        Некорректный формат имени.\n
        Пожалуйста, введите ваше полное имя (Фамилия Имя Отчество).\n
        Например: Иванов Иван Иванович
        """
        return StatusRegisterStudent.INVALID_FULLNAME, text
    fullname_split = _split_fullname_to_dict(fullname)
    student_id = await students.get_student_id_by_fullname(fullname_split)
    if not student_id:
        text = """
        Введенное ФИО не найдено в базе.\n
        Проверьте правильность вводимых данных и повторите попытку.
        """
        return StatusRegisterStudent.NOT_FOUND, text
    if await students.is_registered_student(student_id):
        text = """
        Студент с таким ФИО уже авторизован в системе.
        """
        return StatusRegisterStudent.BUSY_REGISTER, text
    await students.set_student_tg_id(student_id, user_tg_id)
    text = """
    Вы успешно авторизовались.
    """
    return StatusRegisterStudent.OK, text