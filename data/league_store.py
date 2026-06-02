import uuid
from typing import List, Optional
from models import League, Round, LeaguePlayer
from .base_store import BaseStore

class LeagueStore:
    def __init__(self, base: BaseStore):
        self.base = base

    def add_league(self, nr: int, start_date: str, weeks_rounds: int, weeks_playoffs: int, end_date: str) -> League:
        if self.base.client:
            from google.cloud import datastore
            key = self.base.client.key("League")
            entity = datastore.Entity(key=key)
            entity.update({"nr": nr, "start_date": start_date, "weeks_rounds": weeks_rounds, "weeks_playoffs": weeks_playoffs, "end_date": end_date, "round_robin_closed": False, "playoffs_closed": False})
            self.base.client.put(entity)
            return League(id=str(entity.key.id or entity.key.name), nr=nr, start_date=start_date, weeks_rounds=weeks_rounds, weeks_playoffs=weeks_playoffs, end_date=end_date)
        
        lid = str(uuid.uuid4())
        l = League(id=lid, nr=nr, start_date=start_date, weeks_rounds=weeks_rounds, weeks_playoffs=weeks_playoffs, end_date=end_date)
        self.base.leagues[lid] = l
        self.base.save_local_data()
        return l

    def list_leagues(self) -> List[League]:
        if self.base.client:
            query = self.base.client.query(kind="League")
            return [League(id=str(e.key.id or e.key.name), nr=e.get("nr"), start_date=e.get("start_date"), weeks_rounds=e.get("weeks_rounds", 0), weeks_playoffs=e.get("weeks_playoffs", 0), end_date=e.get("end_date"), round_robin_closed=e.get("round_robin_closed", False), playoffs_closed=e.get("playoffs_closed", False)) for e in query.fetch()]
        return list(self.base.leagues.values())

    def update_league(self, lid: str, **fields) -> Optional[League]:
        if self.base.client:
            key = self.base.client.key("League", int(lid) if lid.isdigit() else lid)
            entity = self.base.client.get(key)
            if not entity: return None
            entity.update(fields)
            self.base.client.put(entity)
            return League(id=lid, nr=entity.get("nr"), start_date=entity.get("start_date"), end_date=entity.get("end_date"), round_robin_closed=entity.get("round_robin_closed"), playoffs_closed=entity.get("playoffs_closed"))
        
        l = self.base.leagues.get(lid)
        if not l: return None
        for k, v in fields.items():
            if hasattr(l, k): setattr(l, k, v)
        self.base.save_local_data()
        return l

    def delete_league(self, lid: str) -> bool:
        res = self.base.leagues.pop(lid, None) is not None
        self.base.save_local_data()
        return res

    # Round methods
    def add_round(self, league_id: str, nr: int, start_date: str, end_date: str) -> Round:
        if self.base.client:
            from google.cloud import datastore
            key = self.base.client.key("Round")
            entity = datastore.Entity(key=key)
            entity.update({"league_id": league_id, "nr": nr, "start_date": start_date, "end_date": end_date})
            self.base.client.put(entity)
            return Round(id=str(entity.key.id or entity.key.name), league_id=league_id, nr=nr, start_date=start_date, end_date=end_date)
        rid = str(uuid.uuid4())
        r = Round(id=rid, league_id=league_id, nr=nr, start_date=start_date, end_date=end_date)
        self.base.rounds[rid] = r
        self.base.save_local_data()
        return r

    def list_rounds(self, league_id: Optional[str] = None) -> List[Round]:
        if self.base.client:
            query = self.base.client.query(kind="Round")
            if league_id: query.add_filter("league_id", "=", league_id)
            return [Round(id=str(e.key.id or e.key.name), league_id=e.get("league_id"), nr=e.get("nr"), start_date=e.get("start_date"), end_date=e.get("end_date")) for e in query.fetch()]
        if league_id: return [r for r in self.base.rounds.values() if r.league_id == league_id]
        return list(self.base.rounds.values())

    # LeaguePlayer methods
    def add_user_to_league(self, league_id: str, user_id: str, deck_id: str) -> LeaguePlayer:
        if self.base.client:
            from google.cloud import datastore
            key = self.base.client.key("LeaguePlayer")
            entity = datastore.Entity(key=key)
            entity.update({"league_id": league_id, "user_id": user_id, "deck_id": deck_id})
            self.base.client.put(entity)
            return LeaguePlayer(id=str(entity.key.id or entity.key.name), league_id=league_id, user_id=user_id, deck_id=deck_id)
        lpid = str(uuid.uuid4())
        lp = LeaguePlayer(id=lpid, league_id=league_id, user_id=user_id, deck_id=deck_id)
        self.base.league_players[lpid] = lp
        self.base.save_local_data()
        return lp

    def list_league_players(self, league_id: Optional[str] = None) -> List[LeaguePlayer]:
        if self.base.client:
            query = self.base.client.query(kind="LeaguePlayer")
            if league_id: query.add_filter("league_id", "=", league_id)
            return [LeaguePlayer(id=str(e.key.id or e.key.name), league_id=e.get("league_id"), user_id=e.get("user_id"), deck_id=e.get("deck_id")) for e in query.fetch()]
        if league_id: return [lp for lp in self.base.league_players.values() if lp.league_id == league_id]
        return list(self.base.league_players.values())

    def update_league_player(self, lp_id: str, **fields) -> bool:
        if self.base.client:
            key = self.base.client.key("LeaguePlayer", int(lp_id) if lp_id.isdigit() else lp_id)
            entity = self.base.client.get(key)
            if not entity: return False
            entity.update(fields)
            self.base.client.put(entity)
            return True
        lp = self.base.league_players.get(lp_id)
        if not lp: return False
        for k, v in fields.items():
            if hasattr(lp, k): setattr(lp, k, v)
        self.base.save_local_data()
        return True

    def remove_player_from_league(self, lp_id: str) -> bool:
        res = self.base.league_players.pop(lp_id, None) is not None
        self.base.save_local_data()
        return res
