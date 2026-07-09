import logging
from aiogram import Router, F
from aiogram.filters import CommandStart, CommandObject
from aiogram.types import Message, CallbackQuery

import database as db
import keyboards as kb
import trafsly_api

logger = logging.getLogger(__name__)
router = Router()


async def _send_script(message_or_call, script: dict) -> None:
    await db.bump_unlocks(script["code"])
    text = (
        f"✅ Готово! Вот твой скрипт «{script['title']}»:\n\n"
        f"<code>{script['content']}</code>"
    )
    target = message_or_call.message if isinstance(message_or_call, CallbackQuery) else message_or_call
    # Telegram режет сообщения на 4096 символов — на всякий случай подрежем и предупредим.
    if len(text) > 4000:
        await target.answer(
            "⚠️ Скрипт слишком длинный для одного сообщения, отправляю файлом ниже, "
            "либо обратись к автору бота."
        )
        text = text[:4000] + "…</code>"
    await target.answer(text, parse_mode="HTML")


async def _request_sponsors_and_show(message: Message, script_code: str) -> bool:
    """Возвращает True, если пользователя можно пускать дальше без заданий."""
    user = message.from_user
    try:
        sponsors = await trafsly_api.get_sponsors(
            user_id=user.id,
            first_name=user.first_name,
            username=user.username,
            language_code=user.language_code,
            is_premium=bool(getattr(user, "is_premium", False)),
        )
    except trafsly_api.TrafslyError as e:
        logger.warning("get_sponsors failed, letting user through: %s", e)
        # Сервис недоступен — не блокируем пользователя намертво.
        return True

    if not sponsors:
        return True

    await db.save_pending_sponsors(user.id, script_code, sponsors)
    await message.answer(
        "Чтобы получить скрипт, подпишись на спонсоров ниже, "
        "а затем нажми «Я подписался»:",
        reply_markup=kb.sponsors_kb(sponsors, script_code),
    )
    return False


@router.message(CommandStart())
async def start_handler(message: Message, command: CommandObject) -> None:
    payload = (command.args or "").strip()
    if not payload:
        await message.answer(
            "Привет! Я бот со скриптами для Roblox 👋\n"
            "Чтобы получить скрипт, перейди по ссылке, которую тебе прислали."
        )
        return

    script = await db.get_script(payload)
    if not script:
        await message.answer("Эта ссылка недействительна или скрипт был удалён 😕")
        return

    await db.bump_clicks(payload)
    can_proceed = await _request_sponsors_and_show(message, payload)
    if can_proceed:
        await _send_script(message, script)


@router.callback_query(F.data.startswith("check:"))
async def check_subscription_cb(call: CallbackQuery) -> None:
    script_code = call.data.split(":", 1)[1]
    user_id = call.from_user.id

    script = await db.get_script(script_code)
    if not script:
        await call.answer("Скрипт больше не доступен", show_alert=True)
        return

    pending = await db.get_pending_sponsors(user_id, script_code)
    if not pending:
        # Сессии нет — перезапросим задания на всякий случай
        can_proceed = await _request_sponsors_and_show(call.message, script_code)
        await call.answer()
        if can_proceed:
            await _send_script(call, script)
        return

    still_pending = []
    for sp in pending:
        try:
            result = await trafsly_api.confirm_subscription(user_id, sp["ads_id"])
        except trafsly_api.TrafslyError as e:
            logger.warning("confirm_subscription failed: %s", e)
            still_pending.append(sp)
            continue
        if not result["subscribed"]:
            still_pending.append(sp)

    if still_pending:
        await db.save_pending_sponsors(user_id, script_code, still_pending)
        await call.answer("Похоже, подписался не на всё. Проверь ещё раз ⤴️", show_alert=True)
        await call.message.edit_reply_markup(reply_markup=kb.sponsors_kb(still_pending, script_code))
        return

    await db.clear_pending_sponsors(user_id, script_code)
    await call.answer("Все подписки подтверждены ✅")
    await call.message.edit_text("✅ Все задания выполнены!")
    await _send_script(call, script)
