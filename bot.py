# bot.py
# Telegram bot that controls the streaming server via HTTP control endpoints.
# Usage: configure config.json with BOT_TOKEN and CHANNEL_ID and SERVER_URL, then run `python bot.py`.
import os, requests, json, asyncio
from telegram import InlineKeyboardMarkup, InlineKeyboardButton, Update
from telegram.ext import Application, CommandHandler, ContextTypes

CONFIG_PATH = os.path.join(os.path.dirname(__file__), "config.json")
if os.path.exists(CONFIG_PATH):
    with open(CONFIG_PATH,"r") as f:
        cfg = json.load(f)
else:
    cfg = {
        "BOT_TOKEN": "REPLACE_WITH_YOUR_BOT_TOKEN",
        "CHANNEL_ID": "@your_channel_or_chat_id",
        "SERVER_URL": "http://localhost:8000"
    }
    with open(CONFIG_PATH,"w") as f:
        json.dump(cfg,f,indent=2)

BOT_TOKEN = cfg.get("BOT_TOKEN")
CHANNEL_ID = cfg.get("CHANNEL_ID")
SERVER_URL = cfg.get("SERVER_URL").rstrip("/")

if BOT_TOKEN == "REPLACE_WITH_YOUR_BOT_TOKEN":
    print("Please edit config.json and add your bot token and channel id (or chat id).")
    exit(1)

async def startdj(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Call server to start ffmpeg stream
    r = requests.post(f"{SERVER_URL}/control/start", timeout=10)
    data = r.json()
    if not data.get("ok"):
        await update.message.reply_text(f"Could not start stream: {data.get('msg')}")
        return
    # Post to channel with Listen button
    player_url = f"{SERVER_URL}/player.html"
    keyboard = InlineKeyboardMarkup([[InlineKeyboardButton("▶️ Listen Live", url=player_url)]])
    await context.bot.send_message(chat_id=CHANNEL_ID, text="🎧 DJ is LIVE! Click to open player:", reply_markup=keyboard)
    await update.message.reply_text("Stream started and link posted.")

async def stopdj(update: Update, context: ContextTypes.DEFAULT_TYPE):
    r = requests.post(f"{SERVER_URL}/control/stop", timeout=10)
    data = r.json()
    if not data.get("ok"):
        await update.message.reply_text(f"Error stopping: {data.get('msg')}")
        return
    await update.message.reply_text("Stream stopped.")

async def song(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = " ".join(context.args)
    if not text:
        await update.message.reply_text("Usage: /song Artist - Title")
        return
    r = requests.post(f"{SERVER_URL}/metadata", json={"song": text}, timeout=10)
    await update.message.reply_text(f"Metadata updated: {text}")

async def announce(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # simple announce without starting stream
    player_url = f"{SERVER_URL}/player.html"
    keyboard = InlineKeyboardMarkup([[InlineKeyboardButton("▶️ Listen Live", url=player_url)]])
    await context.bot.send_message(chat_id=CHANNEL_ID, text="🔔 DJ link: Click to open player", reply_markup=keyboard)
    await update.message.reply_text("Announced link.")

def main():
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("startdj", startdj))
    app.add_handler(CommandHandler("stopdj", stopdj))
    app.add_handler(CommandHandler("song", song))
    app.add_handler(CommandHandler("announce", announce))
    print("Bot started. Listening for commands.")
    app.run_polling()

if __name__ == "__main__":
    main()
