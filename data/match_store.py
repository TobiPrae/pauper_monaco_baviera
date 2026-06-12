import uuid
from typing import List, Optional, Dict
from models import Match, Game
from .base_store import BaseStore

class MatchStore:
    def __init__(self, base: BaseStore):
        self.base = base

    def add_match(self, player_a: str, player_b: str, round_id: str, starting_player: Optional[str], games: List[Dict], went_in_time: bool = False, match_type: str = "Round") -> Match:
        if self.base.client:
            from google.cloud import datastore
            key = self.base.client.key("Match")
            entity = datastore.Entity(key=key)
            entity.update({"player_a": player_a, "player_b": player_b, "round_id": round_id, "starting_player": starting_player, "games": games, "went_in_time": went_in_time, "match_type": match_type})
            self.base.client.put(entity)
            game_objs = [Game(game_index=i + 1, winner=g.get("winner")) for i, g in enumerate(games)]
            return Match(id=str(entity.key.id or entity.key.name), player_a=player_a, player_b=player_b, round_id=round_id, starting_player=starting_player, games=game_objs, went_in_time=went_in_time, match_type=match_type, match_link=entity.get("match_link"))
        
        mid = str(uuid.uuid4())
        game_objs = [Game(game_index=i, winner=g.get("winner")) for i, g in enumerate(games, start=1)]
        m = Match(id=mid, player_a=player_a, player_b=player_b, round_id=round_id, starting_player=starting_player, games=game_objs, went_in_time=went_in_time, match_type=match_type)
        self.base.matches[mid] = m
        self.base.save_local_data()
        return m

    def update_match(self, mid: str, **fields) -> Optional[Match]:
        if self.base.client:
            try:
                key = self.base.client.key("Match", int(mid))
            except Exception:
                key = self.base.client.key("Match", mid)
            entity = self.base.client.get(key)
            if not entity: return None
            for k, v in fields.items(): entity[k] = v
            self.base.client.put(entity)
            games = entity.get("games", [])
            game_objs = [Game(game_index=i + 1, winner=g.get("winner")) for i, g in enumerate(games)]
            return Match(id=str(entity.key.id or entity.key.name), player_a=entity.get("player_a"), player_b=entity.get("player_b"), round_id=entity.get("round_id"), starting_player=entity.get("starting_player"), games=game_objs, went_in_time=entity.get("went_in_time", False), match_type=entity.get("match_type", "Round"), match_link=entity.get("match_link"))

        m = self.base.matches.get(mid)
        if not m: return None
        for k, v in fields.items():
            if hasattr(m, k): setattr(m, k, v)
            if k == 'games':
                if isinstance(v, list) and v and isinstance(v[0], dict):
                    game_objs = [Game(game_index=i, winner=g.get('winner')) for i, g in enumerate(v, start=1)]
                    setattr(m, 'games', game_objs)
                elif isinstance(v, list) and v and hasattr(v[0], 'winner'): setattr(m, 'games', v)
                else: setattr(m, 'games', [])
        self.base.save_local_data()
        return m

    def list_matches(self) -> List[Match]:
        if self.base.client:
            query = self.base.client.query(kind="Match")
            out = []
            for e in query.fetch():
                games = e.get("games", [])
                game_objs = [Game(game_index=i + 1, winner=g.get("winner")) for i, g in enumerate(games)]
                out.append(Match(id=str(e.key.id or e.key.name), player_a=e.get("player_a"), player_b=e.get("player_b"), round_id=e.get("round_id"), starting_player=e.get("starting_player"), games=game_objs, went_in_time=e.get("went_in_time", False), match_type=e.get("match_type", "Round"), match_link=e.get("match_link")))
            return out
        return list(self.base.matches.values())

    def delete_match(self, mid: str) -> bool:
        if self.base.client:
            try:
                key = self.base.client.key("Match", int(mid) if mid.isdigit() else mid)
            except Exception:
                key = self.base.client.key("Match", mid)
            self.base.client.delete(key)
            return True
        if mid in self.base.matches:
            del self.base.matches[mid]
            self.base.save_local_data()
            return True
        return False
