from typing import Dict, List, Optional
from models import User, Match, Deck, League, LeaguePlayer, Round, Game
from data.base_store import BaseStore
from data.user_store import UserStore
from data.deck_store import DeckStore
from data.league_store import LeagueStore
from data.match_store import MatchStore

class DatastoreClient:
    def __init__(self):
        self.base = BaseStore()
        self.user_store = UserStore(self.base)
        self.deck_store = DeckStore(self.base)
        self.league_store = LeagueStore(self.base)
        self.match_store = MatchStore(self.base)

    @property
    def client(self):
        return self.base.client

    # --- User methods ---
    def create_user(self, user: User) -> User:
        return self.user_store.create_user(user)

    def add_user(self, username: str, password_hash: str, is_admin: bool = False) -> User:
        return self.user_store.add_user(username, password_hash, is_admin)

    def update_user(self, uid: str, **fields) -> Optional[User]:
        return self.user_store.update_user(uid, **fields)

    def delete_user(self, uid: str) -> bool:
        return self.user_store.delete_user(uid)

    def list_users(self) -> List[User]:
        return self.user_store.list_users()

    def get_user_by_username(self, username: str) -> Optional[User]:
        return self.user_store.get_user_by_username(username)

    # Backward compatibility aliases
    def list_players(self) -> List[User]:
        return self.list_users()

    # --- Deck methods ---
    def add_deck(self, deck_name: str, deck_list_link: Optional[str] = None) -> Deck:
        return self.deck_store.add_deck(deck_name, deck_list_link)

    def list_decks(self) -> List[Deck]:
        return self.deck_store.list_decks()

    def update_deck(self, did: str, **fields) -> Optional[Deck]:
        return self.deck_store.update_deck(did, **fields)

    def delete_deck(self, did: str) -> bool:
        return self.deck_store.delete_deck(did)

    # --- League methods ---
    def add_league(self, nr: int, start_date: str, weeks_rounds: int, weeks_playoffs: int, end_date: str, league_name: str = "") -> League:
        return self.league_store.add_league(nr, start_date, weeks_rounds, weeks_playoffs, end_date, league_name)

    def list_leagues(self) -> List[League]:
        return self.league_store.list_leagues()

    def update_league(self, lid: str, **fields) -> Optional[League]:
        return self.league_store.update_league(lid, **fields)

    def delete_league(self, lid: str) -> bool:
        return self.league_store.delete_league(lid)

    # --- Round methods ---
    def add_round(self, league_id: str, nr: int, start_date: str, end_date: str) -> Round:
        return self.league_store.add_round(league_id, nr, start_date, end_date)

    def list_rounds(self, league_id: Optional[str] = None) -> List[Round]:
        return self.league_store.list_rounds(league_id)

    def delete_round(self, rid: str) -> bool:
        return self.league_store.delete_round(rid)

    # --- LeaguePlayer methods ---
    def add_user_to_league(self, league_id: str, user_id: str, deck_id: str) -> LeaguePlayer:
        return self.league_store.add_user_to_league(league_id, user_id, deck_id)

    def list_league_players(self, league_id: Optional[str] = None) -> List[LeaguePlayer]:
        return self.league_store.list_league_players(league_id)

    def update_league_player(self, lp_id: str, **fields) -> bool:
        return self.league_store.update_league_player(lp_id, **fields)

    def remove_player_from_league(self, lp_id: str) -> bool:
        return self.league_store.remove_player_from_league(lp_id)

    # --- Match methods ---
    def add_match(self, player_a: str, player_b: str, round_id: str, starting_player: Optional[str], games: List[Dict], went_in_time: bool = False, match_type: str = "Round") -> Match:
        return self.match_store.add_match(player_a, player_b, round_id, starting_player, games, went_in_time, match_type)

    def update_match(self, mid: str, **fields) -> Optional[Match]:
        return self.match_store.update_match(mid, **fields)

    def list_matches(self) -> List[Match]:
        return self.match_store.list_matches()

    def delete_match(self, mid: str) -> bool:
        return self.match_store.delete_match(mid)


# Singleton instance for simple use in app
_ds = None


def get_client() -> DatastoreClient:
    global _ds
    if _ds is None:
        _ds = DatastoreClient()
    return _ds
