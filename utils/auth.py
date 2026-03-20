import secrets, time, random, json, os
from threading import Lock

# File paths for JSON storage
TOKEN_FILE = 'tokens.json'
OTP_FILE = 'otps.json'

# Locks to prevent race conditions when accessing files
token_lock = Lock()
otp_lock = Lock()

# Helper function to read from a JSON file
def _read_json(filepath, lock):
    with lock:
        if not os.path.exists(filepath):
            return {}
        try:
            with open(filepath, 'r') as f:
                return json.load(f)
        except (json.JSONDecodeError, FileNotFoundError):
            return {}

# Helper function to write to a JSON file
def _write_json(filepath, data, lock):
    with lock:
        with open(filepath, 'w') as f:
            json.dump(data, f, indent=4)

def create_token(mobile):
    tokens = _read_json(TOKEN_FILE, token_lock)
    current_time = time.time()
    # Clean up expired tokens for maintenance
    for t in list(tokens.keys()):
        if tokens[t].get("exp", 0) < current_time:
            del tokens[t]

    t = secrets.token_hex(16)
    one_month_in_seconds = 30 * 24 * 60 * 60
    tokens[t] = {"mobile": mobile, "exp": current_time + one_month_in_seconds}
    _write_json(TOKEN_FILE, tokens, token_lock)
    return t

def verify_token(t):
    tokens = _read_json(TOKEN_FILE, token_lock)
    d = tokens.get(t)
    if not d or d.get("exp", 0) < time.time():
        return None
    return d["mobile"]

def create_otp(mobile):
    """Generates a 6-digit OTP, stores it with a 5-minute expiry."""
    otps = _read_json(OTP_FILE, otp_lock)
    otp = str(random.randint(100000, 999999))
    otps[mobile] = {"otp": otp, "exp": time.time() + 300} # 5 minutes expiry
    _write_json(OTP_FILE, otps, otp_lock)
    print(f"OTP for {mobile} is: {otp}") # Simulate sending OTP via SMS
    return otp

def verify_otp(mobile, otp, consume=True):
    """Verifies the OTP. Returns True if valid, False otherwise."""
    otps = _read_json(OTP_FILE, otp_lock)
    stored_otp_data = otps.get(mobile)
    if not stored_otp_data or stored_otp_data.get("exp", 0) < time.time() or stored_otp_data.get("otp") != otp:
        return False
    
    if consume:
        del otps[mobile] # OTP is single-use
        _write_json(OTP_FILE, otps, otp_lock)
    return True
