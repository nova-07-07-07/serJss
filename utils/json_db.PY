import json
import os
from threading import Lock
import requests
import datetime

# possible storage paths
FOLDER_PATHS = [
    "linux/",
    "E:\\"
]

def _get_base_dir():
    year = str(datetime.datetime.now().year)

    for path in FOLDER_PATHS:
        try:
            base = os.path.join(path, 'datas', year)
            os.makedirs(base, exist_ok=True)
            return base
        except:
            continue

    # fallback (current dir)
    base = os.path.join(os.getcwd(), 'datas', year)
    os.makedirs(base, exist_ok=True)
    return base


BASE_DIR = _get_base_dir()

USER_FILE = os.path.join(BASE_DIR, 'user.json')
ORDER_FILE = os.path.join(BASE_DIR, 'order.json')
LINES_FILE = os.path.join(BASE_DIR, 'lines.json')

# FIRST define helpers

def _ensure_dir(filepath):
    folder = os.path.dirname(filepath)
    if not os.path.exists(folder):
        os.makedirs(folder)

def _write_json(filepath, data):
    _ensure_dir(filepath)
    with open(filepath, 'w') as f:
        json.dump(data, f, indent=4)

def _read_json(filepath):
    if not os.path.exists(filepath):
        return []
    try:
        with open(filepath, 'r') as f:
            data = json.load(f)
            return data if isinstance(data, list) else []
    except:
        return []

# THEN init

def init_files():
    for file in [USER_FILE, ORDER_FILE, LINES_FILE]:
        if not os.path.exists(file):
            _write_json(file, [])

init_files()



db_lock = Lock()

def _ensure_dir(filepath):
    """Ensures the data directory exists."""
    folder = os.path.dirname(filepath)
    if not os.path.exists(folder):
        os.makedirs(folder)

def _read_json(filepath):
    if not os.path.exists(filepath):
        return []
    try:
        with open(filepath, 'r') as f:
            data = json.load(f)
            return data if isinstance(data, list) else []
    except:
        return []



def _get_next_id(data_list):
    """Calculates the next ID based on the maximum ID in the list."""
    if not data_list:
        return 1
    # Assumes records are dicts with an 'id' key
    try:
        ids = [item.get('id', 0) for item in data_list]
        return max(ids) + 1
    except:
        return 1

def get_user_by_mobile(mobile):
    with db_lock:
        users = _read_json(USER_FILE)
        for u in users:
            if u.get("mobile") == mobile:
                return u
        return None

