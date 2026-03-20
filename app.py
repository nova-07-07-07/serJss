import os, time
from flask import Flask, request, jsonify, render_template, send_from_directory
from utils.auth import create_token, verify_token, create_otp, verify_otp
from utils.json_db import get_user_by_mobile, create_user_record, create_order_record, get_user_orders, cancel_order_record, update_user_profile_pic, update_user_location, add_user_ref_img, delete_user_ref_img, update_order_items, update_order_location
from werkzeug.utils import secure_filename
# from datetime import datetime # No longer needed for parsing

app = Flask(__name__, template_folder='.')

UPLOAD_FOLDER = 'uploads'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/home")
def dashboard():
    return render_template("dashboard.html")

@app.route("/config")
def get_config():
    return send_from_directory('.', 'config.json')

# /downlode
@app.route('/download')
def download():
    return send_from_directory('./static','myapp.apk')



@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

@app.route("/request-otp", methods=["POST"])
def request_otp():
    mobile = request.json.get("mobile")
    if not mobile:
        return {"error": "Mobile number is required"}, 400
    create_otp(mobile)
    return {"message": "OTP sent successfully"}, 200

@app.route("/user/me", methods=["GET"])
def get_current_user():
    auth_token = request.headers.get("Authorization")
    if not auth_token:
        return jsonify({"error": "No token provided"}), 401

    mobile = verify_token(auth_token)
    if not mobile:
        return jsonify({"error": "Invalid or expired token"}), 401

    user = get_user_by_mobile(mobile)
    if not user:
        return jsonify({"error": "User not found"}), 404
    return jsonify(user)

@app.route("/login", methods=["POST"])
def login():
    data = request.json
    mobile = str(data.get("mobile", "")).strip()
    otp = str(data.get("otp", "")).strip()
    name = data.get("name", "")

    if not mobile or not otp:
        return {"error": "Mobile and OTP are required"}, 400

    # Use JSON DB instead of SQL
    user = get_user_by_mobile(mobile)

    if not user:
        if not name:
            # Verify OTP exists but do not consume it yet
            if not verify_otp(mobile, otp, consume=False):
                return {"error": "Invalid or expired OTP"}, 401
            return jsonify({"error": "new_user_name_required"}), 400

    # Verify and consume OTP now that we are proceeding
    if not verify_otp(mobile, otp, consume=True):
        return {"error": "Invalid or expired OTP"}, 401

    if not user:
        user = create_user_record(name, mobile)

    token = create_token(mobile)
    # Access dict keys instead of object attributes
    return jsonify({"token": token, "user_id": user["id"], "name": user["name"], "profile_pic": user.get("profile_pic"), "lat": user.get("lat"), "lng": user.get("lng")})

@app.route("/order", methods=["POST"])
def create_order():
    d = request.json or {}
    user_id = d.get("user_id")
    items = d.get("items", [])
    created_at = d.get("created_at")
    location = d.get("location")


    if not user_id:
        return {"error": "user_id is required"}, 400

    if not items:
        return {"error": "Items list is empty"}, 400

    try:
        user_id = int(user_id)
    except (ValueError, TypeError):
        return {"error": "Invalid user_id"}, 400

    # new order is exactly 1x20l ?
    is_new_only_1x20l = (
        len(items) == 1 and
        str(items[0].get("id")).lower() == "20l" and
        int(items[0].get("quantity", 0)) == 1
    )
    o = create_order_record(user_id, items, created_at, location)
    
    return {
        "id": o["id"],
        "message": "Order created successfully"
    }, 200

@app.route("/orders/<int:user_id>", methods=["GET"])
def get_orders(user_id):
    # Fetch directly from JSON
    orders = get_user_orders(user_id)
    return jsonify(orders)

@app.route("/order/<int:order_id>/cancel", methods=["POST"])
def cancel_order(order_id):
    # In a real app, you'd verify the user owns this order
    if cancel_order_record(order_id):
        return {"message": "Order cancelled successfully"}, 200
    else:
        return {"error": "Order not found"}, 404

