"""Room assistant: a request in plain English or German -> the booking it means -> the best rooms for it.

"quiet room for 3 people tomorrow at 14:00 for 2 hours", "Gruppenraum für 5 heute um 15 Uhr, 90 Minuten",
"meeting now, just us", "board games in Z this evening". Rule-based (no AI service, works offline): it picks out
day, time, length, people, purpose, private/shared and building; whatever is missing gets a sensible default, and the
answer says what was understood so the user can check it. Rooms come from booking.suggest (same rules as booking).
"""

import re
from datetime import datetime, timedelta

from app import booking
from app.booking import ApiError, slot_start

NUMBER_WORDS = {
    "one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10,
    "eleven": 11, "twelve": 12, "ein": 1, "eine": 1, "einer": 1, "zwei": 2, "drei": 3, "vier": 4, "fünf": 5,
    "sechs": 6, "sieben": 7, "acht": 8, "neun": 9, "zehn": 10, "elf": 11, "zwölf": 12,
}
NUM = r"(\d{1,3}|" + "|".join(NUMBER_WORDS) + r")"
WEEKDAYS = {
    "monday": 0, "tuesday": 1, "wednesday": 2, "thursday": 3, "friday": 4, "saturday": 5, "sunday": 6,
    "montag": 0, "dienstag": 1, "mittwoch": 2, "donnerstag": 3, "freitag": 4, "samstag": 5, "sonntag": 6,
}
PARTS_OF_DAY = [(r"\b(morning|morgens|vormittags?)\b", 9), (r"\b(noon|lunch|mittags?)\b", 12),
                (r"\b(afternoon|nachmittags?)\b", 14), (r"\b(evening|tonight|abends?)\b", 18)]
# purpose keywords, checked in this order (board games before games, ...)
PURPOSES = [
    ("board_games", r"board ?games?|brettspiel"),
    ("event", r"event|party|feier|veranstaltung|celebrat"),
    ("gaming", r"gaming|video ?games?|zocken|games?\b|spielen"),
    ("meeting", r"meeting|besprechung|treffen|call\b|interview|sitzung"),
    ("quiet_study", r"quiet|silent|silence|focus|concentrat|exam|ruhig|leise|stille?|konzentr|prüfung|klausur"),
    ("group_study", r"group|team|together|project|gruppe|zusammen|projekt|lerngruppe"),
]
PRIVATE = r"private|privat|whole room|entire room|just us|only us|exclusive|ganzen raum|nur wir|für uns allein"
SHARED = r"\bshare|\bshared|teilen|geteilt|gemeinsam nutzen"
PEOPLE_WORDS = r"(people|persons?|students?|of us|guys|friends|personen|leute|studenten|studierende|freunde|pers\.?)\b"
GROUP_SIZES = {r"zu zweit": 2, r"zu dritt": 3, r"zu viert": 4, r"zu fünft": 5, r"zu sechst": 6, r"both of us": 2,
               r"the two of us": 2, r"just me": 1, r"only me": 1, r"myself": 1, r"nur ich": 1, r"\balone\b": 1,
               r"(?<!uns )\ballein\b": 1}


def number(word: str) -> int:
    return int(word) if word.isdigit() else NUMBER_WORDS[word]


