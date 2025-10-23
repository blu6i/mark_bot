from enum import Enum

class TeacherAuthStatus(Enum):
    OK = 1
    TIMEOUT = 2

class StudentAuthStatus(Enum):
    OK = 1
    BUSY_USER = 2
    INVALID_USER = 3

class TeacherRegistrationStatus(Enum):
    OK = 1
    NOT_FOUND = 2
    ALREADY_TG = 3

class MarkStudentStatus(Enum):
    OK = 1
    MORE_MARK = 2
    NO_STUDENT = 3
    NO_MARK = 4


class RunMarkStatus(Enum):
    OK = 1
    HAS_STARTED_MARK = 2
    NO_PAIR_TEACHER = 3
    IS_NO_TEACHER = 4

class AccessRights(Enum):
    ADMINS = 1
    TEACHER = 2
    STUDENT = 3


class AttendanceStudent(Enum):
    OK = 1
    ALREADY = 2
    ERROR=3

class StatusLoadExcel(Enum):
    OK = 1
    NO_DATA = 2
    ERROR = 3

class StatusValidCountStudent(Enum):
    OK = 1
    OVER = 2
    NO_OVER = 3
    ERROR = 4
    EQUALLY = 5
    NO_DATA = 6