def create_user_record(name, mobile):
    with db_lock:
        users = _read_json(USER_FILE)
        # Double check to avoid duplicates
        for u in users:
            if u.get("mobile") == mobile:
                return u

        new_id = _get_next_id(users)
        user = {
            "id": new_id,
            "name": name,
            "mobile": mobile,
            "profile_pic": None,
            "pcp": 40,
            "ref_img": [],
            "lat": None,
            "lng": None,
            "created_at": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        users.append(user)
        _write_json(USER_FILE, users)
        return user

def create_order_record(user_id, items, created_at, location=None):
    with db_lock:
        orders = _read_json(ORDER_FILE)
        
        order_id = _get_next_id(orders)
        
        # Create the Order Header



        order = {
            "id": order_id,
            "user_id": user_id,
            "created_at": created_at,
            "location": location,
            "status": "Pending",
            "payment_status": "Unpaid",
            "amount": 0,
            "paid_amount": 0
        }


        # get data from config.json file
        # {
        #     "items": [
        #         {"id": "300ml", "name": "300ml Bottle", "available": true, "price": 100},
        #         {"id": "500ml", "name": "500ml Bottle", "available": true, "price": 150},
        #         {"id": "1l", "name": "1L Bottle", "available": true, "price": 250},
        #         {"id": "2l", "name": "2L Bottle", "available": true, "price": 400},
        #         {"id": "20l", "name": "20L Jar", "available": true, "price": 40}
        #     ]
        # }

        config_data = None
        with open('config.json', 'r') as f:
            config_data = json.load(f)


        # Calculate total amount

        total_amount = 0
        for item in items:
            for i in config_data["items"]:
                if i["id"] == item["id"]:
                    total_amount += i["price"] * item["quantity"]
                    break
        order["amount"] = total_amount
            
        # Store items directly in the order with 'item_id'
        order["items"] = [{"item_id": item['id'], "quantity": item['quantity']} for item in items]
        
        orders.append(order)
        _write_json(ORDER_FILE, orders)

        
        # Return order with items for frontend consistency
        order["items"] = items
        return order

def cancel_order_record(order_id):
    with db_lock:
        orders = _read_json(ORDER_FILE)
        
        original_len = len(orders)
        orders = [o for o in orders if o.get("id") != order_id]
        
        if len(orders) < original_len:
            return True
        return False
    

def update_order_items(order_id, items):
    with db_lock:
        orders = _read_json(ORDER_FILE)
        for order in orders:
            if order['id'] == order_id:
                # Update items directly in order
                order['items'] = [{"item_id": item['id'], "quantity": item['quantity']} for item in items]
                # Note: This does not update the total amount, keeping behavior consistent with previous version
                _write_json(ORDER_FILE, orders)
                return True
        return False

def update_user_profile_pic(user_id, pic_path):
    with db_lock:
        users = _read_json(USER_FILE)
        for user in users:
            if user["id"] == user_id:
                user["profile_pic"] = []
                user["profile_pic"].append(pic_path)
                _write_json(USER_FILE, users)
                return True
        return False
    

def add_user_ref_img(user_id, pic_path):
    with db_lock:
        users = _read_json(USER_FILE)
        for user in users:
            if user["id"] == user_id:
                if not isinstance(user.get("ref_img"), list):
                    user["ref_img"] = []

                if len(user["ref_img"]) >= 6:
                    return False

                user["ref_img"].append(pic_path)
                _write_json(USER_FILE, users)
                return True
        return False
    
def delete_user_ref_img(user_id, pic_path):
    with db_lock:
        users = _read_json(USER_FILE)
        for user in users:
            if user["id"] == user_id:
                if user.get("ref_img") and pic_path in user["ref_img"]:
                    user["ref_img"].remove(pic_path)
                    _write_json(USER_FILE, users)
                    return True
        return False

def update_user_location(user_id, lat, lng):
    with db_lock:
        users = _read_json(USER_FILE)

        for user in users:
            if user["id"] == user_id:

                user["lat"] = lat
                user["lng"] = lng

                try:
                    
                    url = f"https://api.geoapify.com/v1/geocode/reverse?lat={lat}&lon={lng}&apiKey=e4865a6fb15c412b9260343686aa7100"
                    
                    res = requests.get(url, timeout=5)

                    data = res.json()

                    features = data.get("features", [])

                    if len(features) > 0:
                        address = features[0].get("properties", {}).get("formatted")
                    else:
                        address = None


                except:
                    address = None
                user["address"] = address

                _write_json(USER_FILE, users)
                return True

        return False


def update_order_location(order_id, location):
    with db_lock:
        orders = _read_json(ORDER_FILE)
        for order in orders:
            if order['id'] == order_id:
                order['location'] = location
                _write_json(ORDER_FILE, orders)
                return True
        return False

def get_user_orders(user_id):
    with db_lock:
        orders = _read_json(ORDER_FILE)
        
        # Filter orders for the specific user
        user_orders = [o for o in orders if o.get("user_id") == user_id]
        
        # Reconstruct items for each order from lines.json
        for order in user_orders:
            if "items" in order:
                order["items"] = [{"id": i.get("item_id"), "quantity": i.get("quantity")} for i in order["items"]]
            else:
                order["items"] = []
            
        # Sort by created_at descending
        user_orders.sort(key=lambda x: x["created_at"], reverse=True)
        return user_orders
    

