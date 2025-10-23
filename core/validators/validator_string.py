def is_valid_fullname(fullname: str) -> bool:
    """
    Проверяет, что ФИО состоит из букв и содержит минимум имя и фамилию
    :param fullname: полное имя
    :return: True, если ФИО корректно, иначе False
    """
    parts = fullname.split()
    if len(parts) < 2:
        return False
    return all(part.isalpha() for part in parts)