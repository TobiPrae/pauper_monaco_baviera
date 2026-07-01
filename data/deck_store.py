import uuid
from typing import List, Optional
from models import Deck
from .base_store import BaseStore

class DeckStore:
    def __init__(self, base: BaseStore):
        self.base = base

    def add_deck(self, deck_name: str, deck_list_link: Optional[str] = None) -> Deck:
        audit = self.base._get_audit_fields()
        if self.base.client:
            from google.cloud import datastore
            key = self.base.client.key("Deck")
            entity = datastore.Entity(key=key)
            entity.update({"deck_name": deck_name, "deck_list_link": deck_list_link})
            entity.update(audit)
            self.base.client.put(entity)
            did = str(entity.key.id or entity.key.name)
            return Deck(id=did, deck_name=deck_name, deck_list_link=deck_list_link)

        did = str(uuid.uuid4())
        d = Deck(id=did, deck_name=deck_name, deck_list_link=deck_list_link)
        d.modified_by = audit["modified_by"]
        d.modified_at = audit["modified_at"]
        self.base.decks[did] = d
        self.base.save_local_data()
        return d

    def list_decks(self) -> List[Deck]:
        if self.base.client:
            query = self.base.client.query(kind="Deck")
            res = list(query.fetch())
            return [Deck(id=str(e.key.id or e.key.name), deck_name=e.get("deck_name"), deck_list_link=e.get("deck_list_link")) for e in res]
        return list(self.base.decks.values())

    def update_deck(self, did: str, **fields) -> Optional[Deck]:
        audit = self.base._get_audit_fields()
        if self.base.client:
            key = self.base.client.key("Deck", int(did) if did.isdigit() else did)
            entity = self.base.client.get(key)
            if not entity: return None
            entity.update(fields)
            entity.update(audit)
            self.base.client.put(entity)
            return Deck(id=did, deck_name=entity.get("deck_name"), deck_list_link=entity.get("deck_list_link"))
        
        d = self.base.decks.get(did)
        if not d: return None
        for k, v in fields.items():
            if hasattr(d, k): setattr(d, k, v)
        d.modified_by = audit["modified_by"]
        d.modified_at = audit["modified_at"]
        self.base.save_local_data()
        return d

    def delete_deck(self, did: str) -> bool:
        if self.base.client:
            try:
                key = self.base.client.key("Deck", int(did) if did.isdigit() else did)
            except Exception:
                key = self.base.client.key("Deck", did)
            self.base.client.delete(key)
            return True
        res = self.base.decks.pop(did, None) is not None
        self.base.save_local_data()
        return res
