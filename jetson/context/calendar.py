import pathlib
from datetime import datetime


def _parse_dt(dt_str: str) -> datetime | None:
    try:
        return datetime.strptime(dt_str.strip(), "%Y%m%dT%H%M%S")
    except Exception:
        return None


def load_events_from_ics(ics_path: str) -> list[dict]:
    path = pathlib.Path(ics_path)
    if not path.exists():
        return []

    events = []
    current = None
    for line in path.read_text().splitlines():
        line = line.strip()
        if line == "BEGIN:VEVENT":
            current = {}
        elif line == "END:VEVENT":
            if current:
                events.append(current)
            current = None
        elif current is not None and ":" in line:
            key, value = line.split(":", 1)
            key = key.upper()
            if key == "DTSTART":
                current["start"] = _parse_dt(value)
            elif key == "DTEND":
                current["end"] = _parse_dt(value)
            elif key == "SUMMARY":
                current["summary"] = value
            elif key == "LOCATION":
                current["location"] = value
    # filter invalid
    valid = []
    for ev in events:
        if isinstance(ev.get("start"), datetime) and isinstance(ev.get("end"), datetime):
            valid.append(ev)
    return sorted(valid, key=lambda e: e["start"])


def _fmt_event(ev: dict) -> str:
    loc = f" @ {ev['location']}" if ev.get("location") else ""
    return f"{ev['summary']} ({ev['start'].strftime('%b %d %H:%M')} - {ev['end'].strftime('%H:%M')}){loc}"


def summarize_schedule(events: list[dict], now: datetime | None = None) -> str:
    now = now or datetime.now()
    if not events:
        return "No events scheduled."

    current = None
    prev_events = []
    next_events = []

    for ev in events:
        if ev["start"] <= now < ev["end"]:
            current = ev
        elif ev["end"] <= now:
            prev_events.append(ev)
        else:
            next_events.append(ev)

    prev_events = prev_events[-2:] if prev_events else []
    next_events = next_events[:2] if next_events else []

    parts = []
    if current:
        parts.append(f"Current event: {_fmt_event(current)}")
    if prev_events:
        parts.append(
            "Earlier: " + "; ".join(_fmt_event(ev) for ev in prev_events)
        )
    if next_events:
        parts.append(
            "Upcoming: " + "; ".join(_fmt_event(ev) for ev in next_events)
        )

    if not parts:
        parts.append("No active events; upcoming schedule:\n" + "; ".join(_fmt_event(ev) for ev in events[:3]))

    return " | ".join(parts)


def load_and_summarize_schedule(ics_path: str, now: datetime | None = None) -> str:
    events = load_events_from_ics(ics_path)
    return summarize_schedule(events, now=now)
