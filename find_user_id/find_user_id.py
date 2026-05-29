import requests
from concurrent.futures import ThreadPoolExecutor
import time
import threading
import os

# ============================================================
# PARAMETERS TO FILL IN BY THE USER
# ============================================================
#
# This script automatically searches for the internal user ID
# associated with your Linky meter on Total Energies, in order
# to then retrieve your real-time consumption data.
#
# Before running the script, you need to fill in the 3 fields
# below with YOUR OWN information:
#
#   1) EMAIL              -> the email address you use to log
#                            in to your Total Energies customer
#                            account.
#
#   2) PASSWORD           -> the password associated with that
#                            account.
#                            (keep the quotes around it)
#
#   3) CUSTOMER_REF       -> your customer reference number
#                            (9 digits). You can find it:
#                              - on any Total Energies invoice
#                              - or on the home page of your online
#                                customer portal, just below your address.
#
# IMPORTANT: keep the quotes " " around each value.
# Correct example   : EMAIL = "myaddress@gmail.com"
# Incorrect example : EMAIL = myaddress@gmail.com   <-- will not work
#
EMAIL = "your.email@example.com"   # <-- put your Total Energies email here
PASSWORD = "YourPassword"          # <-- put your password here
CUSTOMER_REF = "123456789"         # <-- put your customer reference here (9 digits)


# ------------------------------------------------------------
# SEARCH RANGE
# ------------------------------------------------------------
#
# The script will test numerical IDs one by one in order to
# find the one matching your meter.
#
# By default, it tests from 1 to 10,000,000 (ten million), which
# can take a very long time. If you prefer to split the search
# into several shorter runs, you can change the bounds:
#
#   - First run  : SEARCH_START = 1          / SEARCH_END = 990_000
#   - Second run : SEARCH_START = 990_001    / SEARCH_END = 2_000_000
#   - Third run  : SEARCH_START = 2_000_001  / SEARCH_END = 3_000_000
#   - etc.
#
# The "_" character in numbers is just there to make them more
# readable (10_000_000 = 10000000). You can use it or not.
#
SEARCH_START = 1                   # search starting point
SEARCH_END = 10_000_000            # search ending point


# ============================================================
# TECHNICAL CONFIGURATION
# (only change this if you know what you are doing)
# ============================================================
BASE_URL = "https://esoftlink.esoftthings.com"
THREADS = 30
RELOGIN_INTERVAL = 2 * 60 * 60     # 2 hours
PROGRESS_INTERVAL = 5              # seconds between two progress prints


# ------------------------------------------------------------
# GLOBAL STATE
# ------------------------------------------------------------
session = requests.Session()
php_session_id = None
lock = threading.Lock()
stats_lock = threading.Lock()
hit_lock = threading.Lock()

last_login_time = 0

# Statistics
checked_count = 0
found_count = 0
error_count = 0
start_time = 0

# Signal to stop when a valid user ID is found
found_event = threading.Event()


# ------------------------------------------------------------
# LOGIN TO THE SERVER
# ------------------------------------------------------------
def login():
    global php_session_id, last_login_time, session

    print("[+] Logging in...")

    s = requests.Session()

    r = s.post(
        f"{BASE_URL}/login_check",
        data={
            "_username": EMAIL,
            "_password": PASSWORD
        },
        allow_redirects=False,
        timeout=10
    )

    cookies = s.cookies.get_dict()

    if "PHPSESSID" not in cookies:
        print("Login failed - no PHPSESSID received")
        return False

    with lock:
        session = s
        php_session_id = cookies["PHPSESSID"]
        last_login_time = time.time()

    print(f"[+] Session refreshed successfully")

    return True


# ------------------------------------------------------------
# CHECK SESSION EXPIRATION
# ------------------------------------------------------------
def ensure_login():
    global last_login_time

    if time.time() - last_login_time > RELOGIN_INTERVAL:
        login()


# ------------------------------------------------------------
# SHUTDOWN WHEN A VALID USER ID IS FOUND
# ------------------------------------------------------------
def shutdown_with_hit(user_id, response_text):
    """Prints the found user ID, the final statistics, then
    immediately terminates the program."""
    elapsed = time.time() - start_time

    print("\n" + "=" * 60)
    print(f"[!!! HIT FOUND] UserId = {user_id}")
    print("-" * 60)
    print(response_text)
    print("-" * 60)
    with stats_lock:
        print(f"[DONE] Checked        : {checked_count}")
        print(f"[DONE] Errors         : {error_count}")
    print(f"[DONE] Time to find   : {int(elapsed//60)}m{int(elapsed%60)}s")
    print("=" * 60)

    # os._exit immediately terminates the whole process (and therefore
    # all threads), without waiting for the pool workers to finish their
    # in-flight requests.
    os._exit(0)


