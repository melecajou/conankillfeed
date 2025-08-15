import discord
from discord.ext import commands, tasks
import sqlite3
import os
import glob
from datetime import datetime
import config

# --- Constants ---
DEATH_EVENT_TYPE = 103

# --- Intents and Bot Initialization ---
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix='!killfeed', intents=intents)

# --- Helper Functions ---

def get_last_event_time(file_path):
    """Reads the last processed event time from a given file."""
    try:
        with open(file_path, 'r') as f:
            return int(f.read().strip())
    except (FileNotFoundError, ValueError):
        return 0

def set_last_event_time(new_time, file_path):
    """Writes the new last processed event time to a given file."""
    with open(file_path, 'w') as f:
        f.write(str(new_time))

def find_latest_db_backup(search_path, db_pattern):
    """Finds the most recently modified database file in a given path matching a pattern."""
    list_of_files = glob.glob(os.path.join(search_path, db_pattern))
    return max(list_of_files, key=os.path.getmtime) if list_of_files else None

# --- Core Killfeed Logic ---

async def process_server_kills(channel_id, saved_path, db_pattern, last_event_file, server_name):
    """
    Generic function to check for new kills for a specific server and post them to Discord.
    """
    killfeed_channel = bot.get_channel(channel_id)
    if not killfeed_channel:
        print(f"ERROR [{server_name}]: Killfeed channel with ID {channel_id} not found.")
        return

    db_path = find_latest_db_backup(saved_path, db_pattern)
    if not db_path:
        # This is a common case if the server hasn't created a backup yet, so no error message needed.
        return

    last_time = get_last_event_time(last_event_file)
    new_max_time = last_time

    try:
        con = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
        cur = con.cursor()

        # Attach the shared spawns database
        cur.execute(f"ATTACH DATABASE '{config.SPAWNS_DB_PATH}' AS spawns_db;")

        query = f"""
            SELECT
                ge.worldTime,
                ge.causerName,
                ge.ownerName,
                json_extract(ge.argsMap, '$.nonPersistentCauser') AS nonPersistentCauser
            FROM
                game_events ge
            WHERE
                ge.worldTime > ? AND ge.eventType = {DEATH_EVENT_TYPE}
            ORDER BY
                ge.worldTime ASC
        """

        for row in cur.execute(query, (last_time,)):
            event_time, killer_name, victim_name, non_persistent_causer = row

            # If PvP only is enabled, skip events where there is no player killer
            if config.PVP_ONLY_DEATHS and not killer_name:
                continue

            if killer_name:
                message = f"💀 **{killer_name}** killed **{victim_name}**!"
            else:
                npc_name = "the environment"  # Default value
                if non_persistent_causer:
                    # Query the attached spawns database to get the NPC name
                    npc_query = "SELECT Name FROM spawns_db.spawns WHERE RowName = ?"
                    npc_row = cur.execute(npc_query, (non_persistent_causer,)).fetchone()
                    if npc_row:
                        npc_name = npc_row[0]
                message = f"☠️ **{victim_name}** was killed by **{npc_name}**!"

            embed = discord.Embed(description=message, color=discord.Color.dark_red())
            timestamp_obj = datetime.fromtimestamp(event_time)
            formatted_time = timestamp_obj.strftime("%d/%m/%Y at %H:%M:%S")
            embed.set_footer(text=f"Occurred on: {formatted_time}")

            await killfeed_channel.send(embed=embed)

            if event_time > new_max_time:
                new_max_time = event_time

        con.close()

        if new_max_time > last_time:
            set_last_event_time(new_max_time, last_event_file)

    except sqlite3.Error as e:
        print(f"ERROR [{server_name}]: Killfeed error (SQLite): {e}")
    except Exception as e:
        print(f"ERROR [{server_name}]: Unexpected Killfeed error: {e}")

# --- Looping Tasks for Each Server ---

@tasks.loop(seconds=config.EXILED_LANDS_POLL_INTERVAL)
async def check_exiled_lands_kills():
    await process_server_kills(
        channel_id=config.KILLFEED_CHANNEL_ID,
        saved_path=config.CONAN_SAVED_PATH,
        db_pattern='game_backup_*.db',
        last_event_file=config.LAST_EVENT_TIME_FILE,
        server_name="Exiled Lands"
    )

@tasks.loop(seconds=config.SIPTAH_POLL_INTERVAL)
async def check_siptah_kills():
    await process_server_kills(
        channel_id=config.SIPTAH_KILLFEED_CHANEL_ID,
        saved_path=config.SIPTAH_SAVED_PATH,
        db_pattern='dlc_siptah_backup_*.db',
        last_event_file=config.SIPTAH_LAST_EVENT_TIME_FILE,
        server_name="Siptah"
    )

# --- Bot Events ---

@check_exiled_lands_kills.before_loop
async def before_check_exiled_lands_kills():
    await bot.wait_until_ready()

@check_siptah_kills.before_loop
async def before_check_siptah_kills():
    await bot.wait_until_ready()

@bot.event
async def on_ready():
    print(f'Killfeed bot connected as {bot.user}')
    print('---------------------------------')
    check_exiled_lands_kills.start()
    check_siptah_kills.start()

# --- Run Bot ---
bot.run(config.KILLFEED_BOT_TOKEN)
