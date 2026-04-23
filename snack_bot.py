"""
🍪 Snack Expiry Reminder Bot
============================
This bot watches your Telegram group for messages like:
  "Oreos, 2026-05-10"
It saves them and sends you a reminder 7 days before they expire.
If you include a photo, it will send that photo back in the reminder too.
"""

import os
import json
import asyncio
from datetime import datetime, timedelta
from telegram import Update, Bot
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    filters,
    ContextTypes,
)

# ─────────────────────────────────────────
# CONFIGURATION — fill these in!
# ─────────────────────────────────────────

BOT_TOKEN = "8650760048:AAFGmhHsoOEoqZ5l948a-pd018yDh3qsy1U"   # From BotFather (Step 1)
GROUP_CHAT_ID = "-5226491280" # You'll find this in Step 4

# How many days before expiry to send the reminder
DAYS_BEFORE = 7

# File where snack data is saved (no database needed!)
DATA_FILE = "snacks.json"

# ─────────────────────────────────────────
# DATA HELPERS — saving & loading snacks
# ─────────────────────────────────────────

def load_snacks():
    """Load the list of snacks from the file. Returns empty list if none yet."""
    if not os.path.exists(DATA_FILE):
        return []
    with open(DATA_FILE, "r") as f:
        return json.load(f)

def save_snacks(snacks):
    """Save the list of snacks to the file."""
    with open(DATA_FILE, "w") as f:
        json.dump(snacks, f, indent=2)

# ─────────────────────────────────────────
# MESSAGE HANDLER — reads your group messages
# ─────────────────────────────────────────

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    This runs every time someone sends a message in your group.
    It looks for the pattern:  Snack Name, YYYY-MM-DD
    It also checks if a photo was attached.
    """
    message = update.message
    if message is None:
        return

    # Get the text — check caption (used when photo is sent) or plain text
    text = message.caption or message.text or ""
    text = text.strip()

    # Try to find a date in the message
    # We look for something like:  Oreos, 2026-05-10
    snack_name = None
    expiry_date = None
    photo_file_id = None

    # Split by comma
    if "," in text:
        parts = text.split(",", 1)  # split only on the FIRST comma
        possible_name = parts[0].strip()
        possible_date = parts[1].strip()

        # Try to read the date (must be YYYY-MM-DD format)
        try:
            expiry_date = datetime.strptime(possible_date, "%Y-%m-%d").date()
            snack_name = possible_name
        except ValueError:
            # Date wasn't in the right format — ignore this message
            pass

    # If we found a valid snack name and date, save it!
    if snack_name and expiry_date:
        # Check if there's a photo attached
        if message.photo:
            # Telegram gives multiple sizes — we take the largest (last one)
            photo_file_id = message.photo[-1].file_id

        # Load existing snacks, add the new one, save
        snacks = load_snacks()
        snacks.append({
            "name": snack_name,
            "expiry": str(expiry_date),       # stored as text like "2026-05-10"
            "photo_file_id": photo_file_id,   # None if no photo
            "chat_id": message.chat_id,
            "added_on": str(datetime.now().date()),
        })
        save_snacks(snacks)

        # Reply to confirm
        days_left = (expiry_date - datetime.now().date()).days
        photo_note = " 📸 Photo saved too!" if photo_file_id else ""
        await message.reply_text(
            f"✅ Got it! I'll remind you about **{snack_name}** "
            f"on **{expiry_date - timedelta(days=DAYS_BEFORE)}** "
            f"(7 days before it expires on {expiry_date}).\n"
            f"That's {days_left} days away.{photo_note}",
            parse_mode="Markdown"
        )

# ─────────────────────────────────────────
# /list COMMAND — shows all saved snacks
# ─────────────────────────────────────────

async def list_snacks(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send the user a list of all saved snacks when they type /list"""
    snacks = load_snacks()
    if not snacks:
        await update.message.reply_text("📭 No snacks saved yet! Send me one like:\nOreos, 2026-05-10")
        return

    today = datetime.now().date()
    lines = ["🍪 **Your saved snacks:**\n"]
    for s in snacks:
        expiry = datetime.strptime(s["expiry"], "%Y-%m-%d").date()
        days_left = (expiry - today).days
        photo_icon = "📸 " if s.get("photo_file_id") else ""
        if days_left < 0:
            status = "⚠️ EXPIRED"
        elif days_left <= DAYS_BEFORE:
            status = f"🔴 Expires SOON ({days_left} days)"
        else:
            status = f"✅ {days_left} days left"
        lines.append(f"{photo_icon}• **{s['name']}** — {s['expiry']} ({status})")

    await update.message.reply_text("\n".join(lines), parse_mode="Markdown")

