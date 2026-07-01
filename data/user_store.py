import uuid
from typing import List, Optional
from models import User
from .base_store import BaseStore

class UserStore:
    def __init__(self, base: BaseStore):
        self.base = base

    def create_user(self, user: User) -> User:
        audit = self.base._get_audit_fields()
        user.modified_by = audit["modified_by"]
        user.modified_at = audit["modified_at"]
        if self.base.client:
            from google.cloud import datastore
            key = self.base.client.key("User", user.id)
            entity = datastore.Entity(key=key)
            entity.update(vars(user))
            self.base.client.put(entity)
            return user
        
        self.base.users[user.id] = user
        self.base.save_local_data()
        return user

    def add_user(self, username: str, password_hash: str, is_admin: bool = False) -> User:
        uid = str(uuid.uuid4())
        u = User(id=uid, username=username, password_hash=password_hash, is_admin=is_admin, original_username=username)
        return self.create_user(u)

    def update_user(self, uid: str, **fields) -> Optional[User]:
        audit = self.base._get_audit_fields()
        if self.base.client:
            try:
                key = self.base.client.key("User", int(uid))
            except Exception:
                key = self.base.client.key("User", uid)
            entity = self.base.client.get(key)
            if not entity:
                return None
            for k, v in fields.items():
                entity[k] = v
            entity.update(audit)
            self.base.client.put(entity)
            return User(
                id=str(entity.key.id or entity.key.name), 
                username=entity.get("username"),
                password_hash=entity.get("password_hash"),
                is_admin=entity.get("is_admin", False),
                original_username=entity.get("original_username", entity.get("username")),
                modified_by=entity.get("modified_by"),
                modified_at=entity.get("modified_at")
            )

        u = self.base.users.get(uid)
        if not u:
            return None
        for k, v in fields.items():
            if hasattr(u, k):
                setattr(u, k, v)
        u.modified_by = audit["modified_by"]
        u.modified_at = audit["modified_at"]
        self.base.save_local_data()
        return u

    def delete_user(self, uid: str) -> bool:
        if self.base.client:
            try:
                key = self.base.client.key("User", int(uid))
            except Exception:
                key = self.base.client.key("User", uid)
            try:
                self.base.client.delete(key)
                return True
            except Exception:
                return False
        res = self.base.users.pop(uid, None) is not None
        self.base.save_local_data()
        return res

    def list_users(self) -> List[User]:
        if self.base.client:
            query = self.base.client.query(kind="User")
            res = list(query.fetch())
            return [User(
                id=str(e.key.id or e.key.name), 
                username=e.get("username"),
                password_hash=e.get("password_hash"),
                is_admin=e.get("is_admin", False),
                original_username=e.get("original_username", e.get("username")),
                modified_by=e.get("modified_by"),
                modified_at=e.get("modified_at")
            ) for e in res]
        return list(self.base.users.values())

    def get_user_by_username(self, username: str) -> Optional[User]:
        if self.base.client:
            query = self.base.client.query(kind="User")
            query.add_filter("username", "=", username)
            res = list(query.fetch(limit=1))
            return self.update_user(str(res[0].key.id or res[0].key.name)) if res else None
        return next((u for u in self.base.users.values() if u.username == username), None)
