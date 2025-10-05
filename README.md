DJ Bot — Deployable Telegram Streaming Bot (mini-app)

Contents:
- server.py        : FastAPI server that controls FFmpeg and broadcasts audio to listeners at /stream
- bot.py           : Telegram bot that calls server control endpoints to start/stop stream and post player link
- player.html      : Lightweight WebApp player (opens inside Telegram) at /player.html
- config.json      : Generated on first run; edit to add your BOT_TOKEN, CHANNEL_ID, SERVER_URL, and FFmpeg command
- requirements.txt : Python dependencies

Quickstart (local):
0. Install ffmpeg on your machine. On Debian/Ubuntu: sudo apt install ffmpeg
1. Extract the zip and open a terminal in the folder.
2. Edit config.json and set BOT_TOKEN, CHANNEL_ID (or chat id), and SERVER_URL (e.g., http://your-ip:8000)
   - The default ffmpeg command in config.json is for Linux PulseAudio ("default").
   - For macOS use avfoundation: ["ffmpeg","-f","avfoundation","-i",":0","-vn","-acodec","libmp3lame","-b:a","128k","-f","mp3","pipe:1"]
   - For Windows using dshow: ["ffmpeg","-f","dshow","-i","audio=Stereo Mix (Realtek(R) Audio)","-vn","-acodec","libmp3lame","-b:a","128k","-f","mp3","pipe:1"]
3. Install Python deps:
   python3 -m pip install -r requirements.txt
4. Start the server:
   python server.py
5. In another terminal, run the bot:
   python bot.py
6. In Telegram, as the bot user (or an admin), send /startdj to the bot to start streaming and auto-post the Listen button.
7. Click the Listen button in Telegram to open the mini player (player.html). Listeners will hear the DJ's system audio.

Important notes & limitations:
- Mobile system audio capture is limited. To capture system audio on iOS/Android you'll need a native app and ReplayKit/MediaProjection.
- Re-streaming commercial services (Spotify/YouTube) may violate Terms of Service and copyright; obtain licensing if streaming to a public audience.
- This implementation is a simple MVP. For scale, replace the ffmpeg->broadcast design with an SFU (LiveKit) and a TURN server.