@app.route("/order/<int:order_id>/update", methods=["POST"])
def update_order(order_id):
    d = request.json or {}
    items = d.get("items", [])
    
    if not items:
        return {"error": "No items provided"}, 400
        
    if update_order_items(order_id, items):
        return {"message": "Order updated successfully"}, 200
    return {"error": "Order not found or update failed"}, 404

@app.route("/order/<int:order_id>/location", methods=["POST"])
def update_order_loc(order_id):
    d = request.json or {}
    lat = d.get("lat")
    lng = d.get("lng")
    
    if update_order_location(order_id, {"lat": lat, "lng": lng}):
        return {"message": "Order location updated successfully"}, 200
    return {"error": "Order not found"}, 404

@app.route('/upload/profile-picture/<int:user_id>', methods=['POST'])
def upload_profile_picture(user_id):

    auth_token = request.headers.get("Authorization")
    if not auth_token:
        return jsonify({"error": "No token provided"}), 401

    mobile = verify_token(auth_token)
    if not mobile:
        return jsonify({"error": "Invalid or expired token"}), 401

    user = get_user_by_mobile(mobile)
    if not user or user["id"] != user_id:
        return jsonify({"error": "Unauthorized or user mismatch"}), 403

    if 'profile_pic' not in request.files:
        return jsonify({'error': 'No file part'}), 400

    file = request.files['profile_pic']
    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400

    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    import glob
    # delete all old files for this user
    old_files = glob.glob(os.path.join(app.config['UPLOAD_FOLDER'], f"{user_id}_*.*"))
    for f in old_files:
        try:
            os.remove(f)
        except:
            pass

    # save new file
    _, ext = os.path.splitext(secure_filename(file.filename))
    new_filename = f"{user_id}_1{ext}"
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], new_filename)

    file.save(filepath)

    # update DB (store single path, not array)
    if update_user_profile_pic(user_id, f'uploads/{new_filename}'):
        return jsonify({
            'message': 'Uploaded successfully',
            'filepath': f'uploads/{new_filename}'
        }), 200

    # rollback if DB fails
    if os.path.exists(filepath):
        os.remove(filepath)

    return jsonify({'error': 'DB update failed'}), 500

@app.route('/upload/ref-image/<int:user_id>', methods=['POST'])
def upload_ref_image(user_id):
    auth_token = request.headers.get("Authorization")
    if not auth_token: return jsonify({"error": "No token provided"}), 401
    mobile = verify_token(auth_token)
    if not mobile: return jsonify({"error": "Invalid token"}), 401
    user = get_user_by_mobile(mobile)
    if not user or user["id"] != user_id: return jsonify({"error": "Unauthorized"}), 403

    if 'ref_img' not in request.files: return {'error': 'No file part'}, 400
    file = request.files['ref_img']
    if file.filename == '': return {'error': 'No selected file'}, 400

    if file:
        _, ext = os.path.splitext(secure_filename(file.filename))
        # Unique name: ref_USERID_TIMESTAMP.ext
        filename = f"ref_{user_id}_{int(time.time()*1000)}{ext}"
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        
        os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
        file.save(filepath)
        
        db_path = f"uploads/{filename}"
        if add_user_ref_img(user_id, db_path):
            return jsonify({'message': 'Uploaded', 'filepath': db_path}), 200
        else:
            os.remove(filepath)
            return jsonify({'error': 'Limit reached (Max 6 images)'}), 400
    return {'error': 'Upload failed'}, 500

@app.route('/delete/ref-image/<int:user_id>', methods=['POST'])
def delete_ref_image(user_id):
    auth_token = request.headers.get("Authorization")
    if not auth_token: return jsonify({"error": "No token"}), 401
    if not verify_token(auth_token): return jsonify({"error": "Invalid token"}), 401
    
    path = request.json.get('filepath')
    if delete_user_ref_img(user_id, path):
        os.remove(os.path.join(os.getcwd(), path))
        return jsonify({"message": "Deleted"}), 200
    return jsonify({"error": "Failed to delete"}), 400

@app.route("/user/location", methods=["POST"])
def save_location():
    d = request.json
    if update_user_location(d["user_id"], d["lat"], d["lng"]):
        return {"message": "Location updated"}, 200
    return {"error": "User not found"}, 404

if __name__ == "__main__":
    app.run( debug=True )
