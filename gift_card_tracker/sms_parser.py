import hashlib
import os
import re
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Iterable, Optional

import gspread
from dateutil import tz

import config


ONE4ALL_REGEX = re.compile(
    r"You have GBP\s+(?P<gbp>[0-9]+(?:\.[0-9]{1,2})?)\s+available on your One4all Gift Card ending with\s+(?P<last4>\d{4})",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class BalanceEvent:
    last4: str
    balance_gbp: float
    query_date: str
    timestamp: str
    message_id: int

    @property
    def fingerprint(self) -> str:
        payload = f"{self.last4}|{self.balance_gbp:.2f}|{self.timestamp}".encode("utf-8")
        return hashlib.sha1(payload).hexdigest()


def get_messages_db_path() -> str:
    home = os.path.expanduser("~")
    return os.path.join(home, "Library", "Messages", "chat.db")


def connect_chat_db(db_path: str) -> sqlite3.Connection:
    # read-only connection: prevents accidental writes
    uri = f"file:{db_path}?mode=ro"
    return sqlite3.connect(uri, uri=True)


def fetch_one4all_messages(conn: sqlite3.Connection, max_rows: Optional[int]) -> list[tuple[int, int, str]]:
    # Apple epoch is 2001-01-01. date is usually nanoseconds on newer macOS.
    limit_sql = "" if not max_rows else "LIMIT ?"

    sql = f"""
    SELECT
        m.ROWID as message_id,
        m.date as apple_date,
        m.text as text
    FROM message m
    WHERE m.text IS NOT NULL
      AND lower(m.text) LIKE '%one4all gift card%'
      AND lower(m.text) LIKE '%you have gbp%'
    ORDER BY m.date DESC
    {limit_sql}
    """

    cur = conn.cursor()
    if max_rows:
        cur.execute(sql, (max_rows,))
    else:
        cur.execute(sql)
    rows = cur.fetchall()
    return [(int(r[0]), int(r[1]), str(r[2])) for r in rows]


def apple_time_to_datetime(apple_time: int, timezone: str) -> datetime:
    # Apple epoch starts 2001-01-01 UTC.
    # In chat.db, message.date is commonly:
    # - nanoseconds since 2001-01-01 (modern macOS)
    # - seconds since 2001-01-01 (older)
    apple_epoch = datetime(2001, 1, 1, tzinfo=tz.UTC)

    # Heuristic: nanoseconds in 2026 are ~1e18; seconds are ~1e9.
    # Some DBs store in nanoseconds but still below 1e18 depending on date.
    if apple_time > 10**12:
        seconds = apple_time / 1_000_000_000
    else:
        seconds = float(apple_time)

    dt_utc = apple_epoch + timedelta(seconds=seconds)
    target_tz = tz.gettz(timezone)
    return dt_utc if target_tz is None else dt_utc.astimezone(target_tz)


def parse_balance_events(rows: Iterable[tuple[int, int, str]], timezone: str) -> list[BalanceEvent]:
    events: list[BalanceEvent] = []

    for message_id, apple_date, text in rows:
        m = ONE4ALL_REGEX.search(text)
        if not m:
            continue

        balance = float(m.group("gbp"))
        last4 = m.group("last4")

        # Fallback timestamp if conversion fails
        # We'll just store ISO string of now.
        try:
            dt = apple_time_to_datetime(apple_date, timezone)
            query_date = dt.strftime("%Y-%m-%d")
            timestamp = dt.strftime("%Y-%m-%d %H:%M:%S")
        except Exception:
            now = datetime.now(tz=tz.gettz(timezone) or tz.UTC)
            query_date = now.strftime("%Y-%m-%d")
            timestamp = now.strftime("%Y-%m-%d %H:%M:%S")

        events.append(
            BalanceEvent(
                last4=last4,
                balance_gbp=balance,
                query_date=query_date,
                timestamp=timestamp,
                message_id=message_id,
            )
        )

    # De-dupe by message_id
    uniq: dict[int, BalanceEvent] = {}
    for ev in events:
        uniq[ev.message_id] = ev

    # Oldest first for nicer append order
    return sorted(uniq.values(), key=lambda e: e.message_id)


def open_sheet(credentials_path: str, sheet_id: str):
    gc = gspread.service_account(filename=credentials_path)
    return gc.open_by_key(sheet_id)


def ensure_worksheet(sh, worksheet_name: str):
    header = ["Card Last 4", "Balance GBP", "Query Date", "Timestamp", "Message ID", "Fingerprint"]

    try:
        ws = sh.worksheet(worksheet_name)
    except Exception:
        ws = sh.add_worksheet(title=worksheet_name, rows=1000, cols=10)
        ws.append_row(header)
        return ws

    # Ensure header exists
    try:
        first_row = ws.row_values(1)
    except Exception:
        first_row = []

    if first_row != header:
        if not first_row:
            ws.update("A1:F1", [header])
        # If it already has a different header, we leave it alone.

    return ws


def append_events(ws, events: list[BalanceEvent], existing_message_ids: set[int], existing_fingerprints: set[str]):
    new_events = [
        e
        for e in events
        if (e.message_id not in existing_message_ids) and (e.fingerprint not in existing_fingerprints)
    ]
    if not new_events:
        return 0

    rows = [
        [e.last4, f"{e.balance_gbp:.2f}", e.query_date, e.timestamp, str(e.message_id), e.fingerprint]
        for e in new_events
    ]
    ws.append_rows(rows, value_input_option="USER_ENTERED")
    return len(rows)


def fetch_existing_message_ids(ws, limit_rows: int = 20000) -> set[int]:
    # Reads column E (Message ID) and returns a set of ints.
    # We cap reads to avoid pulling an entire huge sheet.
    try:
        values = ws.col_values(5)  # 1-indexed
    except Exception:
        return set()

    # Drop header
    values = values[1:]
    if limit_rows:
        values = values[:limit_rows]

    out: set[int] = set()
    for v in values:
        v = (v or "").strip()
        if not v:
            continue
        try:
            out.add(int(v))
        except ValueError:
            continue
    return out


def fetch_existing_fingerprints(ws, limit_rows: int = 20000) -> set[str]:
    # Reads column F (Fingerprint) and returns a set of strings.
    try:
        values = ws.col_values(6)  # 1-indexed
    except Exception:
        return set()

    # Drop header
    values = values[1:]
    if limit_rows:
        values = values[:limit_rows]

    out: set[str] = set()
    for v in values:
        v = (v or "").strip()
        if v:
            out.add(v)
    return out


def main():
    db_path = get_messages_db_path()
    if not os.path.exists(db_path):
        raise SystemExit(f"Messages database not found: {db_path}")

    if not config.SHEET_ID:
        raise SystemExit("Please set SHEET_ID in config.py")

    credentials_path = os.path.join(os.path.dirname(__file__), "credentials.json")
    if not os.path.exists(credentials_path):
        raise SystemExit(
            "Missing credentials.json. Download Service Account JSON and save as gift_card_tracker/credentials.json"
        )

    conn = connect_chat_db(db_path)
    try:
        rows = fetch_one4all_messages(conn, config.MAX_ROWS)
    finally:
        conn.close()

    events = parse_balance_events(rows, config.TIMEZONE)

    sh = open_sheet(credentials_path, config.SHEET_ID)
    ws = ensure_worksheet(sh, config.WORKSHEET_NAME)

    existing_ids = fetch_existing_message_ids(ws)
    existing_fps = fetch_existing_fingerprints(ws)
    written = append_events(ws, events, existing_ids, existing_fps)

    if written == 0:
        print(f"No new One4all messages to write (worksheet '{config.WORKSHEET_NAME}').")
    else:
        print(f"Wrote {written} new rows to worksheet '{config.WORKSHEET_NAME}'.")


if __name__ == "__main__":
    main()
