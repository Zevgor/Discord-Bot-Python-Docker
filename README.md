# Discord Bot Python Docker

A Discord music and utility bot built with Python, designed to run in a Docker container. This bot supports music playback from YouTube, music queue management and basic voice channel controls.

## Features
- Play music from YouTube (search or direct URL)
- Queue management (play, skip, pause, resume, stop, leave)
- WoW Token price lookup via Blizzard API
- Session management for multiple guilds/channels
- Dockerized for easy deployment

## Requirements
- Python 3.9+
- Docker
- Discord Bot Token
- Blizzard API Credentials
- YouTube-dl/yt-dlp

## Setup

### First, configure environment variables
Create a `.env` file in the project root with the following:
```
DISCORD_TOKEN=your_discord_token
DISCORD_CHANNELS=channel1,channel2   <-- Channels the Bot will listen to
BATTLENET_CLIENT=your_blizzard_client_id
BATTLENET_SECRET=your_blizzard_client_secret
```

### Then, run the docker-compose.yml file.

## Usage
- `.play <song name or YouTube URL>`: Play a song or add to queue
- `.next` or `.skip`: Skip to next song
- `.queue` or `.q`: Show current queue
- `.pause`: Pause playback
- `.resume`: Resume playback
- `.stop`: Stop and clear queue
- `.leave`: Disconnect bot from voice channel
- `.wt`: Get current WoW Token price

## File Structure
```
app/
  bot.py         # Main bot logic
  utilities.py   # Session and queue management
requirements.txt # Python dependencies
Dockerfile       # Docker build instructions
docker-compose.yml # Docker Compose config
```

## Notes
- Only works in allowed channels specified in `DISCORD_CHANNELS`.
- Requires FFmpeg for audio streaming.
- Make sure your bot has the necessary Discord permissions (voice, messages).

## License
MIT
