import streamlit as st
import os

# Path to a local session file (used only on Streamlit Cloud or localhost)
SESSION_FILE = ".user_session"

def save_session(email, token):
    with open(SESSION_FILE, "w") as f:
        f.write(f"{email}|{token}")

def load_session():
    if os.path.exists(SESSION_FILE):
        with open(SESSION_FILE, "r") as f:
            content = f.read().strip()
            if "|" in content:
                email, token = content.split("|")
                return {"email": email, "token": token}
    return None

def clear_session():
    if os.path.exists(SESSION_FILE):
        os.remove(SESSION_FILE)