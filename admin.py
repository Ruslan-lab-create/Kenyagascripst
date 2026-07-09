import logging
from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext

import database as db
import keyboards as kb
import trafsly_api
from config import ADMIN_IDS
from states import CreateScript

logger = logging.getLogger(__name__)
router = Router()


def _is_admin(user_id: int) -> bool:
    return user_id in ADMIN_IDS


@router.message(Command("admin"))
async def admin_menu(message: Message) -> None:
    if not _is_admin(message.from_user.id):
        return  # молча игнорируем, чтобы не палить наличие админки посторонним
    await message.answer(
        "🛠 Админ-панель\n\nВыбери действие:",
        reply_markup=kb.admin_main_menu(),
    )


@router.callback_query(F.data == "admin:menu")
async def admin_menu_cb(call: CallbackQuery, state: FSMContext) -> None:
    if not _is_admin(call.from_user.id):
        return await call.answer()
    await state.clear()
    await call.message.edit_text("🛠 Админ-панель\n\nВыбери действие:", reply_markup=kb.admin_main_menu())
    await call.answer()


# ---------- Создание скрипта ----------

@router.callback_query(F.data == "admin:create")
async def create_start(call: CallbackQuery, state: FSMContext) -> None:
    if not _is_admin(call.from_user.id):
        return await call.answer()
    await state.set_state(CreateScript.waiting_title)
    await call.message.edit_text("Введи название скрипта (для себя, юзеры его не увидят):")
    await call.answer()


@router.message(CreateScript.waiting_title)
async def create_title(message: Message, state: FSMContext) -> None:
    if not _is_admin(message.from_user.id):
        return
    title = (message.text or "").strip()
    if not title:
        await message.answer("Название не может быть пустым. Введи ещё раз:")
        return
    await state.update_data(title=title)
    await state.set_state(CreateScript.waiting_content)
    await message.answer(
        "Теперь пришли сам Lua-скрипт (текстом). "
        "Можно с loadstring/require, форматирование сохранится как есть."
    )


@router.message(CreateScript.waiting_content)
async def create_content(message: Message, state: FSMContext) -> None:
    if not _is_admin(message.from_user.id):
        return
    content = message.text or message.caption
    if not content:
        await message.answer("Не вижу текста скрипта. Пришли его текстовым сообщением:")
        return
    data = await state.get_data()
    title = data["title"]
    code = await db.create_script(title=title, content=content, created_by=message.from_user.id)
    await state.clear()

    link = kb.short_link_for(code)
    await message.answer(
        f"✅ Скрипт «{title}» создан.\n\n"
        f"Короткая ссылка:\n{link}\n\n"
        f"Переходя по ней, пользователь сначала выполнит спонсорские задания Trafsly, "
        f"а затем получит текст скрипта.",
        reply_markup=kb.admin_main_menu(),
    )


# ---------- Список / просмотр / удаление ----------

@router.callback_query(F.data == "admin:list")
async def list_scripts_cb(call: CallbackQuery) -> None:
    if not _is_admin(call.from_user.id):
        return await call.answer()
    scripts = await db.list_scripts()
    if not scripts:
        await call.message.edit_text(
            "Скриптов пока нет.", reply_markup=kb.admin_main_menu()
        )
        return await call.answer()
    await call.message.edit_text(
        "📋 Твои скрипты:", reply_markup=kb.scripts_list_kb(scripts)
    )
    await call.answer()


@router.callback_query(F.data.startswith("admin:view:"))
async def view_script_cb(call: CallbackQuery) -> None:
    if not _is_admin(call.from_user.id):
        return await call.answer()
    code = call.data.split(":", 2)[2]
    script = await db.get_script(code)
    if not script:
        await call.answer("Скрипт не найден, возможно уже удалён", show_alert=True)
        return
    link = kb.short_link_for(code)
    preview = script["content"][:500]
    more = "…" if len(script["content"]) > 500 else ""
    text = (
        f"📄 {script['title']}\n\n"
        f"Ссылка: {link}\n"
        f"Переходов: {script['clicks']} | Разблокировок: {script['unlocks']}\n\n"
        f"Превью скрипта:\n<code>{preview}{more}</code>"
    )
    await call.message.edit_text(text, reply_markup=kb.script_view_kb(code), parse_mode="HTML")
    await call.answer()


@router.callback_query(F.data.startswith("admin:delete:"))
async def delete_script_cb(call: CallbackQuery) -> None:
    if not _is_admin(call.from_user.id):
        return await call.answer()
    code = call.data.split(":", 2)[2]
    ok = await db.delete_script(code)
    await call.answer("Удалено" if ok else "Не найдено", show_alert=True)
    scripts = await db.list_scripts()
    if scripts:
        await call.message.edit_text("📋 Твои скрипты:", reply_markup=kb.scripts_list_kb(scripts))
    else:
        await call.message.edit_text("Скриптов пока нет.", reply_markup=kb.admin_main_menu())


# ---------- Баланс Trafsly ----------

@router.callback_query(F.data == "admin:balance")
async def balance_cb(call: CallbackQuery) -> None:
    if not _is_admin(call.from_user.id):
        return await call.answer()
    try:
        data = await trafsly_api.get_balance()
    except trafsly_api.TrafslyError as e:
        logger.warning("balance error: %s", e)
        await call.answer("Не удалось получить баланс. Проверь TRAFSLY_TOKEN в .env", show_alert=True)
        return
    text = (
        f"💰 Баланс: {data.get('balance', 0)} ₽\n"
        f"⏳ В холде: {data.get('hold_balance', 0)} ₽\n"
    )
    await call.message.edit_text(text, reply_markup=kb.admin_main_menu())
    await call.answer()
