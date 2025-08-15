# Conan Exiles Killfeed Bot

This is a Python-based Discord bot designed to monitor the **database backups** of a Conan Exiles server and announce player deaths in a specific Discord channel. It queries death events directly from the game's database, making it accurate and efficient.

The bot supports multiple servers (e.g., Exiled Lands and Isle of Siptah) and posts deaths to separate channels.

## Features

- Real-time death notifications extracted directly from the game database.
- Identifies whether the killer was a player or an NPC.
- Support for multiple servers/maps with dedicated Discord channels.
- Simple configuration through a single file.
- Tracks the last read event to avoid duplicate messages after restarts.

## Prerequisites

- Python 3.6 or higher.
- `discord.py` library (`pip install discord.py`).
- A Discord Bot and its Token. [Guide to creating a Bot](https://discordpy.readthedocs.io/en/stable/discord.html)
- Direct access to the Conan Exiles server's `Saved` directory, where the database backups (`game_backup_*.db`) are stored.
- The `spawns.db` database file is included to map NPC IDs to their names.

## Installation and Configuration

1.  **Clone the Repository**
    ```bash
    git clone https://github.com/melecajou/conankillfeed.git
    cd conankillfeed
    ```

2.  **Install Dependencies**
    ```bash
    pip install discord.py
    ```

3.  **Create the Configuration File**
    Copy the example file to create your own configuration file.
    ```bash
    cp config.py.example config.py
    ```

4.  **Edit the `config.py` File**
    Open the `config.py` file and fill in the variables with your information.

    - `KILLFEED_BOT_TOKEN`: Your Discord bot's token. **Keep this secret!**
    - `KILLFEED_CHANNEL_ID`: The ID of the Discord channel where deaths from the main map (Exiled Lands) will be sent.
    - `SIPTAH_KILLFEED_CHANEL_ID`: The channel ID for deaths from the Siptah map.
    - `CONAN_SAVED_PATH`: The absolute path to the `Saved` directory of your main server installation.
      - Example: `/home/steam/conan_exiles/ConanSandbox/Saved/`
    - `SIPTAH_SAVED_PATH`: The absolute path to the `Saved` directory of your Siptah server.
    - `LAST_EVENT_TIME_FILE`: Path to the file that stores the timestamp of the last read event for the main server. You can leave the default.
    - `SIPTAH_LAST_EVENT_TIME_FILE`: Path to the timestamp file for the Siptah server. You can leave the default.
    - `SPAWNS_DB_PATH`: Path to the `spawns.db` database. This file is required to identify NPCs.

    **How to get a Discord Channel ID:**
    - In Discord, go to `User Settings` > `Advanced` and enable `Developer Mode`.
    - Right-click on the desired text channel and select `Copy Channel ID`.

## Running the Bot

After configuring, you can start the bot with the following command:

```bash
python3 killfeed_bot.py
```

To keep the bot running 24/7, it is highly recommended to run it in a persistent terminal session using tools like `screen` or `tmux`.

### Example with `screen`:

```bash
# Starts a new session named 'killfeed'
screen -S killfeed

# Starts the bot inside the session
python3 killfeed_bot.py

# To detach from the session without stopping the bot, press Ctrl+A and then D.
# To return to the session, use:
screen -r killfeed
```

## How It Works

The bot periodically checks the server's `Saved` directory for the latest database backup (`game_backup_*.db` or `dlc_siptah_backup_*.db`). It then connects to this database in read-only mode and queries the `game_events` table for new death events (eventType 103) since the last check. If an NPC is the killer, the bot uses the `spawns.db` database to find and display the NPC's name.