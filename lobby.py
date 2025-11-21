import logging
import asyncio
from telegram import (
    Update, InlineKeyboardButton, InlineKeyboardMarkup, User
)
from telegram.ext import (
    ApplicationBuilder, CommandHandler, CallbackQueryHandler, ContextTypes, MessageHandler, filters
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ============================
# GLOBAL DATA
# ============================
lobby_data = {
    "team_a": [],
    "team_b": [],
    "max_team_size": 5,
    "chat_id": None,
    "message_id": None,
    "maps": [],
    "format": None,
    "match_time": None,
    "ready_users": set(),
    "server_link": None
}

ADMIN_ID = 403798834
GROUP_CHAT_ID = -1003339482869
MATCH_TIMES = [f"{h:02d}:00" for h in range(13, 24)] + ["00:00", "Vaqtni kelishamiz"]
ALL_MAPS = ["Dust2", "Mirage", "Inferno","Nuke","Ancient","Anubis","Overpass","Train"]

# ============================
# /start
# ============================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [[InlineKeyboardButton("🎮 Lobby yaratish", callback_data="create_lobby")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        "👋 Salom! CS2 da lobby yarat yoki qo'shilish uchun link ol!",
        reply_markup=reply_markup
    )

# ============================
# CREATE LOBBY
# ============================
async def create_lobby_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if query: await query.answer()
    context.user_data.clear()

    keyboard = [
        [InlineKeyboardButton("1x1", callback_data="format_1x1"),
         InlineKeyboardButton("2x2", callback_data="format_2x2"),
         InlineKeyboardButton("3x3", callback_data="format_3x3")],
        [InlineKeyboardButton("4x4", callback_data="format_4x4"),
         InlineKeyboardButton("5x5", callback_data="format_5x5")],
        [InlineKeyboardButton("🔫 Retake", callback_data="format_retake"),
         InlineKeyboardButton("🎉 Fun Maps", callback_data="format_fun")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    text = "➕ *Lobby yaratish boshlandi*\n1️⃣ Match formatini tanlang:"
    if query:
        await query.edit_message_text(text=text, reply_markup=reply_markup, parse_mode="Markdown")
    else:
        await update.message.reply_text(text=text, reply_markup=reply_markup, parse_mode="Markdown")

# ============================
# FORMAT SELECTED → MAP
# ============================
async def format_selected(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    selected_format = query.data.replace("format_", "")
    context.user_data["format"] = selected_format

    if selected_format in ["1x1","2x2","3x3","4x4","5x5"]:
        lobby_data["max_team_size"] = int(selected_format[0])
    else:
        lobby_data["max_team_size"] = 5

    keyboard = []
    for m in ALL_MAPS: keyboard.append([InlineKeyboardButton(m, callback_data=f"map_{m}")])
    keyboard.append([InlineKeyboardButton("✅ Tugatish", callback_data="maps_done")])
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(
        f"Format tanlandi: *{selected_format.upper()}* ✅\n2️⃣ Xarita tanlang:",
        reply_markup=reply_markup,
        parse_mode="Markdown"
    )

# ============================
# MAP SELECTION
# ============================
async def map_selection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    map_choice = query.data.replace("map_", "")
    if "maps" not in context.user_data:
        context.user_data["maps"] = []

    if map_choice not in context.user_data["maps"]:
        context.user_data["maps"].append(map_choice)

    keyboard = []
    for m in ALL_MAPS:
        if m not in context.user_data["maps"]:
            keyboard.append([InlineKeyboardButton(m, callback_data=f"map_{m}")])
    keyboard.append([InlineKeyboardButton("✅ Tugatish", callback_data="maps_done")])
    reply_markup = InlineKeyboardMarkup(keyboard)

    maps_selected = ", ".join(context.user_data["maps"]) or "-"
    await query.edit_message_text(
        f"📋 Tanlangan xaritalar: {maps_selected}\nBoshqa xaritalarni tanlang yoki ✅ Tugatish tugmasini bosing",
        reply_markup=reply_markup
    )

# ============================
# MAP DONE → MATCH TIME
# ============================
async def map_selection_done(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    keyboard = []
    row=[]
    for t in MATCH_TIMES:
        row.append(InlineKeyboardButton(t, callback_data=f"time_{t}"))
        if len(row)==3:
            keyboard.append(row)
            row=[]
    if row: keyboard.append(row)
    reply_markup = InlineKeyboardMarkup(keyboard)

    maps_selected = ", ".join(context.user_data.get("maps", []))
    fmt = context.user_data.get("format", "-")
    await query.edit_message_text(
        f"🗺 Tanlangan xaritalar: {maps_selected}\n🎯 Format: {fmt}\n3️⃣ Match vaqti tanlang:",
        reply_markup=reply_markup
    )

# ============================
# TIME SELECTED → PREVIEW
# ============================
async def time_selected(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    selected_time = query.data.split("_", 1)[1]
    context.user_data["match_time"] = selected_time

    keyboard = [[InlineKeyboardButton("✅ To'g'ri", callback_data="confirm_lobby"),
                 InlineKeyboardButton("✏️ O'zgartirish", callback_data="edit_lobby")]]

    maps_selected = ", ".join(context.user_data.get("maps", [])) or "-"
    fmt = context.user_data.get("format", "-")
    time = context.user_data.get("match_time", "-")

    text = (
        f"🎮 *CS2 Lobby Preview* 🎮\n\n"
        f"🅰️ TEAM A (0/{lobby_data['max_team_size']}): -\n"
        f"🅱️ TEAM B (0/{lobby_data['max_team_size']}): -\n"
        f"🗺 Xaritalar: {maps_selected}\n"
        f"🎯 Format: {fmt}\n"
        f"🕒 Vaqt: {time}\n\n"
        f"Foydalanuvchilar TEAM A / TEAM B ga qo‘shilishi mumkin."
    )
    await query.edit_message_text(text=text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")

# ============================
# CONFIRM / EDIT
# ============================
async def confirm_or_edit(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if query.data=="edit_lobby":
        await create_lobby_handler(update, context)
        return
    elif query.data=="confirm_lobby":
        lobby_data["chat_id"] = GROUP_CHAT_ID
        lobby_data["team_a"].clear()
        lobby_data["team_b"].clear()
        lobby_data["ready_users"].clear()
        lobby_data["maps"] = context.user_data.get("maps", [])
        lobby_data["format"] = context.user_data.get("format")
        lobby_data["match_time"] = context.user_data.get("match_time")

        # Guruhga lobby yuborish
        keyboard = [
            [InlineKeyboardButton("🅰️ TEAM A", callback_data="join_a"),
             InlineKeyboardButton("🅱️ TEAM B", callback_data="join_b")],
            [InlineKeyboardButton("❌ Leave", callback_data="leave")]
        ]
        text = make_lobby_text()
        message = await context.bot.send_message(chat_id=GROUP_CHAT_ID,
                                                 text=text,
                                                 reply_markup=InlineKeyboardMarkup(keyboard),
                                                 parse_mode="Markdown")
        lobby_data["message_id"]=message.message_id
        await query.edit_message_text("✅ Lobby guruhga yuborildi! Foydalanuvchilar TEAM A / TEAM B ga qo‘shila oladi.")

# ============================
# GENERATE LOBBY TEXT
# ============================
def make_lobby_text():
    def name_link(u: User):
        return f"[{u.first_name}](tg://user?id={u.id})"
    team_a_text = ", ".join([name_link(u) for u in lobby_data["team_a"]]) or "-"
    team_b_text = ", ".join([name_link(u) for u in lobby_data["team_b"]]) or "-"
    max_size = lobby_data["max_team_size"]
    return (
        f"🎮 *CS2 Lobby* 🎮\n\n"
        f"🅰️ TEAM A ({len(lobby_data['team_a'])}/{max_size}): {team_a_text}\n"
        f"🅱️ TEAM B ({len(lobby_data['team_b'])}/{max_size}): {team_b_text}\n"
        f"🗺 Xaritalar: {', '.join(lobby_data['maps'])}\n"
        f"🎯 Format: {lobby_data['format']}\n"
        f"🕒 Vaqt: {lobby_data['match_time']}"
    )

# ============================
# USER JOIN / LEAVE / READY
# ============================
async def user_join_leave_ready(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user = query.from_user
    await query.answer()

    if query.data in ["join_a","join_b"]:
        if user in lobby_data["team_a"] or user in lobby_data["team_b"]:
            await query.answer("Siz allaqachon bir jamoadasiz!", show_alert=True)
            return
    if query.data=="join_a":
        if len(lobby_data["team_a"])<lobby_data["max_team_size"]: lobby_data["team_a"].append(user)
        else: await query.answer("TEAM A to‘ldi!", show_alert=True); return
    elif query.data=="join_b":
        if len(lobby_data["team_b"])<lobby_data["max_team_size"]: lobby_data["team_b"].append(user)
        else: await query.answer("TEAM B to‘ldi!", show_alert=True); return
    elif query.data=="leave":
        if user in lobby_data["team_a"]: lobby_data["team_a"].remove(user)
        if user in lobby_data["team_b"]: lobby_data["team_b"].remove(user)
        if user in lobby_data["ready_users"]: lobby_data["ready_users"].remove(user)
    elif query.data=="ready":
        if user not in lobby_data["ready_users"]: lobby_data["ready_users"].add(user)

    await update_lobby_message(context)

# ============================
# UPDATE LOBBY MESSAGE
# ============================
async def update_lobby_message(context):
    keyboard = [
        [InlineKeyboardButton("🅰️ TEAM A", callback_data="join_a"),
         InlineKeyboardButton("🅱️ TEAM B", callback_data="join_b")],
        [InlineKeyboardButton("❌ Leave", callback_data="leave")]
    ]
    if len(lobby_data["team_a"])==lobby_data["max_team_size"] and \
       len(lobby_data["team_b"])==lobby_data["max_team_size"]:
        ready_count=len(lobby_data["ready_users"])
        keyboard.append([InlineKeyboardButton(f"✅ Tayyorman ({ready_count})", callback_data="ready")])
        if ready_count==lobby_data["max_team_size"]*2:
            keyboard=[]
            await context.bot.send_message(lobby_data["chat_id"],
                                           "Tez orada serverga ulanish uchun link yuboriladi! Link olish uchun @lobbycs2_bot start bosing!!!")

    reply_markup=InlineKeyboardMarkup(keyboard)
    text=make_lobby_text()
    await context.bot.edit_message_text(chat_id=lobby_data["chat_id"],
                                        message_id=lobby_data["message_id"],
                                        text=text,
                                        reply_markup=reply_markup,
                                        parse_mode="Markdown")

# ============================
# ADMIN SEND SERVER LINK
# ============================
async def admin_send_link(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.from_user.id!=ADMIN_ID: return
    link=update.message.text
    lobby_data["server_link"]=link
    sent_count=0
    for user in lobby_data["ready_users"]:
        try:
            await context.bot.send_message(chat_id=user.id,text=f"🔗 Server link: {link}")
            sent_count+=1
        except Exception as e: logger.error(f"User {user.id} ga link yuborilmadi: {e}")
    try: await context.bot.edit_message_reply_markup(chat_id=lobby_data["chat_id"],
                                                    message_id=lobby_data["message_id"],
                                                    reply_markup=None)
    except Exception as e: logger.error(f"Guruhdagi tugmalarni olib tashlashda xato: {e}")
    await context.bot.send_message(chat_id=lobby_data["chat_id"],
                                   text=f"✅ Lobby toldi va tez orada match boshlandi! Iltimos bot tomonidan yuborilgan havola orqali serverga ulaning! Ssilka  {sent_count} o'yinchiga yuborildi. Agar sizda kelmagan bolsa botga @lobbycs2_bot start bosing")

# ============================
# MAIN
# ============================
if __name__ == "__main__":
    asyncio.set_event_loop(asyncio.new_event_loop())
    app=ApplicationBuilder().token("8554998951:AAGyWR-wo7JYZfQBXhTNw9Qe_e9485D8w10").build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(create_lobby_handler, pattern="create_lobby"))
    app.add_handler(CallbackQueryHandler(format_selected, pattern="format_"))
    app.add_handler(CallbackQueryHandler(map_selection, pattern="map_"))
    app.add_handler(CallbackQueryHandler(map_selection_done, pattern="maps_done"))
    app.add_handler(CallbackQueryHandler(time_selected, pattern="time_"))
    app.add_handler(CallbackQueryHandler(confirm_or_edit, pattern="confirm_lobby|edit_lobby"))
    app.add_handler(CallbackQueryHandler(user_join_leave_ready, pattern="join_a|join_b|leave|ready"))
    app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), admin_send_link))

    print("Bot ishga tushdi...")
    app.run_polling()
