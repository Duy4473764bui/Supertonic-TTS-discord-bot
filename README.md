# Discord TTS Bot 🔊

A production-ready Discord bot that automatically reads messages from a configured text channel aloud into a voice channel using **Supertonic TTS** (Vietnamese voice by default).

---

## Table of Contents

1. [Features](#features)
2. [Project Structure](#project-structure)
3. [Prerequisites](#prerequisites)
4. [Installation](#installation)
5. [FFmpeg Setup](#ffmpeg-setup)
6. [Supertonic Setup](#supertonic-setup)
7. [Discord Bot Setup](#discord-bot-setup)
8. [Configuration](#configuration)
9. [Running the Bot](#running-the-bot)
10. [Usage](#usage)
11. [Troubleshooting](#troubleshooting)

---

## Features

- **`/join` slash command** – Anyone can invite the bot to their voice channel.
- **Single-channel listener** – Only reads from the one text channel you configure.
- **FIFO audio queue** – Messages play in order with no overlapping audio.
- **Auto-disconnect** – Leaves the voice channel as soon as no humans remain.
- **Temp file cleanup** – WAV files are deleted immediately after playback.
- **Fully async** – Built on `discord.py 2.x` and `asyncio`, zero blocking calls on the event loop.
- **Clean architecture** – Cogs, core modules, and config are strictly separated.

---

## Project Structure

```
discord-tts-bot/
├── main.py            # Bot entry point
├── config.py          # All runtime configuration
├── requirements.txt
├── README.md
├── audio/             # Temp WAV files (auto-created, auto-cleaned)
├── cogs/
│   ├── join.py        # /join slash command
│   └── listener.py    # on_message handler → TTS queue
└── core/
    ├── tts.py         # Supertonic wrapper
    ├── voice.py       # VoiceManager (connect, play, monitor)
    ├── queue.py       # TTSQueue (asyncio.Queue wrapper)
    └── utils.py       # Text sanitisation, logging setup
```

---

## Prerequisites

| Requirement | Version |
|---|---|
| Python | 3.11 or newer |
| FFmpeg | 4.x or newer |
| Supertonic | Latest |
| discord.py | 2.3 or newer |

---

## Installation

### 1. Clone the repository

```bash
git clone https://github.com/yourname/discord-tts-bot.git
cd discord-tts-bot
```

### 2. Create a virtual environment

```bash
python -m venv .venv

# Linux / macOS
source .venv/bin/activate

# Windows
.venv\Scripts\activate
```

### 3. Install Python dependencies

```bash
pip install -r requirements.txt
```

---

## FFmpeg Setup

FFmpeg is required to stream audio to Discord.

### Linux (Ubuntu / Debian)

```bash
sudo apt update && sudo apt install ffmpeg -y
```

### macOS (Homebrew)

```bash
brew install ffmpeg
```

### Windows

1. Download a static build from <https://ffmpeg.org/download.html> (e.g. **gyan.dev** release).
2. Extract to `C:\ffmpeg\`.
3. Set `FFMPEG_PATH` in `config.py`:

```python
FFMPEG_PATH = r"C:\ffmpeg\bin\ffmpeg.exe"
```

Or add `C:\ffmpeg\bin` to your system `PATH` and leave `FFMPEG_PATH = "ffmpeg"`.

### Verify

```bash
ffmpeg -version
```

---

## Supertonic Setup

Supertonic is the TTS engine used to generate Vietnamese speech.

### Install

```bash
pip install supertonic
```

The first run will download the TTS model (~200 MB).  Subsequent runs use the cached model.

### Verify

```python
from supertonic import TTS
tts = TTS(language="vi")
tts.tts_to_file(text="Xin chào!", file_path="test.wav")
```

Play `test.wav` to confirm Vietnamese speech was generated.

> **Note:** If you want a different language, change `VOICE_LANGUAGE` in `config.py` and check Supertonic's documentation for supported locale codes.

---

## Discord Bot Setup

### 1. Create a bot application

1. Go to <https://discord.com/developers/applications> and click **New Application**.
2. Name your app, then navigate to **Bot → Add Bot**.
3. Under **Token**, click **Reset Token** and copy it. Keep it secret!

### 2. Enable Privileged Intents

Still on the **Bot** page, enable:

- ✅ **Server Members Intent** – needed to detect humans vs bots in voice channels.
- ✅ **Message Content Intent** – needed to read message text.

### 3. Invite the bot to your server

Build an OAuth2 URL with these scopes and permissions:

- **Scopes:** `bot`, `applications.commands`
- **Bot Permissions:** `Connect`, `Speak`, `Send Messages`, `Read Message History`, `View Channels`

Example URL template (replace `CLIENT_ID`):

```
https://discord.com/api/oauth2/authorize?client_id=CLIENT_ID&permissions=3148800&scope=bot%20applications.commands
```

### 4. Enable Developer Mode (to copy IDs)

In Discord: **User Settings → Advanced → Developer Mode → ON**.  
Then right-click any channel or user to copy their ID.

---

## Configuration

Edit `config.py` **or** set the matching environment variables.

| Setting | Env Variable | Default | Description |
|---|---|---|---|
| `TOKEN` | `DISCORD_TOKEN` | `""` | Your bot token |
| `TEXT_CHANNEL_ID` | `TEXT_CHANNEL_ID` | `0` | ID of the text channel to read |
| `VOICE_LANGUAGE` | `VOICE_LANGUAGE` | `"vi"` | TTS language code |
| `VOICE_SPEAKER` | `VOICE_SPEAKER` | `""` | Supertonic speaker ID (optional) |
| `FFMPEG_PATH` | `FFMPEG_PATH` | `"ffmpeg"` | Path to ffmpeg binary |
| `QUEUE_MAX_SIZE` | — | `50` | Max messages in TTS queue |
| `EMPTY_CHANNEL_CHECK_INTERVAL` | — | `5.0` | Seconds between empty-channel checks |
| `AUDIO_TMP_DIR` | — | `./audio` | Temp WAV file directory |

### Using environment variables (recommended for production)

```bash
export DISCORD_TOKEN="your-bot-token"
export TEXT_CHANNEL_ID="1234567890123456789"
export VOICE_LANGUAGE="vi"
export FFMPEG_PATH="/usr/bin/ffmpeg"

python main.py
```

Or with a `.env` file + `python-dotenv`:

```bash
pip install python-dotenv
```

Add to the top of `main.py`:

```python
from dotenv import load_dotenv
load_dotenv()
```

---

## Running the Bot

```bash
python main.py
```

You should see output like:

```
2024-01-01 12:00:00  INFO      TTSBot: logged in as TTS Bot#1234 (id=123456789).
2024-01-01 12:00:00  INFO      TTSBot: synced 1 slash command(s).
2024-01-01 12:00:00  INFO      TTSBot: monitoring text channel '#general-tts' (id=1234567890).
2024-01-01 12:00:00  INFO      TTSBot: ready and waiting for /join commands.
```

---

## Usage

1. **Join a voice channel** in your Discord server.
2. Type `/join` in any text channel.
3. The bot joins your voice channel and confirms.
4. Send messages in the configured text channel — the bot reads them aloud in order.
5. When everyone leaves the voice channel, the bot disconnects automatically.

---

## Troubleshooting

### Bot doesn't respond to `/join`

- Slash commands can take **up to 1 hour** to appear globally after the first sync.
- Check that the bot has the `applications.commands` scope.
- For instant updates during development, sync to a specific guild:
  ```python
  # In main.py → on_ready, replace:
  synced = await self.tree.sync()
  # with:
  guild = discord.Object(id=YOUR_GUILD_ID)
  self.tree.copy_global_to(guild=guild)
  synced = await self.tree.sync(guild=guild)
  ```

### `Message Content Intent` error

Enable the **Message Content Intent** in the Developer Portal → Bot → Privileged Gateway Intents.

### `No module named 'nacl'`

```bash
pip install PyNaCl
```

### FFmpeg not found

Set the full path in `config.py`:

```python
FFMPEG_PATH = "/usr/bin/ffmpeg"          # Linux
FFMPEG_PATH = r"C:\ffmpeg\bin\ffmpeg.exe"  # Windows
```

### Supertonic model download fails

Ensure you have internet access and disk space (~200 MB).  
Try running the verification script in the [Supertonic Setup](#supertonic-setup) section.

### Bot joins but no audio plays

- Check that the bot has **Connect** and **Speak** permissions in the voice channel.
- Verify FFmpeg works independently: `ffmpeg -i test.wav -f null -`.
- Check the console for `ERROR` lines containing `FFmpeg playback error`.

### Audio cuts out or stutters

Increase buffer size by adjusting `FFMPEG_BEFORE_OPTIONS` in `config.py`:

```python
FFMPEG_BEFORE_OPTIONS = "-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5 -bufsize 512k"
```

### Messages are skipped

The queue has a maximum size (`QUEUE_MAX_SIZE`).  If it fills up, new messages are dropped.
Increase the limit in `config.py` or reduce the verbosity of your text channel.

---

## License

MIT — do whatever you want, no warranty provided.
