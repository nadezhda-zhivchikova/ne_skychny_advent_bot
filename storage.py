from __future__ import annotations

import json
from dataclasses import dataclass, asdict
from datetime import date
from pathlib import Path
from typing import Dict, List, Optional


DATA_DIR = Path(__file__).parent / "data"
DATA_DIR.mkdir(exist_ok=True)

USERS_FILE = DATA_DIR / "users.json"
ADVENT_FILE = DATA_DIR / "advent_days.json"


@dataclass
class User:
    chat_id: int
    is_subscribed: bool = True
    last_sent_date: Optional[str] = None  # ISO-format date


@dataclass
class AdventDay:
    day: str  # ISO date: YYYY-MM-DD
    title: str
    description: str


def _read_json(path: Path, default):
    if not path.exists():
        return default
    try:
        with path.open("r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default


def _write_json(path: Path, data) -> None:
    with path.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def load_users() -> Dict[int, User]:
    raw = _read_json(USERS_FILE, {})
    result: Dict[int, User] = {}
    for k, v in raw.items():
        try:
            chat_id = int(k)
            result[chat_id] = User(
                chat_id=chat_id,
                is_subscribed=v.get("is_subscribed", True),
                last_sent_date=v.get("last_sent_date"),
            )
        except Exception:
            continue
    return result


def save_users(users: Dict[int, User]) -> None:
    raw = {str(k): asdict(v) for k, v in users.items()}
    _write_json(USERS_FILE, raw)


def upsert_user(chat_id: int, is_subscribed: Optional[bool] = None) -> User:
    users = load_users()
    user = users.get(chat_id, User(chat_id=chat_id))
    if is_subscribed is not None:
        user.is_subscribed = is_subscribed
    users[chat_id] = user
    save_users(users)
    return user


def set_user_last_sent(chat_id: int, d: date) -> None:
    users = load_users()
    user = users.get(chat_id, User(chat_id=chat_id))
    user.last_sent_date = d.isoformat()
    users[chat_id] = user
    save_users(users)


def get_subscribed_users() -> List[User]:
    return [u for u in load_users().values() if u.is_subscribed]


def load_advent_days() -> Dict[str, AdventDay]:
    raw = _read_json(ADVENT_FILE, {})
    result: Dict[str, AdventDay] = {}
    for k, v in raw.items():
        result[k] = AdventDay(
            day=k,
            title=v.get("title", ""),
            description=v.get("description", ""),
        )
    return result


def save_advent_days(days: Dict[str, AdventDay]) -> None:
    raw = {k: {"title": v.title, "description": v.description} for k, v in days.items()}
    _write_json(ADVENT_FILE, raw)


def set_advent_day(d: date, title: str, description: str) -> AdventDay:
    days = load_advent_days()
    key = d.isoformat()
    day = AdventDay(day=key, title=title, description=description)
    days[key] = day
    save_advent_days(days)
    return day


def get_advent_day(d: date) -> Optional[AdventDay]:
    days = load_advent_days()
    return days.get(d.isoformat())


def list_advent_days() -> List[AdventDay]:
    return sorted(load_advent_days().values(), key=lambda x: x.day)


def delete_advent_day(d: date) -> bool:
    """Удалить адвент за указанную дату. Возвращает True, если день существовал и был удалён."""
    days = load_advent_days()
    key = d.isoformat()
    if key in days:
        del days[key]
        save_advent_days(days)
        return True
    return False




