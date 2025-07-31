import requests
import firebase_admin
from firebase_admin import credentials, firestore
import streamlit as st

# Firebase Config
firebase_api_key = st.secrets["firebase"]["apiKey"]

# Firebase Admin SDK
if not firebase_admin._apps:
    cred = credentials.Certificate(dict(st.secrets["service_account"]))
    firebase_admin.initialize_app(cred)

db = firestore.client()

def signup_user(email, password):
    url = f"https://identitytoolkit.googleapis.com/v1/accounts:signUp?key={firebase_api_key}"
    payload = {
        "email": email,
        "password": password,
        "returnSecureToken": True
    }
    response = requests.post(url, json=payload)
    if response.status_code == 200:
        db.collection("users").document(email).set({"email": email})
        return response.json()
    else:
        return response.json().get("error", {}).get("message", "Signup failed")

def login_user(email, password):
    url = f"https://identitytoolkit.googleapis.com/v1/accounts:signInWithPassword?key={firebase_api_key}"
    payload = {
        "email": email,
        "password": password,
        "returnSecureToken": True
    }
    response = requests.post(url, json=payload)
    if response.status_code == 200:
        return response.json()
    else:
        return response.json().get("error", {}).get("message", "Login failed")