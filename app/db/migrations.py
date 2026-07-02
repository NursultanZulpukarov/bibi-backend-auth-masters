from sqlalchemy import text

from app.db.session import engine

MIGRATIONS = [
    "ALTER TABLE masters ADD COLUMN IF NOT EXISTS user_id INTEGER "
    "REFERENCES users(id) ON DELETE SET NULL",
    "UPDATE masters m SET user_id = u.id "
    "FROM users u "
    "WHERE m.username = u.username AND u.role = 'master' AND m.user_id IS NULL",
    "CREATE UNIQUE INDEX IF NOT EXISTS ix_masters_user_id_unique "
    "ON masters(user_id) WHERE user_id IS NOT NULL",
    "ALTER TABLE users ALTER COLUMN role SET DEFAULT 'client'",
    "UPDATE users SET role = 'client' WHERE role IS NULL",
    "ALTER TABLE users ALTER COLUMN role SET NOT NULL",
]


async def run_migrations() -> None:
    async with engine.begin() as conn:
        for statement in MIGRATIONS:
            await conn.execute(text(statement))
