import argparse
import sys
from dotenv import load_dotenv
load_dotenv()

from datastore_client import get_client

def main():
    parser = argparse.ArgumentParser(description="Delete matches, rounds, decks, and roster entries belonging to a certain league.")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--league-id", type=str, help="The league ID (e.g. 5629499534213120 or a UUID)")
    group.add_argument("--league-nr", type=int, help="The league number/nr (e.g. 1)")
    args = parser.parse_args()

    client = get_client()
    
    # 1. Resolve League ID
    leagues = client.list_leagues()
    target_league = None
    
    if args.league_id:
        league_id = args.league_id
        target_league = next((l for l in leagues if l.id == league_id), None)
        if not target_league:
            print(f"Warning: League ID '{league_id}' not found in listed leagues.")
            print("Available leagues:")
            for l in leagues:
                print(f"  - League {l.nr} (ID: {l.id})")
            confirm = input("Would you like to try deleting data for this ID anyway? (y/n): ").strip().lower()
            if confirm != 'y':
                print("Aborted.")
                sys.exit(0)
        else:
            print(f"Found League {target_league.nr} (ID: {target_league.id})")
            
    elif args.league_nr:
        target_league = next((l for l in leagues if l.nr == args.league_nr), None)
        if not target_league:
            print(f"Error: League number '{args.league_nr}' not found.")
            print("Available leagues:")
            for l in leagues:
                print(f"  - League {l.nr} (ID: {l.id})")
            sys.exit(1)
        league_id = target_league.id
        print(f"Resolved League {target_league.nr} to ID: {league_id}")

    # 1b. Check if the league is locked
    if target_league and target_league.delete_lock:
        print(f"\nError: League {target_league.nr} (ID: {target_league.id}) is locked and cannot be deleted.")
        print("To unlock it, set the 'locked' flag to False first.")
        sys.exit(1)

    # 2. Get all rounds and league players/decks associated with this league
    rounds = client.list_rounds(league_id)
    round_ids = {r.id for r in rounds}
    print(f"Found {len(rounds)} rounds associated with league '{league_id}': {', '.join(f'Round {r.nr} (ID: {r.id})' for r in sorted(rounds, key=lambda x: x.nr))}")
    
    league_players = client.list_league_players(league_id)
    deck_ids = {m.deck_id for m in league_players if m.deck_id}
    print(f"Found {len(league_players)} league players and {len(deck_ids)} associated decks for league '{league_id}'.")

    # 3. Delete Matches
    all_matches = client.list_matches()
    league_matches = [m for m in all_matches if getattr(m, 'round_id', None) in round_ids]
    
    if league_matches:
        print(f"\nStarting deletion of {len(league_matches)} matches...")
        match_count = 0
        for m in league_matches:
            success = client.delete_match(m.id)
            if success:
                match_count += 1
                print(f"Deleted match {m.id}: player_a={m.player_a} vs player_b={m.player_b}")
            else:
                print(f"Failed to delete match {m.id}")
        print(f"Successfully deleted {match_count} matches.")
    else:
        print("\nNo matches found to delete.")
        
    # 4. Delete Rounds
    if rounds:
        print(f"\nStarting deletion of {len(rounds)} rounds...")
        round_count = 0
        for r in rounds:
            success = client.delete_round(r.id)
            if success:
                round_count += 1
                print(f"Deleted round {r.nr} (ID: {r.id})")
            else:
                print(f"Failed to delete round {r.id}")
        print(f"Successfully deleted {round_count} rounds.")
    else:
        print("\nNo rounds found to delete.")

    # 5. Delete Decks
    if deck_ids:
        print(f"\nStarting deletion of {len(deck_ids)} decks...")
        deck_count = 0
        for did in deck_ids:
            success = client.delete_deck(did)
            if success:
                deck_count += 1
                print(f"Deleted deck {did}")
            else:
                print(f"Failed to delete deck {did}")
        print(f"Successfully deleted {deck_count} decks.")
    else:
        print("\nNo decks found to delete.")
        
    # 6. Delete League Players
    if league_players:
        print(f"\nStarting deletion of {len(league_players)} league players...")
        lp_count = 0
        for lp in league_players:
            success = client.remove_player_from_league(lp.id)
            if success:
                lp_count += 1
                print(f"Deleted league player {lp.id} (user_id={lp.user_id})")
            else:
                print(f"Failed to delete league player {lp.id}")
        print(f"Successfully deleted {lp_count} league players.")
    else:
        print("\nNo league players found to delete.")
    
    # 7. Delete the League itself
    print(f"\nStarting deletion of League '{league_id}'...")
    success = client.delete_league(league_id)
    if success:
        print(f"Successfully deleted League (ID: {league_id}).")
    else:
        print(f"Failed to delete League (ID: {league_id}).")
    
    print("\nCleanup complete.")

if __name__ == "__main__":
    main()
