"""
CLI to create an 'alliance' role user directly against the DB, without
needing a running authservice + an existing admin JWT to call POST /users.

Run inside the authservice container (or locally with the same env vars
available):

    docker compose exec authservice python -m scripts.seed_alliance
"""
import asyncio
import getpass
import sys

import aiomysql

from app.config import DB_HOST, DB_PORT, DB_USER, DB_PASSWORD, DB_NAME
from app.security import PasswordTooLong, hash_password


async def main() -> None:
    username = input("Alliance username: ").strip()
    if not username:
        print("Username cannot be empty.")
        sys.exit(1)

    password = getpass.getpass("Alliance password: ")
    if not password:
        print("Password cannot be empty.")
        sys.exit(1)

    try:
        password_hash = hash_password(password)
    except PasswordTooLong as e:
        print(str(e))
        sys.exit(1)

    conn = await aiomysql.connect(
        host=DB_HOST, port=DB_PORT, user=DB_USER, password=DB_PASSWORD, db=DB_NAME
    )
    try:
        async with conn.cursor() as cur:
            await cur.execute(
                "SELECT id FROM auth_users WHERE username = %s", (username,)
            )
            if await cur.fetchone():
                print(f"Username '{username}' already exists.")
                sys.exit(1)

            await cur.execute(
                "INSERT INTO auth_users (username, password_hash, role) VALUES (%s, %s, 'alliance')",
                (username, password_hash),
            )
            await conn.commit()
    finally:
        conn.close()

    print(f"Alliance user '{username}' created.")


if __name__ == "__main__":
    asyncio.run(main())
