from enum import Enum

class StatusRegisterStudent(Enum):
    OK = 1
    NOT_FOUND = 2
    INVALID_FULLNAME = 3
    BUSY_REGISTER = 4


class StatusAuthUser(Enum):
    OK = 1
    TIMEOUT_LINK = 2


class RunMarkStatus(Enum):
    OK = 1
    HAS_STARTED_MARK = 2
    NO_PAIR_TEACHER = 3
    IS_NO_TEACHER = 4


class AttendanceStudent(Enum):
    OK = 1
    ALREADY = 2
    ERROR=3

class StatusLoadExcel(Enum):
    OK = 1
    NO_DATA = 2
    ERROR = 3
