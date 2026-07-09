import secrets
import string
import json
import time
import aiosqlite

from config import DB_PATH

_ALPHABET = string.ascii_letters + string.digits


def _gen_code(length: int = 8) -> str:
    return "".join(secrets.choice(_ALPHABET) for _ in range(length))


async def init_db() -> None:
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            """
            CREATE TABLE IF NOT EXISTS scripts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                code TEXT UNIQUE NOT NULL,
                title TEXT NOT NULL,
                content TEXT NOT NULL,
                created_by INTEGER NOT NULL,
                created_at INTEGER NOT NULL,
                clicks INTEGER NOT NULL DEFAULT 0,
                unlocks INTEGER NOT NULL DEFAULT 0
            )
            """
        )
        # Хранит для каждого (user_id, script_code) список ads_id, которые ещё
        # не подтверждены, чтобы кнопка "Я подписался" знала, что перепроверять.
        await db.execute(
            """
            CREATE TABLE IF NOT EXISTS pending_checks (
                user_id INTEGER NOT NULL,
                script_code TEXT NOT NULL,
                sponsors_json TEXT NOT NULL,
                PRIMARY KEY (user_id, script_code)
            )
            """
        )
        await db.commit()


async def create_script(title: str, content: str, created_by: int) -> str:
    code = _gen_code()
    async with aiosqlite.connect(DB_PATH) as db:
        # на случай коллизии (маловероятной) генерируем заново
        while True:
            cur = await db.execute("SELECT 1 FROM scripts WHERE code = ?", (code,))
            if await cur.fetchone() is None:
                break
            code = _gen_code()
        await db.execute(
            "INSERT INTO scripts (code, title, content, created_by, created_at) VALUES (?, ?, ?, ?, ?)",
            (code, title, content, created_by, int(time.time())),
        )
        await db.commit()
    return code


async def get_script(code: str):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute("SELECT * FROM scripts WHERE code = ?", (code,))
        row = await cur.fetchone()
        return dict(row) if row else None


async def list_scripts(created_by: int | None = None, limit: int = 20):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        if created_by is None:
            cur = await db.execute(
                "SELECT * FROM scripts ORDER BY id DESC LIMIT ?", (limit,)
            )
        else:
            cur = await db.execute(
                "SELECT * FROM scripts WHERE created_by = ? ORDER BY id DESC LIMIT ?",
                (created_by, limit),
            )
        rows = await cur.fetchall()
        return [dict(r) for r in rows]


async def delete_script(code: str) -> bool:
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute("DELETE FROM scripts WHERE code = ?", (code,))
        await db.commit()
        return cur.rowcount > 0


async def bump_clicks(code: str) -> None:
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE scripts SET clicks = clicks + 1 WHERE code = ?", (code,))
        await db.commit()


async def bump_unlocks(code: str) -> None:
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE scripts SET unlocks = unlocks + 1 WHERE code = ?", (code,))
        await db.commit()


async def save_pending_sponsors(user_id: int, script_code: str, sponsors: list[dict]) -> None:
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT OR REPLACE INTO pending_checks (user_id, script_code, sponsors_json) VALUES (?, ?, ?)",
            (user_id, script_code, json.dumps(sponsors)),
        )
        await db.commit()


async def get_pending_sponsors(user_id: int, script_code: str) -> list[dict]:
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(
            "SELECT sponsors_json FROM pending_checks WHERE user_id = ? AND script_code = ?",
            (user_id, script_code),
        )
        row = await cur.fetchone()
        return json.loads(row[0]) if row else []


async def clear_pending_sponsors(user_id: int, script_code: str) -> None:
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "DELETE FROM pending_checks WHERE user_id = ? AND script_code = ?",
            (user_id, script_code),
        )
        await db.commit()
