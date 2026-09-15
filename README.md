<div align="center">

# 🎧 Musicon

<p align="center">
  <strong>A Next-Generation, High-Fidelity Discord Music Bot powered by Discord.py, yt-dlp, and Spotify with Intelligent Auto-DJ.</strong>
</p>

[![Python](https://img.shields.io/badge/Python-3.10%2B-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/)
[![Discord.py](https://img.shields.io/badge/Discord.py-v2.0%2B-5865F2?style=for-the-badge&logo=discord&logoColor=white)](https://discordpy.readthedocs.io/)
[![Spotify API](https://img.shields.io/badge/Spotify-API-1DB954?style=for-the-badge&logo=spotify&logoColor=white)](https://developer.spotify.com/)
[![yt-dlp](https://img.shields.io/badge/yt--dlp-Stream%20Engine-FF0000?style=for-the-badge&logo=youtube&logoColor=white)](https://github.com/yt-dlp/yt-dlp)
[![FFmpeg](https://img.shields.io/badge/FFmpeg-Audio%20Core-007808?style=for-the-badge&logo=ffmpeg&logoColor=white)](https://ffmpeg.org/)
[![AWS EC2](https://img.shields.io/badge/AWS%20EC2-t3.small%20(Ubuntu)-FF9900?style=for-the-badge&logo=amazonec2&logoColor=white)](https://aws.amazon.com/ec2/)
[![Hosted 24/7](https://img.shields.io/badge/Hosted%2024%2F7-Active%20on%20AWS-brightgreen?style=for-the-badge&logo=linux&logoColor=white)](#-production-deployment-aws-ec2-t3small)
[![License](https://img.shields.io/badge/License-MIT-blue.svg?style=for-the-badge)](LICENSE)

<br />

[Features](#-key-features) • [Architecture](#-architecture) • [Slash Commands](#-slash-commands) • [Installation](#-installation) • [Configuration](#-configuration) • [Spotify Setup](#-spotify-integration) • [YouTube Cookies](#-youtube-cookie-bypass) • [AWS EC2 Deployment (24/7)](#-production-deployment-aws-ec2-t3small)

</div>

---

## ✨ Overview

**Musicon** is a modern, modular Discord music bot engineered for uncompromising audio performance and reliability. It combines native Discord Slash Commands, robust YouTube audio extraction via `yt-dlp`, deep Spotify catalog resolution with genre classification via `spotipy`, and a smart **Auto-DJ** recommendation algorithm that keeps the party alive even when your queue runs empty.

Whether you're listening to single tracks, entire Spotify albums, or massive playlists, Musicon resolves and streams audio with zero lag and high-fidelity sound.

> 🚀 **Live Production Deployment**: Musicon is deployed and runs **24/7** on an **AWS EC2 `t3.small` instance (Ubuntu LTS)** using a dedicated `systemd` daemon with self-healing audio stream recovery and persistent uptime.

---

## 🚀 Key Features

<table>
  <tr>
    <td width="50%">
      <h3>🤖 Intelligent Auto-DJ</h3>
      <p>Never experience an awkward silence again. When the queue runs empty, Musicon analyzes the server's recent listening history and Spotify artist genres to seamlessly generate and queue matching songs on the fly.</p>
    </td>
    <td width="50%">
      <h3>🎵 Multi-Platform Ingestion</h3>
      <p>Play anything effortlessly: YouTube track URLs, YouTube searches, YouTube playlists, Spotify tracks, Spotify albums, and Spotify public/collaborative playlists.</p>
    </td>
  </tr>
  <tr>
    <td width="50%">
      <h3>⚡ 100% Native Slash Commands</h3>
      <p>Built exclusively on Discord's modern Application Commands (<code>/play</code>, <code>/skip</code>, <code>/pause</code>, <code>/resume</code>, <code>/queue</code>, etc.) with interactive embeds, real-time feedback, and zero clutter.</p>
    </td>
    <td width="50%">
      <h3>🛡️ YouTube Anti-Bot & Cookie Bypass</h3>
      <p>Bypass YouTube rate limits, bot verification screens, and age-restrictions with built-in support for exported browser cookies (<code>youtube_cookies.txt</code>) or local browser profile loading.</p>
    </td>
  </tr>
  <tr>
    <td width="50%">
      <h3>🔄 Self-Healing Audio Pipeline</h3>
      <p>Equipped with automatic voice reconnection logic, concurrent queue safety locks, and resilient FFmpeg stream reconnection arguments to survive network hiccups.</p>
    </td>
    <td width="50%">
      <h3>🎨 Rich Dynamic Embeds</h3>
      <p>Sleek, informative Discord embeds display track title, artists, thumbnails, playback status, queue pages, and dedicated Auto-DJ visual badges.</p>
    </td>
  </tr>
</table>

---

## 🏗 Architecture

Musicon separates media discovery, metadata resolution, audio extraction, and voice delivery into a streamlined pipeline:

```mermaid
flowchart TD
    User([👤 User in Voice Channel]) -->|Slash Command e.g. /play| Bot[🤖 Musicon Bot]
    
    subgraph Resolution [Discovery & Resolution Layer]
        Bot -->|Direct Search / URL| YTDL[🔍 yt-dlp Engine]
        Bot -->|Spotify Track / Album / Playlist| Spot[🟢 Spotify Web API]
        Spot -->|Extract Title & Artist + Genre| YTDL
    end
    
    subgraph Streaming [Audio Processing & Streaming]
        YTDL -->|Fetch Direct Audio Stream URL| Stream[Direct Opus / WebM / AAC Stream]
        Stream -->|Piped with reconnect flags| FFmpeg[🎵 FFmpeg Audio Transcoder]
        FFmpeg -->|Discord Voice Client| Voice[🔊 Discord Voice Channel]
    end

    subgraph AutoDJ [Intelligent Auto-DJ Loop]
        Voice -->|Queue Empties| QueueCheck{Queue Empty?}
        QueueCheck -->|Yes & Not Stopped| History[📜 Server History & Genre Analysis]
        History -->|Query Related Track| Spot
    end
```

---

## 🎮 Slash Commands

| Command | Arguments | Description | Example |
| :--- | :--- | :--- | :--- |
| **`/play`** | `query` *(required)* | Search YouTube, or provide a YouTube / Spotify track, album, or playlist link | `/play Bohemian Rhapsody`<br>`/play https://open.spotify.com/playlist/...` |
| **`/skip`** | *None* | Skips the track currently playing | `/skip` |
| **`/pause`** | *None* | Pauses the current audio playback | `/pause` |
| **`/resume`** | *None* | Resumes playback if currently paused | `/resume` |
| **`/stop`** | *None* | Stops playback, clears the queue, and disconnects the bot | `/stop` |
| **`/queue`** | *None* | Displays the currently active track and the upcoming queue | `/queue` |
| **`/history`** | *None* | Shows the last 5 tracks played in the server, with Auto-DJ badges | `/history` |
| **`/spotify_auth`** | *None* | *(Bot Owner only)* Authorizes Spotify OAuth for private/collaborative access | `/spotify_auth` |

---

## 📦 Project Structure

```text
Musicon/
├── MyBot.py                 # Core bot logic, commands, events, and Auto-DJ engine
├── requirements.txt         # Project Python dependencies
├── musicon.service          # Systemd unit file for 24/7 AWS EC2 deployment
├── .env.example             # Template for required environment variables
├── .env                     # Your private credentials (DO NOT COMMIT)
├── youtube_cookies.txt      # Netscape-formatted YouTube cookies for anti-bot bypass
├── bin/
│   └── ffmpeg/
│       └── ffmpeg.exe       # Bundled FFmpeg executable (Windows fallback)
└── README.md                # Project documentation & setup guide
```

---

## 🛠 Installation

### 1. Clone the Repository

```bash
git clone https://github.com/yparshant610/Musicon.git
cd Musicon
```

### 2. Create and Activate a Virtual Environment

* **Windows (PowerShell)**:
  ```powershell
  python -m venv dc_env
  .\dc_env\Scripts\Activate.ps1
  ```

* **Linux / macOS**:
  ```bash
  python3 -m venv dc_env
  source dc_env/bin/activate
  ```

### 3. Install Python Dependencies

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

### 4. Install FFmpeg

Musicon relies on **FFmpeg** to encode audio streams for Discord voice.

* **Windows**:
  - You can place `ffmpeg.exe` directly under `bin/ffmpeg/ffmpeg.exe` (detected automatically by Musicon), or
  - Install via Winget: `winget install Gyan.FFmpeg` and ensure it is on your system `PATH`.
* **Linux (Ubuntu/Debian)**:
  ```bash
  sudo apt update && sudo apt install -y ffmpeg
  ```
* **macOS (Homebrew)**:
  ```bash
  brew install ffmpeg
  ```

Verify your installation:
```bash
ffmpeg -version
```

---

## ⚙️ Configuration

Copy `.env.example` to `.env` (or create a new `.env` file) in the project root:

```bash
cp .env.example .env
```

### Environment Variables

Edit `.env` with your credentials:

```env
# ============================================================
# DISCORD CONFIGURATION
# ============================================================
DISCORD_TOKEN=your_discord_bot_token_here

# ============================================================
# SPOTIFY API CONFIGURATION
# ============================================================
Client_ID=your_spotify_client_id_here
Client_secret=your_spotify_client_secret_here
SPOTIFY_REDIRECT_URI=http://127.0.0.1:8888/callback

# ============================================================
# YOUTUBE COOKIE SETTINGS (RECOMMENDED FOR 24/7 HOSTING)
# ============================================================
# Path to your exported Netscape cookies file
YOUTUBE_COOKIE_FILE=youtube_cookies.txt

# Optional: Read cookies directly from a local browser (e.g., chrome, edge, firefox)
# Leave blank when using YOUTUBE_COOKIE_FILE or on remote servers (EC2/VPS)
YOUTUBE_BROWSER=
```

### Setting up the Discord Bot

1. Go to the [Discord Developer Portal](https://discord.com/developers/applications).
2. Click **New Application** and give your bot a name.
3. Under the **Bot** tab:
   - Click **Reset Token** and copy your token to `DISCORD_TOKEN` in `.env`.
   - Under **Privileged Gateway Intents**, enable:
     - ✅ **Server Members Intent** (recommended)
     - ✅ **Message Content Intent**
4. Under **OAuth2 > URL Generator**:
   - Select scopes: `bot`, `applications.commands`.
   - Bot permissions: `Connect`, `Speak`, `Send Messages`, `Embed Links`, `Read Message History`, `Use Slash Commands`.
   - Open the generated URL in your browser to invite the bot to your Discord server.

---

## 🟢 Spotify Integration

Musicon uses the Spotify Web API to resolve tracks, albums, artist metadata, and genre tags for Auto-DJ.

1. Navigate to the [Spotify Developer Dashboard](https://developer.spotify.com/dashboard) and log in.
2. Click **Create App**:
   - **App Name**: `Musicon Bot`
   - **Redirect URI**: `http://127.0.0.1:8888/callback` (Must match `SPOTIFY_REDIRECT_URI`)
   - **APIs Used**: Select **Web API**.
3. Under your app settings, copy:
   - **Client ID** ➔ Set to `Client_ID` in `.env`
   - **Client Secret** ➔ Set to `Client_secret` in `.env`
4. Once the bot starts up, the bot owner can run the slash command:
   ```text
   /spotify_auth
   ```
   Follow the prompt in your terminal or browser once to authenticate and generate `.spotify_cache`.

---

## 🍪 YouTube Cookie Bypass

To prevent YouTube from blocking requests with *"Sign in to confirm you're not a bot"* or IP throttling (especially when hosting on AWS, DigitalOcean, or other cloud providers):

1. Install a browser extension like **[Get cookies.txt LOCALLY](https://github.com/kairi003/Get-cookies.txt-LOCALLY)** (Chrome / Firefox).
2. Visit [YouTube.com](https://www.youtube.com) while signed into a Google account.
3. Open the extension and export the cookies in **Netscape** format.
4. Save the file as `youtube_cookies.txt` in the root folder of Musicon.
5. In `.env`, ensure:
   ```env
   YOUTUBE_COOKIE_FILE=youtube_cookies.txt
   ```

> **Security Note:** Keep your `youtube_cookies.txt` private. It is already added to `.gitignore` to prevent accidental commits.

---

## ☁️ Production Deployment (AWS EC2 t3.small - 24/7)

Musicon is built and tested for continuous, uninterrupted **24/7 execution** on an **Amazon Web Services (AWS) EC2 `t3.small` instance** running **Ubuntu Linux**.

### ⚙️ Production Architecture & Specs

| Component | Specification | Purpose |
| :--- | :--- | :--- |
| **Cloud Provider** | Amazon Web Services (AWS) | High-availability global infrastructure |
| **Instance Type** | `t3.small` (2 vCPU, 2 GB RAM) | Ideal balance of compute and cost for streaming audio |
| **Operating System**| Ubuntu 22.04 / 24.04 LTS | Stable Linux server environment |
| **Process Manager**| `systemd` (`musicon.service`) | Auto-restart on crash, reboot persistence, background daemon |
| **Storage / Swap** | 20 GB gp3 SSD + 2 GB Swap file | Prevents OOM (Out Of Memory) during peak FFmpeg transcoding |
| **Anti-Bot Engine**| Netscape cookie injection | Bypasses YouTube datacenter IP blocking & bot challenges |

---

### 📋 Step-by-Step EC2 Deployment Walkthrough

#### 1. Launch & Configure the EC2 Instance

1. In the **AWS Management Console**, navigate to **EC2 > Launch Instance**.
2. **Name**: `Musicon-Production-Bot`
3. **AMI**: Ubuntu Server 24.04 LTS or 22.04 LTS (64-bit x86).
4. **Instance Type**: `t3.small` (2 vCPU, 2 GiB Memory).
5. **Key Pair**: Select or generate an SSH key pair (`.pem` format).
6. **Network Settings (Security Group)**:
   - **Inbound Rules**: 
     - `SSH (TCP 22)` from `My IP` (or restricted CIDR for security).
   - **Outbound Rules**:
     - `All traffic (0.0.0.0/0)` (Required for Discord Gateway WebSocket, voice UDP, YouTube streams, and Spotify API).
7. **Storage**: `20 GiB gp3`.
8. Click **Launch Instance**.

#### 2. Connect to Your EC2 Instance via SSH

```bash
chmod 400 your-key.pem
ssh -i "your-key.pem" ubuntu@<YOUR_EC2_PUBLIC_IP_OR_DNS>
```

#### 3. Update System Packages & Install FFmpeg

Run the following commands on your EC2 instance:

```bash
# Update repositories and upgrade packages
sudo apt update && sudo apt upgrade -y

# Install essential packages, Python 3, venv, Git, and FFmpeg
sudo apt install -y python3 python3-pip python3-venv ffmpeg git curl

# Verify FFmpeg installation
ffmpeg -version
```

#### 4. Configure Swap Memory (Recommended for `t3.small`)

The `t3.small` instance features 2 GB of physical RAM. To prevent sudden Out-Of-Memory (OOM) process termination during heavy FFmpeg transcoding or multi-track queueing, configure a 2 GB swap file:

```bash
sudo fallocate -l 2G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile
echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab

# Verify swap activation
free -h
```

#### 5. Clone the Repository & Setup Virtual Environment

```bash
# Navigate to home directory and clone repository
cd /home/ubuntu
git clone https://github.com/yparshant610/Musicon.git
cd Musicon

# Create virtual environment
python3 -m venv dc_env

# Activate virtual environment
source dc_env/bin/activate

# Upgrade pip and install dependencies
pip install --upgrade pip
pip install -r requirements.txt
```

#### 6. Transfer `.env` and `youtube_cookies.txt` from Local Machine

> [!IMPORTANT]
> Because cloud datacenter IPs (like AWS EC2) are frequently challenged with YouTube's *"Sign in to confirm you're not a bot"* page, transferring `youtube_cookies.txt` is essential for 24/7 stream stability.

From your **local terminal** (Windows PowerShell or macOS/Linux):

```bash
# Transfer .env file
scp -i "your-key.pem" .env ubuntu@<YOUR_EC2_PUBLIC_IP>:/home/ubuntu/Musicon/.env

# Transfer youtube_cookies.txt
scp -i "your-key.pem" youtube_cookies.txt ubuntu@<YOUR_EC2_PUBLIC_IP>:/home/ubuntu/Musicon/youtube_cookies.txt
```

#### 7. Set Production Mode in `MyBot.py`

On your EC2 instance, ensure [MyBot.py](file:///d:/bot%20discord/MyBot.py) has global command synchronization enabled:

```python
DEVELOPMENT_MODE = False  # Set to False to register slash commands globally
```

#### 8. Configure & Enable Systemd Service (24/7 Daemon)

Musicon includes a ready-to-use [`musicon.service`](file:///d:/bot%20discord/musicon.service) configuration file in the project root.

Copy the service file to the system directory:

```bash
sudo cp /home/ubuntu/Musicon/musicon.service /etc/systemd/system/musicon.service
```

> **Service File Contents** ([musicon.service](file:///d:/bot%20discord/musicon.service)):
> ```ini
> [Unit]
> Description=Musicon Discord Music Bot (24/7 Production)
> After=network.target
> 
> [Service]
> Type=simple
> User=ubuntu
> WorkingDirectory=/home/ubuntu/Musicon
> ExecStart=/home/ubuntu/Musicon/dc_env/bin/python3 MyBot.py
> Restart=always
> RestartSec=5
> StandardOutput=journal
> StandardError=journal
> Environment=PYTHONUNBUFFERED=1
> 
> [Install]
> WantedBy=multi-user.target
> ```

Reload systemd daemon, enable auto-start on boot, and start Musicon:

```bash
# Reload systemd daemon
sudo systemctl daemon-reload

# Enable service to start automatically on EC2 reboot
sudo systemctl enable musicon

# Start the bot
sudo systemctl start musicon

# Check service status
sudo systemctl status musicon
```

---

### 📊 Managing the 24/7 Service & Live Logs

| Action | Command |
| :--- | :--- |
| **Check bot status** | `sudo systemctl status musicon` |
| **View live logs (real-time)** | `sudo journalctl -u musicon -f` |
| **View last 100 log lines** | `sudo journalctl -u musicon -n 100 --no-pager` |
| **Restart the bot** | `sudo systemctl restart musicon` |
| **Stop the bot** | `sudo systemctl stop musicon` |

---

### 🔄 Updating the Bot & Dependencies on EC2

To pull code updates and restart the bot seamlessly:

```bash
cd /home/ubuntu/Musicon
git pull origin main
source dc_env/bin/activate
pip install --upgrade -r requirements.txt
sudo systemctl restart musicon
```

#### Auto-updating `yt-dlp` (Prevent YouTube stream breaks)

YouTube updates their player signatures often. To ensure zero playback disruption, set up a weekly cron job on EC2 to keep `yt-dlp` updated:

```bash
crontab -e
```

Add the following line to update `yt-dlp` every Sunday at 4:00 AM UTC and restart the bot:

```cron
0 4 * * 0 /home/ubuntu/Musicon/dc_env/bin/pip install --upgrade yt-dlp && sudo systemctl restart musicon
```

---

## 💻 Local Development

If you prefer testing or developing features on your local machine before pushing to AWS EC2:

1. Follow the [Installation](#-installation) steps.
2. Set `DEVELOPMENT_MODE = True` and set `TEST_GUILD_ID` in [MyBot.py](file:///d:/bot%20discord/MyBot.py) for instant slash command synchronization.
3. Start the bot:
   ```bash
   python MyBot.py
   ```

---

## ❓ Troubleshooting

<details>
<summary><b>1. "Sign in to confirm you're not a bot" error from YouTube</b></summary>

YouTube frequently challenges data centers (e.g., AWS EC2, GCP, Hetzner). Ensure you have exported fresh cookies using the [YouTube Cookie Bypass](#-youtube-cookie-bypass) section and verified that `YOUTUBE_COOKIE_FILE` is set properly in `.env`.
</details>

<details>
<summary><b>2. "FFmpeg was not found" warning on startup</b></summary>

Ensure FFmpeg is installed and accessible either globally via your system `PATH` or located at `bin/ffmpeg/ffmpeg.exe`. You can test this by running `ffmpeg -version` in your terminal.
</details>

<details>
<summary><b>3. Slash commands do not appear in my server</b></summary>

- If `DEVELOPMENT_MODE = True`, make sure `TEST_GUILD_ID` matches your testing server ID.
- If `DEVELOPMENT_MODE = False`, Discord global command propagation can take anywhere from a few minutes up to an hour for brand-new applications.
- Re-invite the bot with the `applications.commands` scope checked.
</details>

<details>
<summary><b>4. Bot disconnects immediately after joining</b></summary>

Check your Discord voice region settings or server bitrate. If the bot is the only member left in the voice channel, Musicon gracefully disconnects to conserve resources.
</details>

---

## 🤝 Contributing

Contributions, bug reports, and feature requests are warmly welcomed!

1. Fork the Project
2. Create your Feature Branch (`git checkout -b feature/AmazingFeature`)
3. Commit your Changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the Branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

---

## 📄 License

Distributed under the **MIT License**. See `LICENSE` for more information.

---

<div align="center">
  <sub>Crafted with passion for music and code by <a href="https://github.com/yparshant610">yparshant610</a>.</sub>
</div>
