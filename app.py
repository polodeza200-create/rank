import discord
from discord import app_commands
import requests
import time
import random
import uuid
import base64
import json
import asyncio
import os
import socket

# ============================================================
# CONFIGURATION
# ============================================================
def _d(s):
    """Décode simplement"""
    try:
        return base64.b64decode(s).decode()
    except:
        return s

# Tokens encodés
_UT = "TVRRME5EWXhNREl5T0RNd05UQXdNalE1Tmk1SE0xZHVhRGd1V0hKeGVFeHVZME5XWlhSbFRuZzNiWEY1ZVZCdWJuaHhielpIZW05bk5tSmZPSGhTU1djPQ=="
_BT = "TVRRM05qVXpPVGN3TXpJeE1qWXpPREk1T1M1SE5GbExWbGN1VUhCT2JXdHdOMnQyWlRCVE9FTTRSRE5MTWxoYVJuSm1SMjlSTFVsaldFaEtXQzB6Y0dZMk9BPT0="

USER_TOKEN = os.getenv('USER_TOKEN', _d(_d(_UT)))
BOT_TOKEN = os.getenv('BOT_TOKEN', _d(_d(_BT)))

CHANNEL_ID = 1471651649465483489
GUILD_ID = 1469747545625329931
APPLICATION_ID = "1423032717687132190"
ROYAL_ROLE_ID = "1471650642786517073"

# ============================================================
# INITIALISATION DU BOT
# ============================================================
intents = discord.Intents.default()
intents.message_content = True

class RankBot(discord.Client):
    def __init__(self):
        super().__init__(intents=intents)
        self.tree = app_commands.CommandTree(self)
    
    async def setup_hook(self):
        await self.tree.sync()
        print("✅ Commandes slash synchronisées!")

bot = RankBot()

# ============================================================
# FONCTIONS UTILITAIRES
# ============================================================

def generate_nonce():
    return str(int(time.time() * 1000) * 4194304 + random.randint(0, 4194403))

def generate_session_id():
    return str(uuid.uuid4()).replace('-', '')

def get_super_properties():
    super_props = {
        "os": "Windows",
        "browser": "Chrome",
        "device": "",
        "system_locale": "en-US",
        "browser_user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "browser_version": "120.0.0.0",
        "os_version": "10",
        "referrer": "",
        "referring_domain": "",
        "referrer_current": "",
        "referring_domain_current": "",
        "release_channel": "stable",
        "client_build_number": 501798,
        "client_event_source": None
    }
    return base64.b64encode(json.dumps(super_props, separators=(',', ':')).encode()).decode()

def get_session():
    """Crée une session requests avec configuration spécifique"""
    session = requests.Session()
    
    # Désactiver les proxies
    session.trust_env = False
    
    # Adapter pour éviter les problèmes de connexion
    adapter = requests.adapters.HTTPAdapter(
        max_retries=3,
        pool_connections=10,
        pool_maxsize=10
    )
    session.mount('http://', adapter)
    session.mount('https://', adapter)
    
    return session

def verify_user_token():
    """Vérifie que le USER_TOKEN est valide"""
    url = "https://discord.com/api/v9/users/@me"
    headers = {
        "Authorization": USER_TOKEN,
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Accept": "application/json",
        "Accept-Language": "en-US,en;q=0.9"
    }
    
    # Afficher l'IP actuelle
    try:
        ip_check = requests.get("https://api.ipify.org?format=json", timeout=5)
        print(f"🌐 IP actuelle: {ip_check.json().get('ip')}")
    except:
        pass
    
    session = get_session()
    
    try:
        response = session.get(url, headers=headers, timeout=15)
        
        if response.status_code == 200:
            user_data = response.json()
            print(f"✅ USER_TOKEN valide pour: {user_data.get('username')}#{user_data.get('discriminator')}")
            return True, user_data
        else:
            print(f"❌ Erreur {response.status_code}: {response.text}")
            print("\n⚠️  PROBLÈME DÉTECTÉ:")
            print("   L'IP de Railway est probablement bloquée par Discord pour les user tokens.")
            print("\n💡 SOLUTIONS POSSIBLES:")
            print("   1. Utiliser un VPS personnel (Linode, DigitalOcean, Vultr)")
            print("   2. Utiliser un proxy résidentiel")
            print("   3. Héberger sur ton PC local avec ngrok ou un tunnel")
            return False, None
    except Exception as e:
        print(f"❌ Erreur de connexion: {e}")
        return False, None

