import os
import json
import datetime
import streamlit as st
from typing import Dict, Any
from dataclasses import fields as dataclass_fields
from models import User, Match, Deck, League, LeaguePlayer, Round, Game

class BaseStore:
    def __init__(self):
        self.service_account_info = dict(st.secrets.get("service_account_key", {}))
        
        # Determine if we should use GCP Datastore
        # 1. Check environment variable (Priority for local dev/test via .env)
        env_val = os.getenv("USE_GCP_DATASTORE")
        if env_val is not None:
            self.use_gcp = env_val.lower() == "true"
        else:
            # 2. Check Streamlit secrets (For production)
            # Matches your secrets.toml: [USE_GCP_DATASTORE] var = "true"
            gcp_secret = st.secrets.get("USE_GCP_DATASTORE", {})
            self.use_gcp = str(gcp_secret.get("var", "false")).lower() == "true"

        self.client = None
        self.local_file = "local_datastore.json"
        
        self.users: Dict[str, User] = {}
        self.decks: Dict[str, Deck] = {}
        self.matches: Dict[str, Match] = {}
        self.leagues: Dict[str, League] = {}
        self.rounds: Dict[str, Round] = {}
        self.league_players: Dict[str, LeaguePlayer] = {}

        if self.use_gcp:
            try:
                from google.cloud import datastore
                self.client = datastore.Client.from_service_account_info(self.service_account_info)
            except Exception:
                self.use_gcp = False
        else:
            self._load_local_data()

    def _get_audit_fields(self) -> dict:
        """Returns audit metadata (modified_by, modified_at) for the current user."""
        user_id = "system"
        try:
            user = st.session_state.get("user")
            if user is not None:
                user_id = user.id
        except Exception:
            pass
        return {
            "modified_by": user_id,
            "modified_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        }


    def _load_local_data(self):
        """Loads data from a local JSON file if it exists."""
        if os.path.exists(self.local_file):
            try:
                with open(self.local_file, "r") as f:
                    data = json.load(f)
                    # Restore User objects
                    for u in data.get("users", []):
                        valid_keys = {f.name for f in dataclass_fields(User)}
                        user_fields = {k: v for k, v in u.items() if k in valid_keys}
                        if "original_username" not in user_fields:
                            user_fields["original_username"] = user_fields.get("username", "")
                        self.users[u["id"]] = User(**user_fields)
                    
                    # Restore other entities
                    deck_keys = {f.name for f in dataclass_fields(Deck)}
                    for d in data.get("decks", []):
                        self.decks[d["id"]] = Deck(**{k: v for k, v in d.items() if k in deck_keys})
                    league_keys = {f.name for f in dataclass_fields(League)}
                    for l in data.get("leagues", []):
                        self.leagues[l["id"]] = League(**{k: v for k, v in l.items() if k in league_keys})
                    round_keys = {f.name for f in dataclass_fields(Round)}
                    for r in data.get("rounds", []):
                        self.rounds[r["id"]] = Round(**{k: v for k, v in r.items() if k in round_keys})
                    lp_keys = {f.name for f in dataclass_fields(LeaguePlayer)}
                    for lp in data.get("league_players", []):
                        self.league_players[lp["id"]] = LeaguePlayer(**{k: v for k, v in lp.items() if k in lp_keys})
                    match_keys = {f.name for f in dataclass_fields(Match)}
                    for m in data.get("matches", []):
                        games_data = m.pop("games", [])
                        game_objs = [Game(**g) for g in games_data]
                        match_fields = {k: v for k, v in m.items() if k in match_keys}
                        self.matches[m["id"]] = Match(games=game_objs, **match_fields)
            except Exception as e:
                print(f"Warning: Could not load local data: {e}")

    def save_local_data(self):
        """Saves current in-memory state to a local JSON file."""
        if self.client is not None:
            return

        try:
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
