"""Command-line tasks, run from backend/.

    python -m app.cli create-admin --name "Jane Admin" --phone 0712345678

Prompts for the password, so it never appears in the shell history. The first
administrator has to be created this way; after that, administrators create other
accounts through /admin/users.
"""
import argparse
import getpass
import sys

from pydantic import ValidationError
from sqlalchemy.exc import IntegrityError

from app.core.security import hash_password
from app.db.models import User
from app.db.session import SessionLocal
from app.schemas.users import NewUser


def create_admin(name: str, phone: str, password: str) -> User:
    body = NewUser(full_name=name, phone_number=phone, password=password, role="admin")
    with SessionLocal() as db:
        user = User(full_name=body.full_name, phone_number=body.phone_number,
                    password_hash=hash_password(body.password), role="admin")
        db.add(user)
        db.commit()
        return user


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(prog="python -m app.cli")
    sub = parser.add_subparsers(dest="command", required=True)
    p = sub.add_parser("create-admin", help="create an administrator account")
    p.add_argument("--name", required=True)
    p.add_argument("--phone", required=True)
    args = parser.parse_args(argv)

    password = getpass.getpass("Password (at least 6 characters): ")
    if password != getpass.getpass("Repeat password: "):
        print("passwords do not match", file=sys.stderr)
        return 1
    try:
        user = create_admin(args.name, args.phone, password)
    except ValidationError as e:
        print("; ".join(err["msg"] for err in e.errors()), file=sys.stderr)
        return 1
    except IntegrityError:
        print("an account with this phone number already exists", file=sys.stderr)
        return 1
    print(f"administrator {user.full_name} ({user.phone_number}) created")
    return 0


if __name__ == "__main__":
    sys.exit(main())
