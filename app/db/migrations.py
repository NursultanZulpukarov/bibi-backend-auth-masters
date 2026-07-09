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
    "ALTER TABLE reviews ADD COLUMN IF NOT EXISTS image_url TEXT",
    # None of these had any index beyond the primary key on id — every
    # "this master's services/posts/reviews" or "likes for these posts"
    # query was a full table scan. Fine at today's row counts, but cheap to
    # fix now rather than as a fire drill once the tables grow.
    "CREATE INDEX IF NOT EXISTS ix_services_master_id ON services(master_id)",
    "CREATE INDEX IF NOT EXISTS ix_reviews_master_id ON reviews(master_id)",
    "CREATE INDEX IF NOT EXISTS ix_posts_master_id ON posts(master_id)",
    "CREATE INDEX IF NOT EXISTS ix_post_likes_post_id ON post_likes(post_id)",
    "CREATE INDEX IF NOT EXISTS ix_post_saves_post_id ON post_saves(post_id)",
    # whatsapp_phone existed but was never populated at registration until
    # now — backfill existing masters from their linked account's phone so
    # the WhatsApp booking button isn't empty for accounts created earlier.
    "UPDATE masters m SET whatsapp_phone = u.phone "
    "FROM users u "
    "WHERE m.user_id = u.id AND m.whatsapp_phone IS NULL AND u.phone IS NOT NULL",
]


async def run_migrations() -> None:
    async with engine.begin() as conn:
        for statement in MIGRATIONS:
            await conn.execute(text(statement))
