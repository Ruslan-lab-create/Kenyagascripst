import logging
import httpx

from config import TRAFSLY_TOKEN, TRAFSLY_BASE_URL

logger = logging.getLogger(__name__)

_HEADERS = {"Auth": TRAFSLY_TOKEN, "Content-Type": "application/json"}
_TIMEOUT = httpx.Timeout(10.0)


class TrafslyError(Exception):
    pass


async def get_sponsors(
    user_id: int,
    first_name: str | None = None,
    username: str | None = None,
    language_code: str | None = None,
    is_premium: bool = False,
    max_sponsors: int = 5,
) -> list[dict]:
    """
    Возвращает список невыполненных спонсорских заданий для юзера.
    Пустой список — заданий нет, можно пускать дальше.
    """
    payload = {
        "user_id": user_id,
        "max_sponsors": max_sponsors,
        "is_premium": is_premium,
        "action": "subscribe",
    }
    if first_name:
        payload["first_name"] = first_name
    if username:
        payload["username"] = username
    if language_code:
        payload["language_code"] = language_code

    async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
        try:
            resp = await client.post(
                f"{TRAFSLY_BASE_URL}/api/v1/get-sponsors",
                headers=_HEADERS,
                json=payload,
            )
        except httpx.HTTPError as e:
            logger.exception("Trafsly get-sponsors network error")
            raise TrafslyError(f"network error: {e}") from e

    if resp.status_code != 200:
        logger.warning("Trafsly get-sponsors HTTP %s: %s", resp.status_code, resp.text)
        # Фейлимся мягко: если сервис недоступен, лучше не блокировать юзера намертво.
        raise TrafslyError(f"HTTP {resp.status_code}: {resp.text}")

    data = resp.json()
    sponsors = data.get("sponsors", [])
    logger.info("Trafsly get-sponsors raw response for user %s: %s", user_id, data)
    return sponsors


async def confirm_subscription(user_id: int, ads_id: int) -> dict:
    """
    Проверяет, подписался ли юзер на конкретное задание.
    Возвращает {"subscribed": bool, "credited": float|None}
    """
    async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
        try:
            resp = await client.post(
                f"{TRAFSLY_BASE_URL}/api/v1/confirm-subscription",
                headers=_HEADERS,
                json={"user_id": user_id, "ads_id": ads_id},
            )
        except httpx.HTTPError as e:
            logger.exception("Trafsly confirm-subscription network error")
            raise TrafslyError(f"network error: {e}") from e

    if resp.status_code != 200:
        logger.warning("Trafsly confirm-subscription HTTP %s: %s", resp.status_code, resp.text)
        raise TrafslyError(f"HTTP {resp.status_code}: {resp.text}")

    data = resp.json()
    return {
        "subscribed": bool(data.get("subscribed", False)),
        "credited": data.get("credited"),
    }


async def get_balance() -> dict:
    async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
        resp = await client.post(f"{TRAFSLY_BASE_URL}/api/v1/get-balance", headers=_HEADERS)
    if resp.status_code != 200:
        raise TrafslyError(f"HTTP {resp.status_code}: {resp.text}")
    return resp.json()
