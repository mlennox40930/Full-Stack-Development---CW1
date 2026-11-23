from flask import Blueprint, request, jsonify, make_response
from pymongo import MongoClient
import datetime
import jwt
from werkzeug.security import generate_password_hash, check_password_hash

auth_bp = Blueprint('auth_bp', __name__)

client = MongoClient("mongodb://127.0.0.1:27017")
db = client.cinemapulse
users = db.users

SECRET_KEY = "cinemapulse_secret_key"
# ---------------------------------------------------------
# REGISTER AN AUTHENTICATION
# ---------------------------------------------------------
@auth_bp.route("/api/v1.0/auth/register", methods=["POST"])
def register():
    username = request.form.get("username")
    password = request.form.get("password")

    if not username or not password:
        return make_response(jsonify({"error": "Username and password required"}), 400)

    if users.find_one({"username": username}):
        return make_response(jsonify({"error": "Username already exists"}), 400)

    hashed_password = generate_password_hash(password)
    user_doc = {
        "username": username,
        "password": hashed_password,
        "role": request.form.get("role", "user")
    }
    users.insert_one(user_doc)
    return make_response(jsonify({"message": "User registered successfully"}), 201)
# ---------------------------------------------------------
# AUTHENTICATION LOGIN
# ---------------------------------------------------------
@auth_bp.route("/api/v1.0/auth/login", methods=["POST"])
def login():
    username = request.form.get("username")
    password = request.form.get("password")