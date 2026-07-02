import argparse

from app.core.database import SessionLocal
from app.models.account import Account
from app.services.playwright_session_service import PlaywrightSessionService


def parse_args():
    parser = argparse.ArgumentParser(
        description="Create a Reddit Playwright session for one account."
    )
    selector = parser.add_mutually_exclusive_group(required=True)
    selector.add_argument("--account-id", type=int)
    selector.add_argument("--handle")
    return parser.parse_args()


def load_account(db, account_id: int | None, handle: str | None):
    query = db.query(Account).filter(Account.platform == "reddit")

    if account_id is not None:
        return query.filter(Account.id == account_id).first()

    return query.filter(Account.handle == handle).first()


def main():
    args = parse_args()
    db = SessionLocal()

    try:
        account = load_account(
            db=db,
            account_id=args.account_id,
            handle=args.handle,
        )

        if not account:
            raise SystemExit("Reddit account not found.")

        session_path = PlaywrightSessionService(db=db).create_session(account)
        print(f"Saved Reddit session for {account.handle}: {session_path}")
    finally:
        db.close()


if __name__ == "__main__":
    main()
