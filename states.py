from aiogram.fsm.state import State, StatesGroup


class CreateScript(StatesGroup):
    waiting_title = State()
    waiting_content = State()