def check_channel_permissions(channel_id):
    url = f"https://discord.com/api/v9/channels/{channel_id}"
    headers = {
        "Authorization": USER_TOKEN,
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    }
    
    session = get_session()
    
    try:
        response = session.get(url, headers=headers, timeout=15)
        if response.status_code == 200:
            channel_data = response.json()
            print(f"✅ Accès au canal: {channel_data.get('name', 'Unknown')}")
            return True
        else:
            print(f"⚠️  Statut du canal: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Erreur: {e}")
        return False

# ============================================================
# FONCTIONS API DISCORD
# ============================================================

def delete_message(channel_id, message_id):
    url = f"https://discord.com/api/v9/channels/{channel_id}/messages/{message_id}"
    
    headers = {
        "Authorization": USER_TOKEN,
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "X-Super-Properties": get_super_properties()
    }
    
    session = get_session()
    response = session.delete(url, headers=headers, timeout=15)
    return response.status_code == 204

def send_addrole_command(channel_id, user_id):
    url = f"https://discord.com/api/v9/channels/{channel_id}/messages"
    
    headers = {
        "Authorization": USER_TOKEN,
        "Content-Type": "application/json",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "X-Super-Properties": get_super_properties(),
        "Origin": "https://discord.com",
        "Referer": f"https://discord.com/channels/{GUILD_ID}/{channel_id}"
    }
    
    payload = {
        "mobile_network_type": "unknown",
        "content": f"-addrole {user_id}",
        "nonce": generate_nonce(),
        "tts": False,
        "flags": 0
    }
    
    print(f"📤 Envoi de la commande -addrole pour l'utilisateur {user_id}...")
    
    session = get_session()
    response = session.post(url, json=payload, headers=headers, timeout=15)
    
    if response.status_code == 200:
        data = response.json()
        message_id = data.get("id")
        print(f"✅ Message envoyé avec succès! Message ID: {message_id}")
        
        if delete_message(channel_id, message_id):
            print(f"🗑️  Message supprimé avec succès!")
        
        return data
    else:
        print(f"❌ Erreur {response.status_code}: {response.text}")
        return None

def get_bot_response(channel_id, after_message_id, max_attempts=10):
    url = f"https://discord.com/api/v9/channels/{channel_id}/messages?limit=5&after={after_message_id}"
    
    headers = {
        "Authorization": USER_TOKEN,
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "X-Super-Properties": get_super_properties()
    }
    
    print("🔍 Recherche de la réponse du bot...")
    
    session = get_session()
    
    for attempt in range(max_attempts):
        time.sleep(1)
        
        response = session.get(url, headers=headers, timeout=15)
        
        if response.status_code == 200:
            messages = response.json()
            
            for message in messages:
                author = message.get("author", {})
                if author.get("bot") or message.get("components"):
                    print(f"✅ Réponse du bot trouvée! Message ID: {message.get('id')}")
                    return message
        
        print(f"⏳ Tentative {attempt + 1}/{max_attempts}...")
    
    print("❌ Impossible de trouver la réponse du bot")
    return None

def interact_with_role_selector(message_id, role_id, guild_id, channel_id, session_id):
    url = "https://discord.com/api/v9/interactions"
    
    headers = {
        "Authorization": USER_TOKEN,
        "Content-Type": "application/json",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "X-Super-Properties": get_super_properties(),
        "Origin": "https://discord.com",
        "Referer": f"https://discord.com/channels/{guild_id}/{channel_id}"
    }
    
    payload = {
        "type": 3,
        "nonce": generate_nonce(),
        "guild_id": str(guild_id),
        "channel_id": str(channel_id),
        "message_flags": 32768,
        "message_id": message_id,
        "application_id": APPLICATION_ID,
        "session_id": session_id,
        "data": {
            "component_type": 6,
            "custom_id": "role_select",
            "type": 6,
            "values": [role_id]
        }
    }
    
    print(f"📤 Sélection du rôle {role_id}...")
    
    session = get_session()
    response = session.post(url, json=payload, headers=headers, timeout=15)
    
    if response.status_code in [200, 204]:
        print(f"✅ Rôle sélectionné avec succès!")
        return True
    else:
        print(f"❌ Erreur lors de la sélection du rôle: {response.status_code}")
        print(f"Réponse: {response.text}")
        return False

# ============================================================
# ÉVÉNEMENTS DU BOT
# ============================================================

