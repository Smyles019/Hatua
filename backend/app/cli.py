"""Command-line tasks, run from backend/.

    python -m app.cli create-admin --name "Jane Admin" --email jane@example.com --phone 0712345678
    python -m app.cli add-test-emails

create-admin prompts for the password, so it never appears in the shell history. The
first administrator has to be created this way; after that, administrators create other
accounts through /admin/users.

add-test-emails is for development databases made before email sign-in: it gives every
account without an email a placeholder one (caregiver1@hatua.test, chw1@hatua.test, ...)
so it can sign in again, and prints the list. The passwords do not change.
"""
import argparse
import getpass
import sys

from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.core.security import hash_password
from app.db.models import User
from app.db.session import SessionLocal
from app.schemas.users import NewUser


def create_admin(name: str, email: str, phone: str, password: str) -> User:
    body = NewUser(full_name=name, email=email, phone_number=phone, password=password,
                   role="admin")
    with SessionLocal() as db:
        user = User(full_name=body.full_name, email=body.email,
                    phone_number=body.phone_number, email_verified=True,
                    password_hash=hash_password(body.password), role="admin")
        db.add(user)
        db.commit()
        return user


def add_test_emails(session_factory=SessionLocal) -> list[tuple[str, str, str]]:
    """Returns (email, role, full name) for each account that was given an email."""
    done = []
    with session_factory() as db:
        taken = set(db.scalars(select(User.email).where(User.email.is_not(None))))
        counters: dict[str, int] = {}
        for user in db.scalars(select(User).where(User.email.is_(None))
                               .order_by(User.created_at)):
            while True:
                counters[user.role] = counters.get(user.role, 0) + 1
                email = f"{user.role}{counters[user.role]}@hatua.test"
                if email not in taken:
                    break
            taken.add(email)
            user.email, user.email_verified = email, True
            done.append((email, user.role, user.full_name))
        db.commit()
    return done


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(prog="python -m app.cli")
    sub = parser.add_subparsers(dest="command", required=True)
    p = sub.add_parser("create-admin", help="create an administrator account")
    p.add_argument("--name", required=True)
    p.add_argument("--email", required=True)
    p.add_argument("--phone", required=True)
    sub.add_parser("add-test-emails",
                   help="development: give accounts without an email a placeholder one")
    args = parser.parse_args(argv)

    if args.command == "add-test-emails":
        done = add_test_emails()
        for email, role, name in done:
            print(f"{email:28} {role:10} {name}")
        print(f"{len(done)} account(s) updated")
        return 0

    password = getpass.getpass("Password (at least 6 characters): ")
    if password != getpass.getpass("Repeat password: "):
        print("passwords do not match", file=sys.stderr)
        return 1
    try:
        user = create_admin(args.name, args.email, args.phone, password)
    except ValidationError as e:
        print("; ".join(err["msg"] for err in e.errors()), file=sys.stderr)
        return 1
    except IntegrityError:
        print("an account with this email or phone number already exists", file=sys.stderr)
        return 1
    print(f"administrator {user.full_name} ({user.email}) created")
    return 0


if __name__ == "__main__":
    sys.exit(main())