# ------------------------------------------------------------
# CHECK A USER ID
# ------------------------------------------------------------
def check_user(user_id):
    global checked_count, found_count, error_count

    # If a valid ID has already been found by another thread,
    # we no longer perform any requests.
    if found_event.is_set():
        return

    ensure_login()

    user_raw = str(user_id)
    user_padded = str(user_id).zfill(6)

    seen = set()

    for user_str in (user_raw, user_padded):

        if user_str in seen:
            continue
        seen.add(user_str)

        if found_event.is_set():
            return

        url = f"{BASE_URL}/api/subscription/{user_str}/{CUSTOMER_REF}/measure/live.json"

        try:
            with lock:
                s = session

            r = s.get(url, timeout=5)

            with stats_lock:
                checked_count += 1

            if '"error"' not in r.text:
                with hit_lock:
                    if found_event.is_set():
                        return
                    found_event.set()
                    with stats_lock:
                        found_count += 1
                    shutdown_with_hit(user_str, r.text)

        except requests.RequestException:
            with stats_lock:
                error_count += 1

    time.sleep(0.01)


# ------------------------------------------------------------
# PROGRESS REPORTER
# ------------------------------------------------------------
def progress_reporter(total_users):
    last_checked = 0
    last_time = time.time()

    while True:
        time.sleep(PROGRESS_INTERVAL)

        with stats_lock:
            current_checked = checked_count

        now = time.time()
        elapsed = now - start_time
        delta_checked = current_checked - last_checked
        delta_time = now - last_time

        rate_total = current_checked / elapsed if elapsed > 0 else 0
        rate_recent = delta_checked / delta_time if delta_time > 0 else 0

        # Progress over the total (2 requests per user, except duplicates)
        progress_pct = (current_checked / (total_users * 2)) * 100 if total_users > 0 else 0

        remaining = (total_users * 2) - current_checked
        eta_sec = remaining / rate_recent if rate_recent > 0 else 0
        eta_h = int(eta_sec // 3600)
        eta_m = int((eta_sec % 3600) // 60)

        print(
            f"[STATS] checked={current_checked} "
            f"({progress_pct:.2f}%) | "
            f"rate={rate_recent:.1f}/s (avg {rate_total:.1f}/s) | "
            f"elapsed={int(elapsed//60)}m{int(elapsed%60)}s | "
            f"ETA={eta_h}h{eta_m:02d}m"
        )

        last_checked = current_checked
        last_time = now


# ============================================================
# START
# ============================================================
print("=" * 60)
print(f"[CONFIG] Email          : {EMAIL}")
print(f"[CONFIG] Customer ref   : {CUSTOMER_REF}")
print(f"[CONFIG] Base URL       : {BASE_URL}")
print(f"[CONFIG] Threads        : {THREADS}")
print(f"[CONFIG] Re-login every {RELOGIN_INTERVAL // 60} min")
print("=" * 60)

if not login():
    print("[FATAL] Initial login failed - aborting.")
    exit(1)

total_users = SEARCH_END - SEARCH_START

print(f"[+] Scanning user IDs from {SEARCH_START} to {SEARCH_END} ({total_users} users)")
print(f"[+] ~{total_users * 2} requests total (raw + zero-padded to 6 digits)")
print(f"[+] Progress will be reported every {PROGRESS_INTERVAL}s")
print("=" * 60)

start_time = time.time()

# Starts the progress reporter in the background
reporter_thread = threading.Thread(
    target=progress_reporter,
    args=(total_users,),
    daemon=True
)
reporter_thread.start()

submitted = 0
with ThreadPoolExecutor(max_workers=THREADS) as executor:
    for user_id in range(SEARCH_START, SEARCH_END):
        # If a hit has been found in the meantime, we stop feeding
        # the queue.
        # (shutdown_with_hit calls os._exit, so in practice we only
        #  get here if the hit has not yet been processed.)
        if found_event.is_set():
            break

        executor.submit(check_user, user_id)
        submitted += 1

        if submitted % 10000 == 0:
            print(f"[QUEUE] {submitted}/{total_users} user IDs submitted to the pool")

print("=" * 60)
print("[+] All tasks submitted. Waiting for workers to finish...")

# Note: we only get here if NO hit was found on the whole range,
# since shutdown_with_hit terminates the process via os._exit as
# soon as the first valid ID is found.
elapsed_total = time.time() - start_time
with stats_lock:
    print("=" * 60)
    print("[DONE] Scan finished - NO HIT FOUND on the full range.")
    print(f"[DONE] Total checked : {checked_count}")
    print(f"[DONE] Total errors  : {error_count}")
    print(f"[DONE] Total time    : {int(elapsed_total//3600)}h{int((elapsed_total%3600)//60)}m{int(elapsed_total%60)}s")
    print("=" * 60)
