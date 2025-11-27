import os
from flask import Flask, request
import discord
from discord.ext import commands
import json
import hmac
import hashlib

app = Flask(__name__)

# Environment variables (set these in Railway)
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
GITHUB_SECRET = os.getenv("GITHUB_SECRET", "")
CHANNEL_ID = 1443210803414044704
SITE_URL = "superheavybooster.github.io/Booster-16-Space-Exploration-Technologies-Corporation"  # CHANGE THIS to your site URL

# Initialize Discord bot
intents = discord.Intents.default()
bot = commands.Bot(command_prefix="!", intents=intents)

@bot.event
async def on_ready():
    print(f"Bot logged in as {bot.user}")

def verify_github_signature(request_data, signature):
    """Verify that the webhook came from GitHub"""
    if not GITHUB_SECRET:
        return True
    
    payload_body = request.get_data()
    expected_signature = hmac.new(
        GITHUB_SECRET.encode(),
        payload_body,
        hashlib.sha256
    ).hexdigest()
    
    return hmac.compare_digest(expected_signature, signature.replace("sha256=", ""))

@app.route("/webhook", methods=["POST"])
def github_webhook():
    """Receive GitHub webhook and post to Discord"""
    
    # Verify GitHub signature
    signature = request.headers.get("X-Hub-Signature-256", "")
    if not verify_github_signature(request, signature):
        return {"error": "Invalid signature"}, 401
    
    data = request.json
    
    # Only process push events
    if data.get("action") == "closed" or "head_commit" not in data:
        return {"status": "ignored"}, 200
    
    # Extract commit info
    commits = data.get("commits", [])
    if not commits:
        return {"status": "no commits"}, 200
    
    commit = commits[-1]  # Get the latest commit
    commit_message = commit.get("message", "No message").split("\n")[0]  # First line only
    commit_url = commit.get("url", "")
    
    # Create and send Discord message
    async def send_message():
        channel = bot.get_channel(CHANNEL_ID)
        if channel:
            embed = discord.Embed(
                title="🚀 Site Update",
                description=commit_message,
                color=discord.Color.blue()
            )
            embed.add_field(
                name="Repository",
                value=f"[{data.get('repository', {}).get('full_name', 'Unknown')}]({data.get('repository', {}).get('html_url', '')})",
                inline=False
            )
            embed.add_field(
                name="Commit",
                value=f"[View on GitHub]({commit_url})",
                inline=True
            )
            embed.add_field(
                name="Check it out",
                value=f"[Visit Site]({SITE_URL})",
                inline=True
            )
            await channel.send(embed=embed)
    
    # Schedule the message to be sent
    bot.loop.create_task(send_message())
    
    return {"status": "success"}, 200

@app.route("/", methods=["GET"])
def home():
    return {"status": "Bot is running"}, 200

if __name__ == "__main__":
    # Run Flask and Discord bot together
    import threading
    
    flask_thread = threading.Thread(target=lambda: app.run(host="0.0.0.0", port=5000))
    flask_thread.daemon = True
    flask_thread.start()
    
    bot.run(DISCORD_TOKEN)
  
