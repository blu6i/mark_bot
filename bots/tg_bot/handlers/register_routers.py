from aiogram import Router

from .help_msg import help_msg_router
from .started_cmd import started_router
from .teachers.start_mark import start_mark_router
from .students.mark import mark_students_router
from .teachers.print_excel_mark import print_excel_marks_router
from .admins.generate_invite_link import generate_invite_link_router
from .admins.parser_schedule import parser_router
from .admins.settings_list import settings_list_router

def register_router() -> Router:
    main_router = Router()
    main_router.include_router(started_router)
    main_router.include_router(start_mark_router)
    main_router.include_router(mark_students_router)
    main_router.include_router(print_excel_marks_router)
    main_router.include_router(generate_invite_link_router)
    main_router.include_router(help_msg_router)
    main_router.include_router(parser_router)
    main_router.include_router(settings_list_router)
    return main_router