def parse(text: str, now: datetime) -> dict:
    """What the request asks for. Unknown parts get defaults; `given` lists the parts the text actually named."""
    s = " " + text.lower().replace("’", "'") + " "
    given = set()

    day = now.date()
    if re.search(r"\b(day after tomorrow|übermorgen)\b", s):
        day, _ = now.date() + timedelta(days=2), given.add("day")
    elif re.search(r"\b(tomorrow|morgen)\b", s):
        day, _ = now.date() + timedelta(days=1), given.add("day")
    elif re.search(r"\b(today|heute|now|jetzt|right now|sofort|gleich)\b", s):
        given.add("day")
    else:
        for name, wd in WEEKDAYS.items():
            if re.search(rf"\b{name}\b", s):
                day = now.date() + timedelta(days=(wd - now.weekday()) % 7 or 7)
                given.add("day")
                break

    hours = 1.0
    m = re.search(r"(\d+(?:[.,]\d+)?)\s*(h|hrs?|hours?|stunden?|std)\b", s)
    if m:
        hours, _ = float(m.group(1).replace(",", ".")), given.add("hours")
        s = s.replace(m.group(0), " ")
    elif m := re.search(r"(\d+)\s*(min|mins|minutes?|minuten)\b", s):
        hours, _ = int(m.group(1)) / 60, given.add("hours")
        s = s.replace(m.group(0), " ")
    elif re.search(r"half an hour|halbe stunde", s):
        hours, _ = 0.5, given.add("hours")
    elif re.search(r"\b(an|one|eine) (hour|stunde)\b", s):
        given.add("hours")
    hours = min(booking.MAX_HOURS_PER_DAY, max(0.5, round(hours * 2) / 2))

    seats = None
    for phrase, n in GROUP_SIZES.items():
        if re.search(phrase, s):
            seats = n
            break
    if seats is None and (m := re.search(NUM + r"\s*" + PEOPLE_WORDS, s)):
        seats = number(m.group(1))
        s = s.replace(m.group(0), " ")
    if seats is None and (m := re.search(r"\b(?:for|für)\s+" + NUM + r"\b(?!\s*(?::|\.\d|uhr|am|pm|h\b))", s)):
        seats = number(m.group(1))
        s = s.replace(m.group(0), " ")
    if seats is not None:
        given.add("seats")

    clock = None
    if m := re.search(r"\b(\d{1,2})[:.](\d{2})\b", s):
        clock = (int(m.group(1)), int(m.group(2)))
    elif m := re.search(r"\b(\d{1,2})\s*(am|pm)\b", s):
        h = int(m.group(1)) % 12 + (12 if m.group(2) == "pm" else 0)
        clock = (h, 0)
    elif m := re.search(r"\b(\d{1,2})\s*uhr\b", s):
        clock = (int(m.group(1)), 0)
    elif m := re.search(r"\b(?:at|um|ab|from)\s+(\d{1,2})\b", s):
        h = int(m.group(1))
        clock = (h + 12 if 1 <= h <= 7 else h, 0)   # "at 3" means 15:00 on a campus
    else:
        for pattern, h in PARTS_OF_DAY:
            if re.search(pattern, s):
                clock = (h, 0)
                break
    if clock and clock[0] < 24 and clock[1] < 60:
        given.add("time")
        start = datetime.combine(day, datetime.min.time()).replace(hour=clock[0], minute=clock[1] - clock[1] % 30)
    elif day == now.date():
        start = slot_start(now)
    else:
        start = datetime.combine(day, datetime.min.time()).replace(hour=10)

    purpose = None
    for pid, pattern in PURPOSES:
        if re.search(pattern, s):
            purpose = pid
            given.add("purpose")
            break
    seats = seats or 1
    purpose = purpose or ("quiet_study" if seats == 1 else "group_study")

    mode = "partial"
    if purpose == "event" or re.search(PRIVATE, s):
        mode = "full"
        given.add("mode")
    elif re.search(SHARED, s):
        given.add("mode")

    building = None
    if m := re.search(r"\b(?:in|building|gebäude|haus|trakt)\s+([vnzls])\b", s):
        building = m.group(1).upper()
        given.add("building")

    return {"start": start, "hours": hours, "seats": seats, "purpose": purpose, "mode": mode, "building": building,
            "given": sorted(given)}


def answer(conn, text: str, now: datetime) -> dict:
    """The understood request and up to 3 rooms that can take it, best first."""
    want = parse(text, now)
    out = {"understood": {**{k: v for k, v in want.items() if k != "start"},
                          "date": want["start"].date().isoformat(), "time": f"{want['start']:%H:%M}"},
           "rooms": [], "problem": None}
    if want["start"] < slot_start(now):
        out["problem"] = "past"
        return out
    try:
        booking.validate_times(want["start"], want["hours"], now)
    except ApiError as exc:
        out["problem"] = "too_far" if "days ahead" in exc.message else "times"
        return out
    rooms = booking.suggest(conn, want["start"], want["hours"], want["mode"], want["seats"], want["purpose"], now)
    if want["building"]:
        rooms = [r for r in rooms if r["building"] == want["building"]]
    # right-sized first: a quiet seminar room for 3 beats a quiet lecture hall for 400; for quiet study, quiet first
    quiet = booking.PURPOSE_CLASS[want["purpose"]] == "quiet"
    rooms.sort(key=lambda r: (r["noise_class"] != "quiet" if quiet else 0, r["capacity"] > 4 * want["seats"] + 10,
                              r["capacity"] - want["seats"], r["noise_db"]))
    out["rooms"] = [{key: r[key] for key in ("id", "label", "name", "building", "floor", "capacity", "noise_db",
                                             "noise_class", "seats_free", "people", "rating", "live", "board", "status")}
                    for r in rooms[:3]]
    if not out["rooms"]:
        out["problem"] = "none_free"
    return out
