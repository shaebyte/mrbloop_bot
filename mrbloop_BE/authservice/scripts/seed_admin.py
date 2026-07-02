"""
One-time CLI to bootstrap the first admin user.

Run inside the authservice container (or locally with the same env vars
available), since there's no admin yet to call POST /users:

    docker compose exec authservice python -m scripts.seed_admin
"""
import asyncio
import getpass
import sys

import aiomysql

from app.config import DB_HOST, DB_PORT, DB_USER, DB_PASSWORD, DB_NAME
from app.security import PasswordTooLong, hash_password


async def main() -> None:
    username = input("Admin username: ").strip()
    if not username:
        print("Username cannot be empty.")
        sys.exit(1)

    password = getpass.getpass("Admin password: ")
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
                "INSERT INTO auth_users (username, password_hash, role) VALUES (%s, %s, 'admin')",
                (username, password_hash),
            )
            await conn.commit()
    finally:
        conn.close()

    print(f"Admin user '{username}' created.")


if __name__ == "__main__":
    asyncio.run(main())
