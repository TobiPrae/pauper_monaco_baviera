import os
import json
import streamlit as st
from typing import Dict, Any
from models import User, Match, Deck, League, LeaguePlayer, Round, Game

class BaseStore:
    def __init__(self):
        self.service_account_info = dict(st.secrets.get("service_account_key", {}))
        self.use_gcp = os.environ.get("USE_GCP_DATASTORE") == "1" or bool(self.service_account_info)
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
                self._load_local_data()
            

    def _load_local_data(self):
        """Loads data from a local JSON file if it exists."""
        if os.path.exists(self.local_file):
            try:
                with open(self.local_file, "r") as f:
                    data = json.load(f)
                    # Restore User objects
                    for u in data.get("users", []):
                        user_fields = {k: v for k, v in u.items() if k in ["id", "username", "password_hash", "is_admin", "original_username"]}
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
                        games_data = m.pop("games", [])
                        game_objs = [Game(**g) for g in games_data]
                        self.matches[m["id"]] = Match(games=game_objs, **m)
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
