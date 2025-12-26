# Conan Exiles Killfeed Bot

This is a Python-based Discord bot designed to monitor the **database backups** of a Conan Exiles server and announce player deaths in a specific Discord channel. It queries death events directly from the game's database, making it accurate and efficient.

The bot supports multiple servers (e.g., Exiled Lands and Isle of Siptah) and posts deaths to separate channels.

## Features

- Real-time death notifications from the game database.
- **Auto-Updating PvP Ranking:** A persistent leaderboard message that updates automatically.
- Identifies player vs. player (PvP) and player vs. environment (PvE) kills.
- **Scalable Multi-Server Support:** Easily configure any number of servers.
- **Smart Filtering:** Ignores duplicate death events occurring within 10 seconds (e.g., from game bugs) to ensure accurate ranking.
- Tracks the last read event to avoid duplicate messages after restarts.

## Commands

There are no commands. The ranking leaderboard is now a persistent message that updates automatically.

## Prerequisites

- Python 3.6 or higher.
- `discord.py` library (`pip install discord.py`).
- A Discord Bot and its Token.
- Direct access to the Conan Exiles server's `Saved` directory.

## Installation and Configuration

1.  **Clone the Repository**
    ```bash
    git clone https://github.com/melecajou/conankillfeed.git
    cd conankillfeed
    ```

2.  **Create a Virtual Environment & Install Dependencies**
    ```bash
    python3 -m venv venv
    source venv/bin/activate
    pip install discord.py
    ```

3.  **Create the Configuration File**
    ```bash
    cp config.py.example config.py
    ```

4.  **Run the Backfill Script (First Time Only)**
    To populate the ranking with your server's history, run the backfill script for each configured server.
    ```bash
    # Make sure your config.py is set up before running this!
    python3 backfill_ranking.py "Your Server Name"
    ```

5.  **Edit the `config.py` File**
    Open `config.py` and fill in the variables.

    - `KILLFEED_BOT_TOKEN`: Your Discord bot's token.
    - `RANKING_DB_PATH`: Path to the ranking database file.
    - `SPAWNS_DB_PATH`: Path to the `spawns.db` file.
    - `PVP_ONLY_DEATHS`: A dictionary to control PvP-only death reporting per server.
    - `SERVERS`: A list of dictionaries, one for each server.

      **Server Configuration Example:**
      ```python
      {
          "name": "Exiled Lands",
          "enabled": True,
          "channel_id": 12345, // For kill announcements
          "ranking_channel_id": 67890, // For the auto-updating leaderboard
          "saved_path": "/path/to/conan/saved/",
          "db_pattern": "game_backup_*.db",
          "last_event_file": "/path/to/last_event.txt",
          "poll_interval": 20, // How often to check for kills (seconds)
          "ranking_update_interval": 300, // How often to update the ranking (seconds)
      }
      ```

    **How to get a Discord Channel ID:**
    - In Discord, go to `User Settings` > `Advanced` and enable `Developer Mode`.
    - Right-click on the desired text channel and select `Copy Channel ID`.

## Running the Bot as a Systemd Service (Recommended)

To ensure the bot runs continuously, starts on boot, and restarts automatically if it crashes, setting it up as a `systemd` service is the recommended method.

1.  **Create a Service File**

    Create a file named `killfeed.service` in `/etc/systemd/system/` using a text editor like `nano`:
    ```bash
    sudo nano /etc/systemd/system/killfeed_bot.service
    ```

2.  **Add the Service Configuration**

    Paste the following content into the file. You **must** change `User`, `Group`, and the paths to match your specific setup.

    ```ini
    [Unit]
    Description=Conan Exiles Killfeed Bot
    After=network.target

    [Service]
    # Change this to the user/group that should run the bot
    User=steam

    # Change this to the absolute path of your bot's directory
    WorkingDirectory=/home/steam/bots/Killfeed

    # Command to start the bot using the python from the virtual environment
    ExecStart=/home/steam/bots/Killfeed/venv/bin/python3 -u killfeed_bot.py

    # Restart policy
    Restart=on-failure
    RestartSec=5s

    [Install]
    WantedBy=multi-user.target
    ```

3.  **Enable and Start the Service**

    After saving the file, reload the `systemd` daemon, enable the service to start on boot, and then start it immediately.
    ```bash
    sudo systemctl daemon-reload
    sudo systemctl enable killfeed_bot.service
    sudo systemctl start killfeed_bot.service
    ```

4.  **Check the Status**

    You can check if the bot is running correctly and see its latest logs with:
    ```bash
    sudo systemctl status killfeed_bot.service
    ```

## How It Works

The bot periodically checks the server's `Saved` directory for the latest database backup (`game_backup_*.db` or `dlc_siptah_backup_*.db`). It then connects to this database in read-only mode and queries the `game_events` table for new death events (eventType 103) since the last check. If an NPC is the killer, the bot uses the `spawns.db` database to find and display the NPC's name.