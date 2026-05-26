import os
import uuid
from typing import Dict, List, Optional
from models import Player, Match

# Choose backend: use real GCP Datastore if env indicates, otherwise in-memory fallback
USE_GCP = os.environ.get("USE_GCP_DATASTORE") == "1" or os.environ.get("GOOGLE_APPLICATION_CREDENTIALS") is not None
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
            self.client = _datastore.Client()
        else:
            self.client = None
            self.players: Dict[str, Player] = {}
            self.matches: Dict[str, Match] = {}

    # --- Player methods ---
    def add_player(self, player_name: str, deck_name: Optional[str] = None, deck_list_link: Optional[str] = None) -> Player:
        if self.client:
            key = self.client.key("Player")
            entity = _datastore.Entity(key=key)
            entity.update({"player_name": player_name, "deck_name": deck_name, "deck_list_link": deck_list_link})
            self.client.put(entity)
            pid = str(entity.key.id or entity.key.name)
            return Player(id=pid, player_name=player_name, deck_name=deck_name, deck_list_link=deck_list_link)

        pid = str(uuid.uuid4())
        p = Player(id=pid, player_name=player_name, deck_name=deck_name, deck_list_link=deck_list_link)
        self.players[pid] = p
        return p

    def update_player(self, pid: str, **fields) -> Optional[Player]:
        if self.client:
            # naive implementation: fetch by id
            try:
                key = self.client.key("Player", int(pid))
            except Exception:
                key = self.client.key("Player", pid)
            entity = self.client.get(key)
            if not entity:
                return None
            for k, v in fields.items():
                entity[k] = v
            self.client.put(entity)
            return Player(id=str(entity.key.id or entity.key.name), player_name=entity.get("player_name"), deck_name=entity.get("deck_name"), deck_list_link=entity.get("deck_list_link"))

        p = self.players.get(pid)
        if not p:
            return None
        for k, v in fields.items():
            if hasattr(p, k):
                setattr(p, k, v)
        return p

    def delete_player(self, pid: str) -> bool:
        if self.client:
            try:
                key = self.client.key("Player", int(pid))
            except Exception:
                key = self.client.key("Player", pid)
            try:
                self.client.delete(key)
                return True
            except Exception:
                return False

        return self.players.pop(pid, None) is not None

    def list_players(self) -> List[Player]:
        if self.client:
            query = self.client.query(kind="Player")
            res = list(query.fetch())
            out = []
            for e in res:
                pid = str(e.key.id or e.key.name)
                out.append(Player(id=pid, player_name=e.get("player_name"), deck_name=e.get("deck_name"), deck_list_link=e.get("deck_list_link")))
            return out

        return list(self.players.values())

    # --- Match methods ---
    def add_match(self, player_a: str, player_b: str, starting_player: Optional[str], games: List[Dict], went_in_time: bool = False) -> Match:
        if self.client:
            key = self.client.key("Match")
            entity = _datastore.Entity(key=key)
            entity.update({
                "player_a": player_a,
                "player_b": player_b,
                "starting_player": starting_player,
                "games": games,
                "went_in_time": went_in_time,
            })
            self.client.put(entity)
            mid = str(entity.key.id or entity.key.name)
            from models import Game as GameModel, Match as MatchModel
            game_objs = [GameModel(game_index=i + 1, winner=g.get("winner")) for i, g in enumerate(games)]
            return MatchModel(id=mid, player_a=player_a, player_b=player_b, starting_player=starting_player, games=game_objs, went_in_time=went_in_time)

        mid = str(uuid.uuid4())
        from models import Game as GameModel, Match as MatchModel
        game_objs = [GameModel(game_index=i, winner=g.get("winner")) for i, g in enumerate(games, start=1)]
        m = MatchModel(id=mid, player_a=player_a, player_b=player_b, starting_player=starting_player, games=game_objs, went_in_time=went_in_time)
        self.matches[mid] = m
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
            return MatchModel(id=str(entity.key.id or entity.key.name), player_a=entity.get("player_a"), player_b=entity.get("player_b"), starting_player=entity.get("starting_player"), games=game_objs, went_in_time=entity.get("went_in_time", False))

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
                out.append(MatchModel(id=mid, player_a=e.get("player_a"), player_b=e.get("player_b"), starting_player=e.get("starting_player"), games=game_objs, went_in_time=e.get("went_in_time", False)))
            return out

        return list(self.matches.values())


# Singleton instance for simple use in app
_ds = None


def get_client() -> DatastoreClient:
    global _ds
    if _ds is None:
        _ds = DatastoreClient()
    return _ds
