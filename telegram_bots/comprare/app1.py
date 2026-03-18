import telebot
import json
import os

# ---------------- CONFIG ----------------
API_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN") or "8340925625:AAFJcl_MmBtRoBitmJfUW_Bcz72Wymq-gm8"
FILE_NAME = "tanks_data.json"

bot = telebot.TeleBot(API_TOKEN)

# ---------------- LOAD TANKS ----------------
def load_tanks():
    if not os.path.exists(FILE_NAME):
        return []
    with open(FILE_NAME, "r", encoding="utf-8") as f:
        data = json.load(f)
        # Skip header if it exists
        if data and data[0].get("tank_name") == "Tank Name":
            return data[1:]
        return data

# ---------------- FIND BEST MATCH ----------------
def get_best_match(search_name):
    """Searches by full_name as the primary key."""
    tanks = load_tanks()
    search_name = search_name.lower()
    
    partial_match = None
    for tank in tanks:
        fname = tank.get("full_name", "").lower()
        tname = tank.get("tank_name", "").lower()

        if fname == search_name or tname == search_name:
            return tank
        
        if (search_name in fname or search_name in tname) and not partial_match:
            partial_match = tank
    return partial_match

# ---------------- CALCULATE STATS ----------------
def extract_stats(tank):
    def clean_val(val, take_first=False):
        if not val or not isinstance(val, str): return 0.0
        if take_first and "/" in val: val = val.split("/")[0]
        clean_str = "".join(c for c in val if c.isdigit() or c == '.')
        try: return float(clean_str)
        except ValueError: return 0.0

    return {
        "full_name": tank.get("full_name", "Unknown"),
        "tier": tank.get("tier", "N/A"),
        "dpm": tank.get("Tank DPM", "0"),
        "dmg": tank.get("Dmg", "0"),
        "reload": tank.get("Reload", "0s"),
        "pen": tank.get("Pen", "0"),
        "velo": tank.get("Velo", "0"),
        "acc": tank.get("Acc", "0"),
        "aim": tank.get("Aim", "0s"),
        "dispersion": tank.get("Dispresion", "0"),
        "elevation": tank.get("DeP/Elev", "0"),
        "speed": tank.get("Speed", "0"),
        "traverse": tank.get("Traverse", "0"),
        "power": tank.get("Power", "0"),
        "pw": tank.get("P/W", "0"),
        "weight": tank.get("Weight", "0"),
        "hp": tank.get("Health", "0"),
        "vr": tank.get("VR", "0"),
        # Cleaned numeric values for comparison logic
        "n_dpm": clean_val(tank.get("Tank DPM")),
        "n_dmg": clean_val(tank.get("Dmg")),
        "n_reload": clean_val(tank.get("Reload")),
        "n_pen": clean_val(tank.get("Pen")),
        "n_velo": clean_val(tank.get("Velo")),
        "n_acc": clean_val(tank.get("Acc")),
        "n_aim": clean_val(tank.get("Aim")),
        "n_speed": clean_val(tank.get("Speed"), True),
        "n_traverse": clean_val(tank.get("Traverse")),
        "n_power": clean_val(tank.get("Power")),
        "n_pw": clean_val(tank.get("P/W")),
        "n_hp": clean_val(tank.get("Health")),
        "n_vr": clean_val(tank.get("VR"))
    }

