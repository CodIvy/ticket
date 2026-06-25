import bcrypt

def hash_password(password: str, rounds: int = 12) -> str:
    password_bytes = password.encode('utf-8')
    salt = bcrypt.gensalt(rounds=rounds)
    return bcrypt.hashpw(password_bytes, salt).decode('utf-8')

def verify_password(plain_password: str, hashed_password: str) -> bool:
    try:
        return bcrypt.checkpw(
            plain_password.encode('utf-8'),
            hashed_password.encode('utf-8')
        )
    except ValueError:
        return False