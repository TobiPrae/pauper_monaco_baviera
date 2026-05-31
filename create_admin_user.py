import uuid
import getpass
from datastore_client import get_client
from models import User
from auth import hash_password

def main():
    print("--- Pauper Monaco: Admin User Creation ---")
    
    # Get user input
    username = input("Enter Username: ").strip()
    if not username:
        print("Error: Username cannot be empty.")
        return
        
    email = input("Enter Email: ").strip()
    
    # Secure password entry (input is hidden)
    password = getpass.getpass("Enter Password: ")
    confirm = getpass.getpass("Confirm Password: ")
    
    if password != confirm:
        print("Error: Passwords do not match.")
        return

    if len(password) < 4:
        print("Error: Password is too short.")
        return

    # Hash the password using the logic in auth.py
    hashed_pw = hash_password(password)
    
    # Create the User object
    new_user = User(
        id=str(uuid.uuid4()),
        username=username,
        email=email,
        password_hash=hashed_pw,
        is_admin=True
    )
    
    client = get_client()
    # This assumes your datastore_client has a create_user or save_user method
    client.create_user(new_user)
    print(f"\n✅ Successfully created Admin user: {username}")

if __name__ == "__main__":
    main()
