# Usage: python tools/campus3d/gen_building_v.py tools/campus3d/building_v_rooms.json   (V rooms traced from campusplan.aau.at)
"""Generate web/data/building_v.json from rectangles traced off campusplan.aau.at (building V, floors 0 and 1).
Pixel rectangles are in the de-rotated plan frame (origin = building's north-west corner); converted to metres
with the origin at the building centre, x east, z south."""
import json, sys

W, D = 60.0, 29.5
F1, F0 = W / 420, W / 540  # metres per pixel in the two screenshots

def room(fid, f, scale, x0, y0, x1, y1, kind, name=None):
    w, d = (x1 - x0) * scale, (y1 - y0) * scale
    cx, cz = (x0 + x1) / 2 * scale - W / 2, (y0 + y1) / 2 * scale - D / 2
    area = w * d
    cap = {"seminar": min(48, max(12, int(area / 2.2))), "hall": 120, "atrium": 40,
           "office": 2 if area < 25 else 4}.get(kind, 0)
    return {"id": f"V.{f}.{fid}", "floor": f, "x": round(cx, 2), "z": round(cz, 2), "w": round(w, 2),
            "d": round(d, 2), "capacity": cap, "type": kind, "bookable": kind in ("seminar", "hall", "atrium"),
            "name": name or {"seminar": "Seminar room", "office": "Office", "hall": "Hall", "atrium": "Atrium",
                             "wc": "Restrooms", "foyer": "Foyer"}[kind]}

rooms = []
# ---- floor 1 ----
r = lambda fid, *a, **k: rooms.append(room(fid, 1, F1, *a, **k))
r("01", 0, 0, 58, 55, "seminar"); r("02", 0, 55, 58, 102, "office")
r("03", 0, 102, 58, 155, "seminar"); r("04", 0, 155, 58, 206, "seminar")
south = ["05", "06", "44", "43", "42", "41", "40", "39", "38", "37", "36", "35"]
step = (375 - 72) / len(south)
for i, fid in enumerate(south):
    r(fid, 72 + i * step, 174, 72 + (i + 1) * step, 206, "office")
east = ["17", "18", "19", "20", "21", "22", "23", "23a"]
step = 200 / len(east)
for i, fid in enumerate(east):
    r(fid, 375, i * step, 420, (i + 1) * step, "office")
r("WC1", 140, 0, 180, 30, "wc"); r("09a", 180, 0, 205, 30, "office")
north = ["11", "12", "13", "14", "15", "16"]
step = (375 - 205) / len(north)
for i, fid in enumerate(north):
    r(fid, 205 + i * step, 0, 205 + (i + 1) * step, 30, "office")
r("08", 82, 55, 158, 85, "seminar"); r("07", 112, 85, 158, 160, "seminar", "Seminarraum")
r("07a", 158, 50, 265, 160, "atrium")
r("27", 262, 47, 310, 100, "seminar"); r("34", 265, 100, 310, 155, "seminar")
r("24", 310, 45, 370, 75, "office"); r("30", 310, 75, 340, 100, "office"); r("28", 340, 75, 370, 100, "office")
r("29", 310, 100, 340, 125, "office"); r("32", 340, 100, 370, 125, "office"); r("33", 310, 125, 370, 150, "office")
# ---- floor 0 ----
r = lambda fid, *a, **k: rooms.append(room(fid, 0, F0, *a, **k))
r("01", 7, 0, 47, 45, "office"); r("WC0", 47, 0, 102, 45, "wc"); r("06", 102, 0, 157, 45, "office")
r("07", 157, 0, 187, 22, "office"); r("08", 157, 22, 187, 45, "office"); r("09", 197, 0, 227, 45, "office")
for fid, x0, x1 in [("11", 227, 262), ("12", 262, 292), ("13", 292, 322), ("14", 322, 387), ("15", 387, 452)]:
    r(fid, x0, 0, x1, 40, "office")
r("16", 452, 0, 530, 30, "office"); r("18", 482, 30, 530, 45, "office")
r("23", 17, 82, 72, 127, "office"); r("24", 17, 127, 72, 157, "office"); r("25", 22, 157, 97, 258, "office")
r("26", 80, 96, 112, 138, "seminar"); r("22", 112, 96, 147, 138, "seminar"); r("21", 82, 138, 167, 250, "office")
r("20", 167, 75, 467, 255, "hall", "Event hall"); r("19", 467, 123, 537, 253, "foyer")

data = {"building": "V", "name": "Vorstufe", "outer": {"w": W, "d": D},
        "courtyard": {"x": 0.0, "z": 0.25, "w": 16.0, "d": 16.0}, "floors": [0, 1], "floor_height": 4.0,
        "source": "Traced from https://campusplan.aau.at/ (building V / Vorstufe), simplified; capacities are made up.",
        "rooms": rooms}
json.dump(data, open(sys.argv[1], "w", encoding="utf-8"), indent=1)
print(len(rooms), "rooms;", sum(r["bookable"] for r in rooms), "bookable")
