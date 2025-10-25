from aiogram import Router
from .started_cmd import started_router
from .teachers.start_mark import start_mark_router
from .students.mark import mark_students_router

def register_router() -> Router:
    main_router = Router()
    main_router.include_router(started_router)
    main_router.include_router(start_mark_router)
    main_router.include_router(mark_students_router)
    return main_router