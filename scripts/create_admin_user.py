import uuid
import getpass
from datastore_client import get_client
from models import User
from auth import hash_password
from utils import validate_password

def main():
    print("--- Pauper Monaco: Admin User Creation ---")
    
    # Get user input
    username = input("Enter Username: ").strip()
    if not username:
        print("Error: Username cannot be empty.")
        return
        
    # Secure password entry (input is hidden)
    password = getpass.getpass("Enter Password: ")
    confirm = getpass.getpass("Confirm Password: ")
    
    is_valid, error_msg = validate_password(password, confirm)
    if not is_valid:
        print(f"Error: {error_msg}")
        return

    # Hash the password using the logic in auth.py
    hashed_pw = hash_password(password)
    
    # Create the User object
    new_user = User(
        id=str(uuid.uuid4()),
        username=username,
        password_hash=hashed_pw,
        is_admin=True,
        original_username=username
    )
    
    client = get_client()
    # This assumes your datastore_client has a create_user or save_user method
    client.create_user(new_user)
    print(f"\n✅ Successfully created Admin user: {username}")

if __name__ == "__main__":
    main()
