from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder

from config import BOT_USERNAME


def admin_main_menu() -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text="➕ Создать скрипт", callback_data="admin:create")
    kb.button(text="📋 Мои скрипты", callback_data="admin:list")
    kb.button(text="💰 Баланс Trafsly", callback_data="admin:balance")
    kb.adjust(1)
    return kb.as_markup()


def scripts_list_kb(scripts: list[dict]) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    for s in scripts:
        kb.button(text=f"📄 {s['title']}", callback_data=f"admin:view:{s['code']}")
    kb.button(text="⬅️ Назад", callback_data="admin:menu")
    kb.adjust(1)
    return kb.as_markup()


def script_view_kb(code: str) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text="🗑 Удалить", callback_data=f"admin:delete:{code}")
    kb.button(text="⬅️ К списку", callback_data="admin:list")
    kb.adjust(1)
    return kb.as_markup()


def short_link_for(code: str) -> str:
    return f"https://t.me/{BOT_USERNAME}?start={code}"


def sponsors_kb(sponsors: list[dict], script_code: str) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    for sp in sponsors:
        kb.button(text=f"📢 {sp['title']}", url=sp["link"])
    kb.button(text="✅ Я подписался", callback_data=f"check:{script_code}")
    kb.adjust(1)
    return kb.as_markup()
