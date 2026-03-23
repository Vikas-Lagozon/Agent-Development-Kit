from passlib.context import CryptContext

_pwd_ctx = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(plain_password: str) -> str:
    """Hashes a password using bcrypt."""
    return _pwd_ctx.hash(plain_password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verifies a password against a bcrypt hash."""
    try:
        return _pwd_ctx.verify(plain_password, hashed_password)
    except Exception:
        return False
