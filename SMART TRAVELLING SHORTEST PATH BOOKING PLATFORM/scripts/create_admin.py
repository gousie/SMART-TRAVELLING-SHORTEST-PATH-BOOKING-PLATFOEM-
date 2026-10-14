"""Create a non-demo administrator on a fresh database using an interactive password."""

import argparse
import getpass
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from railora.config import settings  # noqa: E402
from railora.db import Database  # noqa: E402
from railora.models import User  # noqa: E402
from railora.schemas import RegisterInput  # noqa: E402
from railora.services import AuthService  # noqa: E402


def main():
    parser = argparse.ArgumentParser(description="Create a new administrator (does not promote existing accounts).")
    parser.add_argument("--email", required=True)
    parser.add_argument("--name", required=True)
    args = parser.parse_args()
    password = getpass.getpass("New administrator password (8+ characters): ")
    if password != getpass.getpass("Repeat password: "):
        raise SystemExit("Passwords do not match.")
    request = RegisterInput(name=args.name, email=args.email, password=password)
    db = Database(settings.database_url)
    db.create_schema()
    auth = AuthService(db)
    token, user = auth.register(request)
    auth.logout(token)
    with db.transaction() as session:
        account = session.get(User, user["id"])
        if account is None:
            raise SystemExit("Account creation failed.")
        account.role = "admin"
    print(f"Administrator {user['email']} created. No plaintext password was stored.")
    db.engine.dispose()


if __name__ == "__main__":
    main()