# ---------------- BOT HANDLERS ----------------
@bot.message_handler(commands=["info"])
def handle_info(message):
    name = message.text.replace("/info", "").strip()
    tank = get_best_match(name)
    if not tank:
        bot.reply_to(message, "❌ Tank not found.")
        return

    s = extract_stats(tank)
    response = (
        f"🛡️ *{s['full_name']}* (Tier {s['tier']})\n\n"
        f"🔥 *Firepower*\n"
        f"• DPM: `{s['dpm']}`\n"
        f"• Damage: `{s['dmg']}`\n"
        f"• Reload: `{s['reload']}`\n"
        f"• Pen: `{s['pen']}`\n"
        f"• Velocity: `{s['velo']} m/s`\n"
        f"• Acc: `{s['acc']}` | Aim: `{s['aim']}`\n"
        f"• Dispersion: `{s['dispersion']}`\n"
        f"• Dep/Elev: `{s['elevation']}`\n\n"
        f"⚙️ *Mobility & Protection*\n"
        f"• Speed: `{s['speed']} km/h`\n"
        f"• Traverse: `{s['traverse']}`\n"
        f"• Power: `{s['power']} hp` ({s['pw']} hp/t)\n"
        f"• Weight: `{s['weight']}`\n"
        f"• HP: `{s['hp']}` | VR: `{s['vr']}m`"
    )
    bot.send_message(message.chat.id, response, parse_mode="Markdown")

@bot.message_handler(commands=["compare"])
def handle_compare(message):
    parts = message.text.replace("/compare", "").split(",")
    if len(parts) < 2:
        bot.reply_to(message, "💡 Usage: `/compare AMX 30, T-34`", parse_mode="Markdown")
        return

    t1 = get_best_match(parts[0].strip())
    t2 = get_best_match(parts[1].strip())
    if not t1 or not t2:
        bot.reply_to(message, "❌ Could not find both tanks.")
        return

    s1, s2 = extract_stats(t1), extract_stats(t2)

    def comp(v1, v2, raw1, raw2, higher_is_better=True):
        if v1 == v2: return f"{raw1} vs {raw2}"
        if higher_is_better:
            return f"*{raw1}* vs {raw2}" if v1 > v2 else f"{raw1} vs *{raw2}*"
        return f"*{raw1}* vs {raw2}" if v1 < v2 else f"{raw1} vs *{raw2}*"

    response = (
        f"🆚 *{s1['full_name']}* vs *{s2['full_name']}*\n\n"
        f"🎖️ Tier: `{s1['tier']} vs {s2['tier']}`\n"
        f"🔥 DPM: {comp(s1['n_dpm'], s2['n_dpm'], s1['dpm'], s2['dpm'])}\n"
        f"💥 Dmg: {comp(s1['n_dmg'], s2['n_dmg'], s1['dmg'], s2['dmg'])}\n"
        f"⏱️ Reload: {comp(s1['n_reload'], s2['n_reload'], s1['reload'], s2['reload'], False)}\n"
        f"🎯 Pen: {comp(s1['n_pen'], s2['n_pen'], s1['pen'], s2['pen'])}\n"
        f"🚀 Velo: {comp(s1['n_velo'], s2['n_velo'], s1['velo'], s2['velo'])} m/s\n"
        f"🔬 Acc: {comp(s1['n_acc'], s2['n_acc'], s1['acc'], s2['acc'], False)}\n"
        f"⏲️ Aim: {comp(s1['n_aim'], s2['n_aim'], s1['aim'], s2['aim'], False)}\n"
        f"🌀 Disp: `{s1['dispersion']} vs {s2['dispersion']}`\n"
        f"📐 Elev: `{s1['elevation']} vs {s2['elevation']}`\n"
        f"⚡ Speed: {comp(s1['n_speed'], s2['n_speed'], s1['speed'], s2['speed'])}\n"
        f"🔄 Trav: {comp(s1['n_traverse'], s2['n_traverse'], s1['traverse'], s2['traverse'])}\n"
        f"🐎 Power: {comp(s1['n_power'], s2['n_power'], s1['power'], s2['power'])}\n"
        f"⚖️ P/W: {comp(s1['n_pw'], s2['n_pw'], s1['pw'], s2['pw'])}\n"
        f"🏋️ Wgt: `{s1['weight']} vs {s2['weight']}`\n"
        f"❤️ HP: {comp(s1['n_hp'], s2['n_hp'], s1['hp'], s2['hp'])}\n"
        f"👁️ VR: {comp(s1['n_vr'], s2['n_vr'], s1['vr'], s2['vr'])}m"
    )
    bot.send_message(message.chat.id, response, parse_mode="Markdown")

if __name__ == "__main__":
    bot.infinity_polling()