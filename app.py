from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from pathlib import Path
from datetime import date, datetime, timedelta
import json, uuid, os
from werkzeug.utils import secure_filename
from dotenv import load_dotenv
from pywebpush import webpush, WebPushException

load_dotenv()

VAPID_PRIVATE_KEY = os.getenv("VAPID_PRIVATE_KEY")
VAPID_PUBLIC_KEY = os.getenv("VAPID_PUBLIC_KEY")
VAPID_CLAIMS = {"sub": "mailto:YOUR_EMAIL@gmail.com"}

BASE = Path(__file__).resolve().parent
DATA_DIR = BASE / "data"
UPLOAD_DIR = BASE / "uploads"
DATA_FILE = DATA_DIR / "inventory.json"
SUBSCRIPTIONS_FILE = DATA_DIR / "push_subscriptions.json"
ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "webp"}

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "change-this-for-deployment")
DATA_DIR.mkdir(exist_ok=True)
UPLOAD_DIR.mkdir(exist_ok=True)

RECIPES = {
    "apple": ["Apple cinnamon oats", "Apple salad with yogurt", "Warm apple toast"],
    "banana": ["Banana pancakes", "Banana smoothie", "Banana oat muffins"],
    "milk": ["Creamy vegetable soup", "Homemade yogurt", "Milk oats porridge"],
    "tomato": ["Tomato rice", "Fresh tomato salsa", "Tomato soup"],
    "bread": ["Vegetable toast", "Bread upma", "Grilled sandwich"],
    "potato": ["Potato roast", "Aloo paratha", "Potato soup"],
    "egg": ["Vegetable omelette", "Boiled egg salad", "Egg sandwich"],
    "carrot": ["Carrot poriyal", "Carrot soup", "Carrot rice"],
    "default": ["Mixed vegetable stir-fry", "Simple soup", "Use-it-up fried rice"]
}

