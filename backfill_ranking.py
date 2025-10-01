#!/usr/bin/env python3
# Copyright (C) 2025 melecajou
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

import sqlite3
import os
import glob
import sys
import config

# --- Constants ---
DEATH_EVENT_TYPE = 103

def find_latest_db_backup(search_path, db_pattern):
    """Finds the most recently modified database file in a given path matching a pattern."""
    list_of_files = glob.glob(os.path.join(search_path, db_pattern))
    return max(list_of_files, key=os.path.getmtime) if list_of_files else None

def update_player_score(cursor, server_name, player_name, is_kill):
    """
    Updates a player's score in the ranking database using a provided cursor.
    """
    cursor.execute("INSERT OR IGNORE INTO scores (server_name, player_name) VALUES (?, ?)", (server_name, player_name))
    if is_kill:
        cursor.execute("UPDATE scores SET kills = kills + 1, score = score + 1 WHERE server_name = ? AND player_name = ?", (server_name, player_name))
    else:
        cursor.execute("UPDATE scores SET deaths = deaths + 1, score = score - 1 WHERE server_name = ? AND player_name = ?", (server_name, player_name))

def backfill_ranking(server_name):
    """Reads all PvP kills from a server's latest backup and populates the ranking DB."""
    server_config = None
    for s in config.SERVERS:
        if s['name'].lower() == server_name.lower():
            server_config = s
            break

    if not server_config:
        print(f"ERROR: Server '{server_name}' not found in config.py.")
        return

    print(f"Starting backfill for server: {server_config['name']}...")

    db_path = find_latest_db_backup(server_config['saved_path'], server_config['db_pattern'])
    if not db_path:
        print(f"ERROR: No database backup found for {server_config['name']} at {server_config['saved_path']}.")
        return

    print(f"Found latest database: {db_path}")

    ranking_con = None
    game_con = None

    try:
        # Connect to the ranking database
        ranking_con = sqlite3.connect(config.RANKING_DB_PATH)
        ranking_cur = ranking_con.cursor()

        # Clear any existing scores for this server to prevent duplicates
        print(f"Clearing existing scores for {server_config['name']}...")
        ranking_cur.execute("DELETE FROM scores WHERE server_name = ?", (server_config['name'],))

        # Connect to the game database
        game_con = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
        game_cur = game_con.cursor()

        query = f"""
            SELECT causerName, ownerName
            FROM game_events
            WHERE eventType = {DEATH_EVENT_TYPE}
        """

        print("Processing kill events...")
        count = 0
        for killer_name, victim_name in game_cur.execute(query):
            # We only care about PvP kills where both parties are named players
            if killer_name and victim_name and killer_name != victim_name:
                update_player_score(ranking_cur, server_config['name'], killer_name, is_kill=True)
                update_player_score(ranking_cur, server_config['name'], victim_name, is_kill=False)
                count += 1
        
        ranking_con.commit()
        print(f"Successfully processed and updated {count} PvP kills.")

    except sqlite3.Error as e:
        print(f"ERROR: A database error occurred: {e}")
        if ranking_con:
            ranking_con.rollback()
    finally:
        if ranking_con:
            ranking_con.close()
        if game_con:
            game_con.close()

    print("Backfill complete.")

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python3 backfill_ranking.py <ServerName>")
        print("Example: python3 backfill_ranking.py \"Exiled Lands\"")
        sys.exit(1)
    
    # Initialize the main ranking DB schema if it doesn't exist
    try:
        con = sqlite3.connect(config.RANKING_DB_PATH)
        cur = con.cursor()
        cur.execute("""
            CREATE TABLE IF NOT EXISTS scores (
                server_name TEXT NOT NULL,
                player_name TEXT NOT NULL,
                kills INTEGER NOT NULL DEFAULT 0,
                deaths INTEGER NOT NULL DEFAULT 0,
                score INTEGER NOT NULL DEFAULT 0,
                PRIMARY KEY (server_name, player_name)
            )
        """)
        con.commit()
        con.close()
    except sqlite3.Error as e:
        print(f"FATAL: Could not initialize ranking database schema: {e}")
        sys.exit(1)

    backfill_ranking(sys.argv[1])
