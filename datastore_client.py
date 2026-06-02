import os
import uuid
import time
import json
from typing import Dict, List, Optional
from models import User, Match, Deck, League, LeaguePlayer, Round, Game
import streamlit as st

# Choose backend: use real GCP Datastore if env indicates, otherwise in-memory fallback
service_account_info = dict(st.secrets["service_account_key"])
USE_GCP = os.environ.get("USE_GCP_DATASTORE") == "1" or service_account_info is not None
_gcloud_available = False
if USE_GCP:
    try:
        from google.cloud import datastore as _datastore
        _gcloud_available = True
    except Exception:
        _gcloud_available = False
        USE_GCP = False


class DatastoreClient:
    def __init__(self):
        if USE_GCP and _gcloud_available:
            self.client = _datastore.Client.from_service_account_info(service_account_info)
        else:
            self.client = None
            self.local_file = "local_datastore.json"
            self.users: Dict[str, User] = {}
            self.decks: Dict[str, Deck] = {}
            self.matches: Dict[str, Match] = {}
            self.leagues: Dict[str, League] = {}
            self.rounds: Dict[str, Round] = {}
            self.league_players: Dict[str, LeaguePlayer] = {}
            self._load_local_data()

    def _load_local_data(self):
        """Loads data from a local JSON file if it exists."""
        if USE_GCP:
            return

        if os.path.exists(self.local_file):
            try:
                with open(self.local_file, "r") as f:
                    data = json.load(f)
                    # Helper to restore User objects
                    for u in data.get("users", []):
                        # Filter attributes to match current User model
                        user_fields = {k: v for k, v in u.items() if k in ["id", "username", "password_hash", "is_admin", "original_username"]}
                        # Migration: If original_username is missing, use the current username
                        if "original_username" not in user_fields:
                            user_fields["original_username"] = user_fields.get("username", "")
                        self.users[u["id"]] = User(**user_fields)
                    # Restore other entities
                    for d in data.get("decks", []):
                        self.decks[d["id"]] = Deck(**d)
                    for l in data.get("leagues", []):
                        self.leagues[l["id"]] = League(**l)
                    for r in data.get("rounds", []):
                        self.rounds[r["id"]] = Round(**r)
                    for lp in data.get("league_players", []):
                        self.league_players[lp["id"]] = LeaguePlayer(**lp)
                    for m in data.get("matches", []):
                        # Matches need special handling for the list of Game objects
                        games_data = m.pop("games", [])
                        game_objs = [Game(**g) for g in games_data]
                        self.matches[m["id"]] = Match(games=game_objs, **m)
            except Exception as e:
                print(f"Warning: Could not load local data: {e}")

    def _save_local_data(self):
        """Saves current in-memory state to a local JSON file."""
        if USE_GCP or self.client is not None:
            return

        try:
            # Helper to convert objects to dicts, handling nested Game objects in Matches
            def match_to_dict(m):
                d = vars(m).copy()
                d["games"] = [vars(g) for g in m.games]
                return d

            data = {
                "users": [vars(u) for u in self.users.values()],
                "decks": [vars(d) for d in self.decks.values()],
                "leagues": [vars(l) for l in self.leagues.values()],
                "rounds": [vars(r) for r in self.rounds.values()],
                "league_players": [vars(lp) for lp in self.league_players.values()],
                "matches": [match_to_dict(m) for m in self.matches.values()]
            }
            with open(self.local_file, "w") as f:
                json.dump(data, f, indent=4)
        except Exception as e:
            print(f"Warning: Could not save local data: {e}")

    # --- User methods ---
    def create_user(self, user: User) -> User:
        """Used primarily by scripts and admin functions to save a User object."""
        if self.client:
            key = self.client.key("User", user.id)
            entity = _datastore.Entity(key=key)
            entity.update(vars(user))
            self.client.put(entity)
            return user
        
        self.users[user.id] = user
        self._save_local_data()
        return user

    def add_user(self, username: str, password_hash: str, is_admin: bool = False) -> User:
        uid = str(uuid.uuid4())
        u = User(id=uid, username=username, password_hash=password_hash, is_admin=is_admin, original_username=username)
        return self.create_user(u)

    def update_user(self, uid: str, **fields) -> Optional[User]:
        if self.client:
            # naive implementation: fetch by id
            try:
                key = self.client.key("User", int(uid))
            except Exception:
                key = self.client.key("User", uid)
            entity = self.client.get(key)
            if not entity:
                return None
            for k, v in fields.items():
                entity[k] = v
            self.client.put(entity)
            return User(
                id=str(entity.key.id or entity.key.name), 
                username=entity.get("username"),
                password_hash=entity.get("password_hash"),
                is_admin=entity.get("is_admin", False),
                original_username=entity.get("original_username", entity.get("username"))
            )

        u = self.users.get(uid)
        if not u:
            return None
        for k, v in fields.items():
            if hasattr(u, k):
                setattr(u, k, v)
        self._save_local_data()
        return u

    def delete_user(self, uid: str) -> bool:
        if self.client:
            try:
                key = self.client.key("User", int(uid))
            except Exception:
                key = self.client.key("User", uid)
            try:
                self.client.delete(key)
                return True
            except Exception:
                return False
        res = self.users.pop(uid, None) is not None
        self._save_local_data()
        return res

    def list_users(self) -> List[User]:
        if self.client:
            query = self.client.query(kind="User")
            res = list(query.fetch())
            out = []
            for e in res:
                uid = str(e.key.id or e.key.name)
                out.append(User(
                    id=uid, 
                    username=e.get("username"),
                    password_hash=e.get("password_hash"),
                    is_admin=e.get("is_admin", False),
                    original_username=e.get("original_username", e.get("username"))
                ))
            return out

        return list(self.users.values())

    def get_user_by_username(self, username: str) -> Optional[User]:
        """Retrieves a user by their username."""
        if self.client:
            query = self.client.query(kind="User")
            query.add_filter("username", "=", username)
            res = list(query.fetch(limit=1))
            if res:
                e = res[0]
                return User(
                    id=str(e.key.id or e.key.name), 
                    username=e.get("username"),
                    password_hash=e.get("password_hash"),
                    is_admin=e.get("is_admin", False),
                    original_username=e.get("original_username", e.get("username"))
                )
            return None
        
        for u in self.users.values():
            if u.username == username:
                return u
        return None
    # Backward compatibility aliases
    list_players = list_users

    # --- Deck methods ---
    def add_deck(self, deck_name: str, deck_list_link: Optional[str] = None) -> Deck:
        if self.client:
            key = self.client.key("Deck")
            entity = _datastore.Entity(key=key)
            entity.update({"deck_name": deck_name, "deck_list_link": deck_list_link})
            self.client.put(entity)
            did = str(entity.key.id or entity.key.name)
            return Deck(id=did, deck_name=deck_name, deck_list_link=deck_list_link)

        did = str(uuid.uuid4())
        d = Deck(id=did, deck_name=deck_name, deck_list_link=deck_list_link)
        self.decks[did] = d
        self._save_local_data()
        return d

    def list_decks(self) -> List[Deck]:
        if self.client:
            query = self.client.query(kind="Deck")
            res = list(query.fetch())
            return [Deck(id=str(e.key.id or e.key.name), deck_name=e.get("deck_name"), deck_list_link=e.get("deck_list_link")) for e in res]
        return list(self.decks.values())

    def update_deck(self, did: str, **fields) -> Optional[Deck]:
        if self.client:
            key = self.client.key("Deck", int(did) if did.isdigit() else did)
            entity = self.client.get(key)
            if not entity: return None
            entity.update(fields)
            self.client.put(entity)
            return Deck(id=did, deck_name=entity.get("deck_name"), deck_list_link=entity.get("deck_list_link"))
        
        d = self.decks.get(did)
        if not d: return None
        for k, v in fields.items():
            if hasattr(d, k): setattr(d, k, v)
        self._save_local_data()
        return d

    def delete_deck(self, did: str) -> bool:
        if self.client:
            try:
                key = self.client.key("Deck", int(did) if did.isdigit() else did)
                self.client.delete(key)
                return True
            except Exception: return False
        res = self.decks.pop(did, None) is not None
        self._save_local_data()
        return res

    # --- League methods ---
    def add_league(self, nr: int, start_date: str, weeks_rounds: int, weeks_playoffs: int, end_date: str) -> League:
        if self.client:
            key = self.client.key("League")
            entity = _datastore.Entity(key=key)
            entity.update({
                "nr": nr,
                "start_date": start_date,
                "weeks_rounds": weeks_rounds,
                "weeks_playoffs": weeks_playoffs,
                "end_date": end_date,
                "round_robin_closed": False,
                "playoffs_closed": False
            })
            self.client.put(entity)
            lid = str(entity.key.id or entity.key.name)
            return League(id=lid, nr=nr, start_date=start_date, weeks_rounds=weeks_rounds, weeks_playoffs=weeks_playoffs, end_date=end_date)

        lid = str(uuid.uuid4())
        l = League(id=lid, nr=nr, start_date=start_date, weeks_rounds=weeks_rounds, weeks_playoffs=weeks_playoffs, end_date=end_date)
        self.leagues[lid] = l
        self._save_local_data()
        return l

    def list_leagues(self) -> List[League]:
        if self.client:
            query = self.client.query(kind="League")
            res = list(query.fetch())
            return [League(
                id=str(e.key.id or e.key.name),
                nr=e.get("nr"),
                start_date=e.get("start_date"),
                weeks_rounds=e.get("weeks_rounds", 0),
                weeks_playoffs=e.get("weeks_playoffs", 0),
                end_date=e.get("end_date"),
                round_robin_closed=e.get("round_robin_closed", False),
                playoffs_closed=e.get("playoffs_closed", False)
            ) for e in res]
        return list(self.leagues.values())

    def update_league(self, lid: str, **fields) -> Optional[League]:
        if self.client:
            key = self.client.key("League", int(lid) if lid.isdigit() else lid)
            entity = self.client.get(key)
            if not entity: return None
            entity.update(fields)
            self.client.put(entity)
            return League(id=lid, nr=entity.get("nr"), start_date=entity.get("start_date"), end_date=entity.get("end_date"), round_robin_closed=entity.get("round_robin_closed"), playoffs_closed=entity.get("playoffs_closed"))
        
        l = self.leagues.get(lid)
        if not l: return None
        for k, v in fields.items():
            if hasattr(l, k): setattr(l, k, v)
        self._save_local_data()
        return l

    def delete_league(self, lid: str) -> bool:
        if self.client:
            try:
                key = self.client.key("League", int(lid) if lid.isdigit() else lid)
            except Exception:
                key = self.client.key("League", lid)
            try:
                self.client.delete(key)
                return True
            except Exception:
                return False

        return self.leagues.pop(lid, None) is not None

    # --- Round methods ---
    def add_round(self, league_id: str, nr: int, start_date: str, end_date: str) -> Round:
        if self.client:
            key = self.client.key("Round")
            entity = _datastore.Entity(key=key)
            entity.update({
                "league_id": league_id,
                "nr": nr,
                "start_date": start_date,
                "end_date": end_date
            })
            self.client.put(entity)
            rid = str(entity.key.id or entity.key.name)
            return Round(id=rid, league_id=league_id, nr=nr, start_date=start_date, end_date=end_date)

        rid = str(uuid.uuid4())
        r = Round(id=rid, league_id=league_id, nr=nr, start_date=start_date, end_date=end_date)
        self.rounds[rid] = r
        self._save_local_data()
        return r

    def list_rounds(self, league_id: Optional[str] = None) -> List[Round]:
        if self.client:
            query = self.client.query(kind="Round")
            if league_id:
                query.add_filter("league_id", "=", league_id)
            res = list(query.fetch())
            return [Round(id=str(e.key.id or e.key.name), league_id=e.get("league_id"), nr=e.get("nr"), start_date=e.get("start_date"), end_date=e.get("end_date")) for e in res]
        
        if league_id:
            return [r for r in self.rounds.values() if r.league_id == league_id]
        return list(self.rounds.values())

    # --- LeaguePlayer methods ---
    def add_user_to_league(self, league_id: str, user_id: str, deck_id: str) -> LeaguePlayer:
        if self.client:
            key = self.client.key("LeaguePlayer")
            entity = _datastore.Entity(key=key)
            entity.update({"league_id": league_id, "user_id": user_id, "deck_id": deck_id})
            self.client.put(entity)
            lpid = str(entity.key.id or entity.key.name)
            return LeaguePlayer(id=lpid, league_id=league_id, user_id=user_id, deck_id=deck_id)

        lpid = str(uuid.uuid4())
        lp = LeaguePlayer(id=lpid, league_id=league_id, user_id=user_id, deck_id=deck_id)
        self.league_players[lpid] = lp
        self._save_local_data()
        return lp

    def list_league_players(self, league_id: Optional[str] = None) -> List[LeaguePlayer]:
        if self.client:
            query = self.client.query(kind="LeaguePlayer")
            if league_id:
                query.add_filter("league_id", "=", league_id)
            res = list(query.fetch())
            return [LeaguePlayer(id=str(e.key.id or e.key.name), league_id=e.get("league_id"), user_id=e.get("user_id"), deck_id=e.get("deck_id")) for e in res]
        
        if league_id:
            return [lp for lp in self.league_players.values() if lp.league_id == league_id]
        return list(self.league_players.values())

    def update_league_player(self, lp_id: str, **fields) -> bool:
        if self.client:
            key = self.client.key("LeaguePlayer", int(lp_id) if lp_id.isdigit() else lp_id)
            entity = self.client.get(key)
            if not entity: return False
            entity.update(fields)
            self.client.put(entity)
            return True
        
        lp = self.league_players.get(lp_id)
        if not lp: return False
        for k, v in fields.items():
            if hasattr(lp, k): setattr(lp, k, v)
        self._save_local_data()
        return True

    def remove_player_from_league(self, lp_id: str) -> bool:
        if self.client:
            key = self.client.key("LeaguePlayer", int(lp_id) if lp_id.isdigit() else lp_id)
            self.client.delete(key)
            return True
        res = self.league_players.pop(lp_id, None) is not None
        self._save_local_data()
        return res

    # --- Match methods ---
    def add_match(self, player_a: str, player_b: str, round_id: str, starting_player: Optional[str], games: List[Dict], went_in_time: bool = False, match_type: str = "Round") -> Match:
        if self.client:
            key = self.client.key("Match")
            entity = _datastore.Entity(key=key)
            entity.update({
                "player_a": player_a,
                "player_b": player_b,
                "round_id": round_id,
                "starting_player": starting_player,
                "games": games,
                "went_in_time": went_in_time,
                "match_type": match_type,
            })
            self.client.put(entity)
            mid = str(entity.key.id or entity.key.name)
            from models import Game as GameModel, Match as MatchModel
            game_objs = [GameModel(game_index=i + 1, winner=g.get("winner")) for i, g in enumerate(games)]
            return MatchModel(id=mid, player_a=player_a, player_b=player_b, round_id=round_id, starting_player=starting_player, games=game_objs, went_in_time=went_in_time, match_type=match_type)

        mid = str(uuid.uuid4())
        from models import Game as GameModel, Match as MatchModel
        game_objs = [GameModel(game_index=i, winner=g.get("winner")) for i, g in enumerate(games, start=1)]
        m = MatchModel(id=mid, player_a=player_a, player_b=player_b, round_id=round_id, starting_player=starting_player, games=game_objs, went_in_time=went_in_time, match_type=match_type)
        self.matches[mid] = m
        self._save_local_data()
        return m

    def update_match(self, mid: str, **fields) -> Optional[Match]:
        from models import Game as GameModel, Match as MatchModel
        if self.client:
            try:
                key = self.client.key("Match", int(mid))
            except Exception:
                key = self.client.key("Match", mid)
            entity = self.client.get(key)
            if not entity:
                return None
            for k, v in fields.items():
                entity[k] = v
            self.client.put(entity)
            # rebuild Match model
            games = entity.get("games", [])
            game_objs = [GameModel(game_index=i + 1, winner=g.get("winner")) for i, g in enumerate(games)]
            return MatchModel(
                id=str(entity.key.id or entity.key.name), 
                player_a=entity.get("player_a"), 
                player_b=entity.get("player_b"), 
                round_id=entity.get("round_id"),
                starting_player=entity.get("starting_player"), 
                games=game_objs, 
                went_in_time=entity.get("went_in_time", False),
                match_type=entity.get("match_type", "Round")
            )

        m = self.matches.get(mid)
        if not m:
            return None
        for k, v in fields.items():
            if hasattr(m, k):
                setattr(m, k, v)
            if k == 'games':
                # convert list of dicts to Game objects if necessary
                if isinstance(v, list) and v and isinstance(v[0], dict):
                    game_objs = [GameModel(game_index=i, winner=g.get('winner')) for i, g in enumerate(v, start=1)]
                    setattr(m, 'games', game_objs)
                elif isinstance(v, list) and v and hasattr(v[0], 'winner'):
                    setattr(m, 'games', v)
                else:
                    setattr(m, 'games', [])
        self._save_local_data()
        return m

    def list_matches(self) -> List[Match]:
        if self.client:
            query = self.client.query(kind="Match")
            res = list(query.fetch())
            out = []
            from models import Game as GameModel, Match as MatchModel
            for e in res:
                mid = str(e.key.id or e.key.name)
                games = e.get("games", [])
                game_objs = [GameModel(game_index=i + 1, winner=g.get("winner")) for i, g in enumerate(games)]
                out.append(MatchModel(
                    id=mid, 
                    player_a=e.get("player_a"), 
                    player_b=e.get("player_b"), 
                    round_id=e.get("round_id"),
                    starting_player=e.get("starting_player"), 
                    games=game_objs, 
                    went_in_time=e.get("went_in_time", False),
                    match_type=e.get("match_type", "Round")
                ))
            return out

        return list(self.matches.values())


# Singleton instance for simple use in app
_ds = None


def get_client() -> DatastoreClient:
    global _ds
    if _ds is None:
        _ds = DatastoreClient()
    return _ds
