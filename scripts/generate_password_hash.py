from auth import hash_password
import sys

if len(sys.argv) < 2:
    print("Usage: python generate_password_hash.py <password>")
    sys.exit(1)

pwd = sys.argv[1]
print(hash_password(pwd))