@bot.event
async def on_ready():
    print("=" * 60)
    print(f'✅ Bot connecté en tant que {bot.user}')
    print(f'📋 ID du bot: {bot.user.id}')
    print(f'🎯 Serveur cible: {GUILD_ID}')
    print(f'📺 Canal cible: {CHANNEL_ID}')
    print('💎 Commande disponible: /rank royal <user_id>')
    print("=" * 60)
    
    print("\n🔍 Vérification de la configuration...")
    valid, user_data = verify_user_token()
    
    if valid:
        print(f"🔍 Vérification des permissions sur le canal...")
        if check_channel_permissions(CHANNEL_ID):
            print("\n✅ Configuration complète et fonctionnelle!")
        else:
            print("\n⚠️  ATTENTION: Problème de permission sur le canal!")
    else:
        print("\n⚠️  ATTENTION: Impossible d'utiliser le USER_TOKEN depuis Railway!")
        print("⚠️  Railway utilise des IP partagées bloquées par Discord.")

# ============================================================
# COMMANDES SLASH
# ============================================================

rank_group = app_commands.Group(name="rank", description="Commandes de gestion des rangs")

@rank_group.command(name="royal", description="Attribuer le rang Royal à un utilisateur")
@app_commands.describe(user_id="L'ID de l'utilisateur Discord")
async def rank_royal(interaction: discord.Interaction, user_id: str):
    print("\n" + "=" * 60)
    print(f"🎯 Commande /rank royal reçue de {interaction.user}")
    print(f"👤 User ID cible: {user_id}")
    print("=" * 60)
    
    if not user_id.isdigit():
        await interaction.response.send_message(
            "❌ L'ID utilisateur doit être un nombre!",
            ephemeral=True
        )
        return
    
    await interaction.response.send_message(
        f"⏳ Attribution du rang **Royal** à l'utilisateur `{user_id}`...",
        ephemeral=True
    )
    
    try:
        session_id = generate_session_id()
        print(f"🔐 Session ID généré: {session_id}")
        
        response_data = send_addrole_command(CHANNEL_ID, user_id)
        
        if not response_data:
            await interaction.edit_original_response(
                content="❌ Échec - L'IP de Railway est bloquée par Discord pour les user tokens.\n\n**Solutions:**\n• Héberger sur un VPS (Linode, DigitalOcean)\n• Héberger localement avec ngrok"
            )
            return
        
        user_message_id = response_data.get("id")
        bot_message = get_bot_response(CHANNEL_ID, user_message_id)
        
        if not bot_message:
            await interaction.edit_original_response(
                content="❌ Impossible de récupérer la réponse du bot."
            )
            return
        
        bot_message_id = bot_message.get("id")
        
        print("⏳ Attente de 1 seconde...")
        await asyncio.sleep(1)
        
        success = interact_with_role_selector(
            message_id=bot_message_id,
            role_id=ROYAL_ROLE_ID,
            guild_id=GUILD_ID,
            channel_id=CHANNEL_ID,
            session_id=session_id
        )
        
        if success:
            await interaction.edit_original_response(
                content=f"✅ Rang **Royal** attribué avec succès à <@{user_id}>!"
            )
            print("✅ Opération terminée avec succès!")
        else:
            await interaction.edit_original_response(
                content="❌ Erreur lors de la sélection du rôle."
            )
            print("❌ Échec de l'opération")
    
    except Exception as e:
        await interaction.edit_original_response(
            content=f"❌ Une erreur s'est produite: {str(e)}"
        )
        print(f"❌ Erreur: {e}")
    
    print("=" * 60 + "\n")

bot.tree.add_command(rank_group)

# ============================================================
# LANCEMENT DU BOT
# ============================================================

if __name__ == "__main__":
    print("=" * 60)
    print("🤖 Bot Discord - Attribution de rang Royal")
    print("=" * 60)
    print("✅ Configuration détectée")
    print(f"🎯 Guild ID: {GUILD_ID}")
    print(f"📺 Channel ID: {CHANNEL_ID}")
    print(f"💎 Royal Role ID: {ROYAL_ROLE_ID}")
    print("\n🚀 Démarrage du bot...")
    print("=" * 60 + "\n")
    
    try:
        bot.run(BOT_TOKEN)
    except discord.errors.LoginFailure:
        print("\n❌ ERREUR: Token bot invalide!")
    except Exception as e:
        print(f"\n❌ ERREUR: {e}")