# ─────────────────────────────────────────
# /delete COMMAND — removes a snack by name
# ─────────────────────────────────────────

async def delete_snack(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Remove a snack. Usage: /delete Oreos
    """
    if not context.args:
        await update.message.reply_text("Usage: /delete SnackName\nExample: /delete Oreos")
        return

    name_to_delete = " ".join(context.args).strip()
    snacks = load_snacks()
    new_snacks = [s for s in snacks if s["name"].lower() != name_to_delete.lower()]

    if len(new_snacks) == len(snacks):
        await update.message.reply_text(f"❌ Couldn't find a snack named '{name_to_delete}'.\nCheck the spelling or use /list to see saved snacks.")
    else:
        save_snacks(new_snacks)
        await update.message.reply_text(f"🗑️ Removed **{name_to_delete}** from the list.", parse_mode="Markdown")

# ─────────────────────────────────────────
# /start COMMAND — welcome message
# ─────────────────────────────────────────

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 Hi! I'm your **Snack Expiry Bot**!\n\n"
        "To track a snack, send a message like:\n"
        "  `Oreos, 2026-05-10`\n\n"
        "You can also attach a **photo** with the message!\n\n"
        "📋 Commands:\n"
        "/list — See all saved snacks\n"
        "/delete Oreos — Remove a snack\n"
        "/checktoday — Manually check for upcoming expiries",
        parse_mode="Markdown"
    )

# ─────────────────────────────────────────
# REMINDER CHECKER — runs every day
# ─────────────────────────────────────────

async def check_expiries(context: ContextTypes.DEFAULT_TYPE):
    """
    This runs automatically every day.
    It checks if any snack is expiring in exactly 7 days.
    If so, it sends a reminder to your group.
    """
    bot: Bot = context.bot
    snacks = load_snacks()
    today = datetime.now().date()
    reminder_date = today + timedelta(days=DAYS_BEFORE)

    for snack in snacks:
        expiry = datetime.strptime(snack["expiry"], "%Y-%m-%d").date()

        # Only remind if today is exactly 7 days before expiry
        if expiry == reminder_date:
            chat_id = snack.get("chat_id") or GROUP_CHAT_ID
            message_text = (
                f"⏰ **Expiry Reminder!**\n\n"
                f"🍪 **{snack['name']}** expires in **{DAYS_BEFORE} days** "
                f"on {snack['expiry']}!\n\n"
                f"Time to eat it or toss it! 🗑️"
            )

            if snack.get("photo_file_id"):
                # Send photo with the reminder text as caption
                await bot.send_photo(
                    chat_id=chat_id,
                    photo=snack["photo_file_id"],
                    caption=message_text,
                    parse_mode="Markdown"
                )
            else:
                # Just send a text reminder
                await bot.send_message(
                    chat_id=chat_id,
                    text=message_text,
                    parse_mode="Markdown"
                )

# ─────────────────────────────────────────
# /checktoday COMMAND — manually trigger check
# ─────────────────────────────────────────

async def check_today(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Lets you manually trigger the expiry check anytime."""
    await check_expiries(context)
    await update.message.reply_text("🔍 Checked! Any reminders due today have been sent.")

# ─────────────────────────────────────────
# MAIN — starts the bot
# ─────────────────────────────────────────

def main():
    print("🤖 Starting Snack Expiry Bot...")
    print(f"📅 Reminders will be sent {DAYS_BEFORE} days before expiry.")
    print("Press Ctrl+C to stop.\n")

    # Build the bot app
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    # Register commands
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("list", list_snacks))
    app.add_handler(CommandHandler("delete", delete_snack))
    app.add_handler(CommandHandler("checktoday", check_today))

    # Register message handler (catches text AND photos with captions)
    app.add_handler(MessageHandler(
        filters.TEXT | filters.PHOTO,
        handle_message
    ))

    # Schedule daily check at 9:00 AM
    app.job_queue.run_daily(
        check_expiries,
        time=datetime.strptime("09:00", "%H:%M").time(),
        name="daily_expiry_check"
    )

    print("✅ Bot is running! Go send a message in your Telegram group.")
    app.run_polling()

if __name__ == "__main__":
    main()
