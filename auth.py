"""
Authorized users manager – stores chat IDs of users who provided the correct key.
"""

import json
import os

AUTH_FILE  = "authorized_users.json"
ACCESS_KEY = "SOLAPE2026"


def _load() -> list:
    if not os.path.exists(AUTH_FILE):
        return []
    try:
        with open(AUTH_FILE, "r") as f:
            return json.load(f)
    except Exception:
        return []


def _save(users: list):
    with open(AUTH_FILE, "w") as f:
        json.dump(users, f)


def is_authorized(chat_id: int) -> bool:
    return chat_id in _load()


def authorize(chat_id: int):
    users = _load()
    if chat_id not in users:
        users.append(chat_id)
        _save(users)


def get_all_authorized() -> list:
    return _load()