def load_items():
    if not DATA_FILE.exists():
        return []
    try:
        return json.loads(DATA_FILE.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return []

def save_items(items):
    DATA_FILE.write_text(
        json.dumps(items, indent=2),
        encoding="utf-8"
    )


def load_subscriptions():
    if not SUBSCRIPTIONS_FILE.exists():
        return []

    try:
        return json.loads(
            SUBSCRIPTIONS_FILE.read_text(encoding="utf-8")
        )
    except (json.JSONDecodeError, OSError):
        return []


def save_subscriptions(subscriptions):
    SUBSCRIPTIONS_FILE.write_text(
        json.dumps(subscriptions, indent=2),
        encoding="utf-8"
    )

def parse_date(value):
    return date.fromisoformat(value)

def enrich(item):
    today = date.today()
    expiry = parse_date(item["expiry_date"])
    days_left = (expiry - today).days
    item["days_left"] = days_left
    item["expiry_label"] = expiry.strftime("%d %b %Y")
    item["purchase_label"] = parse_date(item["purchase_date"]).strftime("%d %b %Y")
    # Keep expired items in history for seven days; mark the first 24 hours as grace period.
    item["in_grace"] = days_left == -1
    item["days_since_expiry"] = max(0, -days_left)
    item["auto_delete_on"] = (expiry + timedelta(days=7)).isoformat()
    item["recipes"] = RECIPES.get(item["name"].lower(), RECIPES["default"])
    if days_left < -7:
        item["status"] = "ready_to_remove"
    elif days_left < -1:
        item["status"] = "expired"
    elif days_left == -1:
        item["status"] = "grace"
    elif days_left == 0:
        item["status"] = "today"
    elif days_left <= 7:
        item["status"] = "soon"
    else:
        item["status"] = "fresh"
    return item

def cleanup_and_enrich():
    items = load_items()
    today = date.today()
    kept = []
    for item in items:
        try:
            expiry = parse_date(item["expiry_date"])
        except (ValueError, KeyError):
            continue
        # Automatically remove from inventory/history seven days after expiry.
        if today > expiry + timedelta(days=7):
            continue
        kept.append(enrich(item))
    if len(kept) != len(items):
        save_items([{k: v for k, v in item.items() if k not in {
            "days_left", "expiry_label", "purchase_label", "in_grace",
            "days_since_expiry", "auto_delete_on", "recipes", "status"
        }} for item in kept])
    return kept

def dashboard_stats(items):
    today = date.today()
    return {
        "total": len(items),
        "fresh": sum(i["days_left"] > 7 for i in items),
        "soon": sum(0 <= i["days_left"] <= 7 for i in items),
        "expired": sum(i["days_left"] < 0 for i in items),
        "today": sum(i["days_left"] == 0 for i in items),
    }

@app.route("/")
def index():
    items = cleanup_and_enrich()
    active = [i for i in items if i["days_left"] >= -1]
    history = [i for i in items if i["days_left"] < -1]
    active.sort(key=lambda x: x["days_left"])
    history.sort(key=lambda x: x["days_left"], reverse=True)
    return render_template("index.html", items=active, history=history,
                           stats=dashboard_stats(items), today=date.today().isoformat())

@app.route("/add", methods=["POST"])
def add_item():
    name = request.form.get("name", "").strip()
    category = request.form.get("category", "Other").strip()
    purchase_date = request.form.get("purchase_date", "").strip()
    expiry_date = request.form.get("expiry_date", "").strip()
    storage = request.form.get("storage", "Refrigerated").strip()
    source = request.form.get("expiry_source", "Predicted").strip()
    if not name or not purchase_date or not expiry_date:
        flash("Please enter the item name, purchase date, and expiry date.", "error")
        return redirect(url_for("index"))
    try:
        pdate, edate = parse_date(purchase_date), parse_date(expiry_date)
        if edate < pdate:
            flash("Expiry date cannot be earlier than purchase date.", "error")
            return redirect(url_for("index"))
    except ValueError:
        flash("Please enter valid dates.", "error")
        return redirect(url_for("index"))

    image_name = ""
    photo = request.files.get("photo")
    if photo and photo.filename:
        ext = photo.filename.rsplit(".", 1)[-1].lower() if "." in photo.filename else ""
        if ext in ALLOWED_EXTENSIONS:
            image_name = f"{uuid.uuid4().hex}.{ext}"
            photo.save(UPLOAD_DIR / secure_filename(image_name))
        else:
            flash("Photo must be PNG, JPG, JPEG, or WEBP.", "error")
            return redirect(url_for("index"))

    item = {
        "id": uuid.uuid4().hex[:10], "name": name, "category": category,
        "purchase_date": purchase_date, "expiry_date": expiry_date,
        "storage": storage, "expiry_source": source, "image": image_name,
        "outcome": "pending", "created_at": datetime.now().isoformat(timespec="seconds")
    }
    all_items = load_items()
    all_items.append(item)
    save_items(all_items)
    flash(f"{name} added to your inventory.", "success")
    return redirect(url_for("index"))

@app.route("/outcome/<item_id>", methods=["POST"])
def outcome(item_id):
    value = request.form.get("outcome", "pending")
    allowed = {"used_after_first", "used_after_second", "expired_unused", "discarded", "used_early"}
    if value not in allowed:
        value = "pending"
    items = load_items()
    for item in items:
        if item["id"] == item_id:
            item["outcome"] = value
            item["outcome_logged_at"] = datetime.now().isoformat(timespec="seconds")
            break
    save_items(items)
    flash("Feedback saved. This demo logs the outcome for future model improvement.", "success")
    return redirect(url_for("index"))

@app.route("/delete/<item_id>", methods=["POST"])
def delete_item(item_id):
    items = [item for item in load_items() if item["id"] != item_id]
    save_items(items)
    flash("Item removed from inventory.", "success")
    return redirect(url_for("index"))

@app.route("/api/push/public-key")
def push_public_key():
    if not VAPID_PUBLIC_KEY:
        return jsonify({"error": "VAPID public key is not configured"}), 500

    return jsonify({"publicKey": VAPID_PUBLIC_KEY})


@app.route("/api/summary")
def api_summary():
    items = cleanup_and_enrich()
    return jsonify(dashboard_stats(items))
@app.route("/api/push/subscribe", methods=["POST"])
def push_subscribe():
    subscription = request.get_json(silent=True)

    if not subscription or not subscription.get("endpoint"):
        return jsonify({"error": "Invalid subscription"}), 400

    subscriptions = load_subscriptions()

    subscriptions = [
        sub for sub in subscriptions
        if sub.get("endpoint") != subscription.get("endpoint")
    ]

    subscriptions.append(subscription)
    save_subscriptions(subscriptions)

    return jsonify({"message": "Subscription saved"}), 201

@app.route("/api/push/test", methods=["POST"])
def push_test():
    if not VAPID_PRIVATE_KEY or not VAPID_PUBLIC_KEY:
        return jsonify({"error": "VAPID keys are not configured"}), 500

    subscriptions = load_subscriptions()

    if not subscriptions:
        return jsonify({
            "error": "Enable notifications on a browser first"
        }), 400

    results = []

    for subscription in subscriptions:
        try:
            webpush(
                subscription_info=subscription,
                data=json.dumps({
                    "title": "FreshTrack Reminder",
                    "body": "Push notifications are working!"
                }),
                vapid_private_key=VAPID_PRIVATE_KEY,
                vapid_claims=VAPID_CLAIMS
            )
            results.append("sent")

        except WebPushException as exc:
            results.append(f"failed: {exc}")

    return jsonify({"results": results})


if __name__ == "__main__":
    app.run(debug=True)
