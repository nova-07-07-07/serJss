import os
import json
from datetime import datetime

BASE_DIR = os.path.join(".", "jss")


def _current_year():
    return str(datetime.now().year)


def _year_dir(year=None):
    year = str(year or _current_year())
    path = os.path.join(BASE_DIR, year)
    os.makedirs(path, exist_ok=True)
    return path


def _file_path(filename, year=None):
    return os.path.join(_year_dir(year), filename)


def _ensure_file(filename, default_data, year=None):
    path = _file_path(filename, year)
    if not os.path.exists(path):
        with open(path, "w", encoding="utf-8") as f:
            json.dump(default_data, f, indent=4, ensure_ascii=False)
    return path


def _read_json(filename, default_data=None, year=None):
    if default_data is None:
        default_data = []
    path = _ensure_file(filename, default_data, year)
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default_data.copy() if isinstance(default_data, list) else dict(default_data)


def _write_json(filename, data, year=None):
    path = _file_path(filename, year)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)
    return True


def init_db(year=None):
    _ensure_file("users.json", [], year)
    _ensure_file("orders.json", [], year)
    _ensure_file("line.json", [], year)
    _ensure_file("bill.json", [], year)
    return True


def _next_id(rows):
    if not rows:
        return 1
    return max(int(row.get("id", 0)) for row in rows) + 1


# ---------------- USERS ----------------

def get_all_users(year=None):
    return _read_json("users.json", [], year)


def get_user_by_mobile(mobile, year=None):
    mobile = str(mobile).strip()
    users = _read_json("users.json", [], year)
    for user in users:
        if str(user.get("mobile_no", "")).strip() == mobile:
            return user
    return None


def get_user_by_id(user_id, year=None):
    users = _read_json("users.json", [], year)
    for user in users:
        if int(user.get("id", 0)) == int(user_id):
            return user
    return None


def create_user_record(name, mobile, address="", landmark=None, who="User", pcp=35, year=None):
    users = _read_json("users.json", [], year)

    existing = get_user_by_mobile(mobile, year)
    if existing:
        return existing

    new_user = {
        "id": _next_id(users),
        "name": str(name).strip(),
        "who": who if who in ["User", "Admin", "Worker"] else "User",
        "pcp": float(pcp),
        "mobile_no": str(mobile).strip(),
        "add": str(address).strip(),
        # Store coordinates here only
        "landmark": landmark if isinstance(landmark, list) else [],
        "refrence_Img": [],
        "profile_pic": "",
        "created_at": datetime.now().isoformat()
        # "lat" and "lng" removed from here
    }

    users.append(new_user)
    _write_json("users.json", users, year)
    return new_user


def update_user_location(user_id, lat, lng, year=None):
    users = _read_json("users.json", [], year)
    for user in users:
        if int(user["id"]) == int(user_id):
            # Update only the landmark array with the new coordinates
            user["landmark"] = [lat, lng]
            
            # Remove lat/lng keys if they happen to exist from old records
            user.pop("lat", None)
            user.pop("lng", None)
            
            _write_json("users.json", users, year)
            return True
    return False


def update_user_profile_pic(user_id, profile_pic_path, year=None):
    users = _read_json("users.json", [], year)
    for user in users:
        if int(user["id"]) == int(user_id):
            user["profile_pic"] = profile_pic_path
            _write_json("users.json", users, year)
            return True
    return False



def add_user_ref_img(user_id, img_path, year=None):
    users = _read_json("users.json", [], year)
    for user in users:
        if int(user["id"]) == int(user_id):
            if "refrence_Img" not in user or not isinstance(user["refrence_Img"], list):
                user["refrence_Img"] = []

            if len(user["refrence_Img"]) >= 6:
                return False

            user["refrence_Img"].append(img_path)
            _write_json("users.json", users, year)
            return True
    return False

def delete_user_ref_img(user_id, img_path, year=None):
    users = _read_json("users.json", [], year)
    for user in users:
        if int(user["id"]) == int(user_id):
            imgs = user.get("refrence_Img", [])
            if img_path in imgs:
                try:
                    full_path = os.path.join(os.getcwd(), img_path)
                    if os.path.exists(full_path):
                        os.remove(full_path)
                except Exception:
                    pass

                imgs.remove(img_path)
                user["refrence_Img"] = imgs
                _write_json("users.json", users, year)
                return True
    return False
# ---------------- ORDERS ----------------

def get_all_orders(year=None):
    return _read_json("orders.json", [], year)


def create_order_record(user_id, items, created_at=None, location=None, delivery_date=None,
                        totalamount=0, paidamount=0, status="Pending", paymentstatus="Unpaid", year=None):
    orders = _read_json("orders.json", [], year)

    load = 0
    empty = 0

    for item in items:
        item_id = str(item.get("id", "")).lower()
        qty = int(item.get("quantity", 0))
        if item_id == "20l":
            load += qty
        elif item_id == "empty":
            empty += qty

    new_order = {
        "id": _next_id(orders),
        "userid": int(user_id),
        "load": load,
        "empty": empty,
        "created_at": created_at or datetime.now().isoformat(),
        "delivery_date": delivery_date,
        "location": location if isinstance(location, dict) else {},
        "item": items if isinstance(items, list) else [],
        "totalamount": float(totalamount),
        "paidamount": float(paidamount),
        "status": status,
        "paymentstatus": paymentstatus
    }

    orders.append(new_order)
    _write_json("orders.json", orders, year)
    return new_order


def get_user_orders(user_id, year=None):
    orders = _read_json("orders.json", [], year)
    return [o for o in orders if int(o.get("userid", 0)) == int(user_id)]


def get_order_by_id(order_id, year=None):
    orders = _read_json("orders.json", [], year)
    for order in orders:
        if int(order.get("id", 0)) == int(order_id):
            return order
    return None


def cancel_order_record(order_id, year=None):
    orders = _read_json("orders.json", [], year)
    for order in orders:
        if int(order["id"]) == int(order_id):
            order["status"] = "Cancelled"
            _write_json("orders.json", orders, year)
            return True
    return False


def update_order_items(order_id, items, year=None):
    orders = _read_json("orders.json", [], year)
    for order in orders:
        if int(order["id"]) == int(order_id):
            order["item"] = items if isinstance(items, list) else []

            load = 0
            empty = 0
            for item in order["item"]:
                item_id = str(item.get("id", "")).lower()
                qty = int(item.get("quantity", 0))
                if item_id == "20l":
                    load += qty
                elif item_id == "empty":
                    empty += qty

            order["load"] = load
            order["empty"] = empty
            _write_json("orders.json", orders, year)
            return True
    return False


def update_order_location(order_id, location, year=None):
    orders = _read_json("orders.json", [], year)
    for order in orders:
        if int(order["id"]) == int(order_id):
            order["location"] = location if isinstance(location, dict) else {}
            _write_json("orders.json", orders, year)
            return True
    return False


# ---------------- LINE ----------------

def get_all_lines(year=None):
    return _read_json("line.json", [], year)


def add_line_record(data, year=None):
    rows = _read_json("line.json", [], year)
    new_row = {
        "id": _next_id(rows),
        **data
    }
    rows.append(new_row)
    _write_json("line.json", rows, year)
    return new_row


# ---------------- BILL ----------------

def get_all_bills(year=None):
    return _read_json("bill.json", [], year)


def add_bill_record(data, year=None):
    rows = _read_json("bill.json", [], year)
    new_row = {
        "id": _next_id(rows),
        **data
    }
    rows.append(new_row)
    _write_json("bill.json", rows, year)
    return new_row