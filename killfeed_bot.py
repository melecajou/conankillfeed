# Copyright (C) 2025 melecajou
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

import discord
from discord.ext import tasks
import sqlite3
import os
import glob
from datetime import datetime
import json
import config

# --- Constants ---
DEATH_EVENT_TYPE = 103
RANKING_STATE_FILE = "/home/steam/bots/Killfeed/ranking_state.json"

# --- Bot Initialization ---
# No special intents are needed as the bot only sends messages and does not read content.
intents = discord.Intents.default()
bot = discord.Client(intents=intents)

# --- Helper Functions ---

def get_last_event_time(file_path):
    try:
        with open(file_path, 'r') as f:
            return int(f.read().strip())
    except (FileNotFoundError, ValueError):
        return 0

def set_last_event_time(new_time, file_path):
    with open(file_path, 'w') as f:
        f.write(str(new_time))

def find_latest_db_backup(search_path, db_pattern):
    list_of_files = glob.glob(os.path.join(search_path, db_pattern))
    return max(list_of_files, key=os.path.getmtime) if list_of_files else None

def load_ranking_state():
    try:
        with open(RANKING_STATE_FILE, 'r') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}

def save_ranking_state(state):
    with open(RANKING_STATE_FILE, 'w') as f:
        json.dump(state, f, indent=4)

# --- Server Monitor Class ---

class ServerMonitor:
    def __init__(self, server_config):
        self.config = server_config
        self.name = self.config['name']

        # Dynamically create the tasks with the correct intervals
        self.kill_check_task = tasks.loop(seconds=self.config['poll_interval'])(self.process_server_kills)
        self.ranking_update_task = tasks.loop(seconds=self.config['ranking_update_interval'])(self.update_ranking_message)

    def start_tasks(self):
        """Starts the monitoring tasks for this server."""
        self.kill_check_task.start()
        self.ranking_update_task.start()

    async def update_player_score(self, killer_name, victim_name):
        try:
            con = sqlite3.connect(config.RANKING_DB_PATH)
            cur = con.cursor()
            # Killer
            cur.execute("INSERT OR IGNORE INTO scores (server_name, player_name) VALUES (?, ?)", (self.name, killer_name))
            cur.execute("UPDATE scores SET kills = kills + 1, score = score + 1 WHERE server_name = ? AND player_name = ?", (self.name, killer_name))
            # Victim
            cur.execute("INSERT OR IGNORE INTO scores (server_name, player_name) VALUES (?, ?)", (self.name, victim_name))
            cur.execute("UPDATE scores SET deaths = deaths + 1, score = score - 1 WHERE server_name = ? AND player_name = ?", (self.name, victim_name))
            con.commit()
            con.close()
        except sqlite3.Error as e:
            print(f"ERROR [Ranking - {self.name}]: Failed to update score for {killer_name}/{victim_name}: {e}")

    async def process_server_kills(self):
        try:
            await bot.wait_until_ready()
            killfeed_channel = bot.get_channel(self.config['channel_id'])
            if not killfeed_channel:
                # This can happen on startup, so we don't need a loud error.
                return

            db_path = find_latest_db_backup(self.config['saved_path'], self.config['db_pattern'])
            if not db_path:
                return

            last_time = get_last_event_time(self.config['last_event_file'])
            new_max_time = last_time

            con = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
            cur = con.cursor()
            cur.execute(f"ATTACH DATABASE '{config.SPAWNS_DB_PATH}' AS spawns_db;")

            query = f"SELECT ge.worldTime, ge.causerName, ge.ownerName, json_extract(ge.argsMap, '$.nonPersistentCauser') AS npc FROM game_events ge WHERE ge.worldTime > ? AND ge.eventType = {DEATH_EVENT_TYPE} ORDER BY ge.worldTime ASC"

            for event_time, killer, victim, npc_id in cur.execute(query, (last_time,)):
                is_pvp_kill = killer and victim and killer != victim

                if is_pvp_kill:
                    await self.update_player_score(killer, victim)

                pvp_only = config.PVP_ONLY_DEATHS.get(self.name, False)
                if pvp_only and not is_pvp_kill:
                    continue

                if is_pvp_kill:
                    message = f"💀 **{killer}** killed **{victim}**!"
                elif victim:
                    npc_name = "the environment"
                    if npc_id:
                        npc_row = cur.execute("SELECT Name FROM spawns_db.spawns WHERE RowName = ?", (npc_id,)).fetchone()
                        if npc_row: npc_name = npc_row[0]
                    message = f"☠️ **{victim}** was killed by **{npc_name}**!"
                else:
                    continue

                embed = discord.Embed(description=message, color=discord.Color.dark_red())
                embed.set_footer(text=f"Occurred on: {datetime.fromtimestamp(event_time).strftime('%d/%m/%Y at %H:%M:%S')}")
                await killfeed_channel.send(embed=embed)

                if event_time > new_max_time:
                    new_max_time = event_time

            con.close()
            if new_max_time > last_time:
                set_last_event_time(new_max_time, self.config['last_event_file'])
        except Exception as e:
            print(f"ERROR in process_server_kills for {self.name} ({type(e).__name__}): {e}")

    async def update_ranking_message(self):
        try:
            await bot.wait_until_ready()
            ranking_channel = bot.get_channel(self.config['ranking_channel_id'])
            if not ranking_channel:
                return

            con = sqlite3.connect(config.RANKING_DB_PATH)
            cur = con.cursor()
            cur.execute("SELECT player_name, kills, deaths, score FROM scores WHERE server_name = ? ORDER BY score DESC, kills DESC LIMIT 10", (self.name,))
            top_players = cur.fetchall()
            con.close()

            embed = discord.Embed(title=f"🏆 PvP Ranking: {self.name}", color=discord.Color.gold())
            if not top_players:
                embed.description = "No PvP ranking data available yet."
            else:
                description = ""
                for i, (player, kills, deaths, score) in enumerate(top_players, 1):
                    rank_emoji = {1: '🥇', 2: '🥈', 3: '🥉'}.get(i, f'**#{i}**')
                    description += f"{rank_emoji} **{player}** - Score: {score} (K: {kills} / D: {deaths})\n"
                embed.description = description
            embed.set_footer(text=f"Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

            state = load_ranking_state()
            message_id = state.get(self.name)

            if message_id:
                try:
                    message = await ranking_channel.fetch_message(message_id)
                    await message.edit(embed=embed)
                    return
                except discord.NotFound:
                    print(f"INFO [{self.name}]: Ranking message not found. Creating a new one.")
            
            new_message = await ranking_channel.send(embed=embed)
            state[self.name] = new_message.id
            save_ranking_state(state)
        except Exception as e:
            print(f"ERROR in update_ranking_message for {self.name} ({type(e).__name__}): {e}")

# --- Bot Events ---

@bot.event
async def on_ready():
    print(f'Killfeed bot connected as {bot.user}')
    print('---------------------------------')
    
    if not hasattr(config, 'SERVERS') or not config.SERVERS:
        print("ERROR: SERVERS configuration is missing or empty in config.py.")
        return

    for server_config in config.SERVERS:
        if server_config.get("enabled", True):
            print(f"Initializing monitor for server: {server_config['name']}")
            monitor = ServerMonitor(server_config)
            monitor.start_tasks()
        else:
            print(f"Skipping disabled server: {server_config['name']}")

# --- Run Bot ---
if __name__ == "__main__":
    try:
        bot.run(config.KILLFEED_BOT_TOKEN)
    except Exception as e:
        print(f"FATAL: An error occurred while running the bot: {e}")