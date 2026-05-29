import os
import uuid
import time
from typing import Dict, List, Optional
from models import Player, Match, Deck, League, LeaguePlayer

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
            self.decks: Dict[str, Deck] = {}
            self.matches: Dict[str, Match] = {}
            self.leagues: Dict[str, League] = {}
            self.league_players: Dict[str, LeaguePlayer] = {}

    # --- Player methods ---
    def add_player(self, player_name: str) -> Player:
        if self.client:
            key = self.client.key("Player")
            entity = _datastore.Entity(key=key)
            entity.update({"player_name": player_name})
            self.client.put(entity)
            pid = str(entity.key.id or entity.key.name)
            return Player(id=pid, player_name=player_name)

        pid = str(uuid.uuid4())
        p = Player(id=pid, player_name=player_name)
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
            return Player(id=str(entity.key.id or entity.key.name), player_name=entity.get("player_name"))

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
                out.append(Player(id=pid, player_name=e.get("player_name")))
            return out

        return list(self.players.values())

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
        return d

    def delete_deck(self, did: str) -> bool:
        if self.client:
            try:
                key = self.client.key("Deck", int(did) if did.isdigit() else did)
                self.client.delete(key)
                return True
            except Exception: return False
        return self.decks.pop(did, None) is not None

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

    # --- LeaguePlayer methods ---
    def add_player_to_league(self, league_id: str, player_id: str, deck_id: str) -> LeaguePlayer:
        if self.client:
            key = self.client.key("LeaguePlayer")
            entity = _datastore.Entity(key=key)
            entity.update({"league_id": league_id, "player_id": player_id, "deck_id": deck_id})
            self.client.put(entity)
            lpid = str(entity.key.id or entity.key.name)
            return LeaguePlayer(id=lpid, league_id=league_id, player_id=player_id, deck_id=deck_id)

        lpid = str(uuid.uuid4())
        lp = LeaguePlayer(id=lpid, league_id=league_id, player_id=player_id, deck_id=deck_id)
        self.league_players[lpid] = lp
        return lp

    def list_league_players(self, league_id: Optional[str] = None) -> List[LeaguePlayer]:
        if self.client:
            query = self.client.query(kind="LeaguePlayer")
            if league_id:
                query.add_filter("league_id", "=", league_id)
            res = list(query.fetch())
            return [LeaguePlayer(id=str(e.key.id or e.key.name), league_id=e.get("league_id"), player_id=e.get("player_id"), deck_id=e.get("deck_id")) for e in res]
        
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
        return True

    def remove_player_from_league(self, lp_id: str) -> bool:
        if self.client:
            key = self.client.key("LeaguePlayer", int(lp_id) if lp_id.isdigit() else lp_id)
            self.client.delete(key)
            return True
        return self.league_players.pop(lp_id, None) is not None

    # --- Match methods ---
    def add_match(self, player_a: str, player_b: str, league_id: str, starting_player: Optional[str], games: List[Dict], went_in_time: bool = False) -> Match:
        if self.client:
            key = self.client.key("Match")
            entity = _datastore.Entity(key=key)
            entity.update({
                "player_a": player_a,
                "player_b": player_b,
                "league_id": league_id,
                "starting_player": starting_player,
                "games": games,
                "went_in_time": went_in_time,
            })
            self.client.put(entity)
            mid = str(entity.key.id or entity.key.name)
            from models import Game as GameModel, Match as MatchModel
            game_objs = [GameModel(game_index=i + 1, winner=g.get("winner")) for i, g in enumerate(games)]
            return MatchModel(id=mid, player_a=player_a, player_b=player_b, league_id=league_id, starting_player=starting_player, games=game_objs, went_in_time=went_in_time)

        mid = str(uuid.uuid4())
        from models import Game as GameModel, Match as MatchModel
        game_objs = [GameModel(game_index=i, winner=g.get("winner")) for i, g in enumerate(games, start=1)]
        m = MatchModel(id=mid, player_a=player_a, player_b=player_b, league_id=league_id, starting_player=starting_player, games=game_objs, went_in_time=went_in_time)
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
            return MatchModel(
                id=str(entity.key.id or entity.key.name), 
                player_a=entity.get("player_a"), 
                player_b=entity.get("player_b"), 
                league_id=entity.get("league_id"),
                starting_player=entity.get("starting_player"), 
                games=game_objs, 
                went_in_time=entity.get("went_in_time", False)
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
                    league_id=e.get("league_id"),
                    starting_player=e.get("starting_player"), 
                    games=game_objs, 
                    went_in_time=e.get("went_in_time", False)
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
