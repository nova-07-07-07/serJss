import secrets
import time
import random
import json
import os

# Configuration
TOKENS_FILE = "tokens.json"
OTPS_FILE = "otps.json"

TOKEN_EXPIRE_SECONDS = 30 * 24 * 60 * 60   # 30 days
OTP_EXPIRE_SECONDS = 5 * 60                # 5 minutes

# ---------------- CORE PERSISTENCE ----------------

def _load_data(filename):
    """Loads JSON data from file safely."""
    if not os.path.exists(filename):
        return {}
    try:
        with open(filename, "r", encoding="utf-8") as f:
            content = f.read().strip()
            return json.loads(content) if content else {}
    except Exception as e:
        print(f"Error loading {filename}: {e}")
        return {}

def _save_data(filename, data):
    """Saves data to JSON file with indentation."""
    try:
        with open(filename, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4)
    except Exception as e:
        print(f"Error saving {filename}: {e}")

# ---------------- TOKEN MANAGEMENT ----------------

def create_token(mobile):
    tokens = _load_data(TOKENS_FILE)
    token = secrets.token_hex(32)
    tokens[token] = {
        "mobile": str(mobile),
        "exp": time.time() + TOKEN_EXPIRE_SECONDS
    }
    _save_data(TOKENS_FILE, tokens)
    return token

def verify_token(token):
    if not token:
        return None

    token = str(token).strip()
    # Handle "Bearer <token>" format if sent from headers
    if token.lower().startswith("bearer "):
        token = token[7:].strip()

    tokens = _load_data(TOKENS_FILE)
    data = tokens.get(token)
    
    if not data:
        return None

    # Check expiration
    if data["exp"] < time.time():
        del tokens[token]
        _save_data(TOKENS_FILE, tokens)
        return None

    return data["mobile"]

def remove_token(token):
    if not token:
        return False

    token = str(token).strip()
    if token.lower().startswith("bearer "):
        token = token[7:].strip()

    tokens = _load_data(TOKENS_FILE)
    if token in tokens:
        del tokens[token]
        _save_data(TOKENS_FILE, tokens)
        return True

    return False

# ---------------- OTP MANAGEMENT ----------------

def create_otp(mobile):
    mobile = str(mobile).strip()
    otp = str(random.randint(1000, 9999))

    otps = _load_data(OTPS_FILE)
    otps[mobile] = {
        "otp": otp,
        "exp": time.time() + OTP_EXPIRE_SECONDS
    }
    _save_data(OTPS_FILE, otps)

    # In production, this would be sent via SMS API
    print(f"DEBUG: OTP for {mobile} is {otp}")
    return otp

def verify_otp(mobile, otp, consume=True):
    mobile = str(mobile).strip()
    otp = str(otp).strip()

    otps = _load_data(OTPS_FILE)
    data = otps.get(mobile)
    
    if not data:
        return False

    # Check expiration
    if data["exp"] < time.time():
        del otps[mobile]
        _save_data(OTPS_FILE, otps)
        return False

    # Check match
    if data["otp"] != otp:
        return False

    # Remove OTP after successful use if requested
    if consume:
        del otps[mobile]
        _save_data(OTPS_FILE, otps)

    return True

# ---------------- CLEANUP UTILITIES ----------------

def clear_expired_tokens():
    """Removes all expired tokens from the storage file."""
    tokens = _load_data(TOKENS_FILE)
    now = time.time()
    initial_count = len(tokens)
    
    tokens = {t: d for t, d in tokens.items() if d["exp"] > now}
    
    if len(tokens) != initial_count:
        _save_data(TOKENS_FILE, tokens)
        return True
    return False

def clear_expired_otps():
    """Removes all expired OTPs from the storage file."""
    otps = _load_data(OTPS_FILE)
    now = time.time()
    initial_count = len(otps)
    
    otps = {m: d for m, d in otps.items() if d["exp"] > now}
    
    if len(otps) != initial_count:
        _save_data(OTPS_FILE, otps)
        return True
    return False