from enum import Enum

class StatusRegisterStudent(Enum):
    OK = 1
    NOT_FOUND = 2
    INVALID_FULLNAME = 3
    BUSY_REGISTER = 4


class StatusAuthUser(Enum):
    OK = 1
    TIMEOUT_LINK = 2


class StatusNewUser(Enum):
    NEW_USER = 1
    OLD_USER_STUDENT = 2
    OLD_USER_TEACHER = 3

class StatusRunMark(Enum):
    OK = 1
    HAS_STARTED_MARK = 2
    NO_PAIR_TEACHER = 3
    IS_NO_TEACHER = 4
    ERROR = 5


class StatusMarkStudent(Enum):
    OK = 1
    ALREADY = 2
    ERROR = 3
    NO_STUDENT = 4
    NO_MARK = 5
    MORE_MARK  = 6
    NOT_YOUR_MARK = 7


class StatusAttendanceMark(Enum):
    OK = 1
    ALREADY = 2
    ERROR = 3


class StatusLoadExcel(Enum):
    OK = 1
    NO_DATA = 2
    ERROR = 3


class StatusValidCountStudent(Enum):
    OK = 1
    OVER = 2
    EQUALLY = 3
    NO_DATA = 4

class StatusInviteLink(Enum):
    OK = 1
    ALREADY_TG = 2
    NOT_FOUND = 3