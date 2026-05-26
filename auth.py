import os
try:
    import bcrypt
    _HAS_BCRYPT = True
except Exception:
    import hashlib
    _HAS_BCRYPT = False

def hash_password(plain: str) -> str:
    if _HAS_BCRYPT:
        return bcrypt.hashpw(plain.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    else:
        return hashlib.sha256(plain.encode('utf-8')).hexdigest()

def check_password(plain: str, stored: str) -> bool:
    if _HAS_BCRYPT:
        try:
            return bcrypt.checkpw(plain.encode('utf-8'), stored.encode('utf-8'))
        except Exception:
            return False
    else:
        return hashlib.sha256(plain.encode('utf-8')).hexdigest() == stored
