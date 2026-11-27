"""Build web/data/campus.json: building V (from building_v.json) + building N (Nordtrakt), positioned relative to V.

N was traced from a campusplan.aau.at screenshot (floor 1) that shows V and N together. Screen points are rotated
about V's centre by the campus grid angle and scaled with V's known length (60 m), so N sits where it really is
relative to V. N room numbers are generated west -> east (north row, then south row) and are approximate; the
blue (seminar) rooms are placed where the plan shows them.

Usage: uv run --with shapely python tools/campus3d/gen_campus.py   (writes web/map3d/campus.json)
"""
import json
import math
from pathlib import Path

HERE = Path(__file__).parent
V_CENTER = (180, 215)          # V centre in the screenshot (px)
PHI = math.atan2(-32, 290)     # V's top edge direction in the screenshot -> campus grid angle
S = 60.0 / 330                 # metres per px (V is 330 px long and 60 m in our model)


def to_m(px, py):
    dx, dy = px - V_CENTER[0], py - V_CENTER[1]
    x = dx * math.cos(PHI) + dy * math.sin(PHI)
    y = -dx * math.sin(PHI) + dy * math.cos(PHI)
    return round(x * S, 2), round(y * S, 2)


# N segments: screen centre, length and depth in px (floor-1 outline)
SEGMENTS = [((378, 383), 145, 70), ((515, 340), 170, 72), ((680, 345), 160, 70),
            ((840, 318), 180, 100), ((1000, 292), 150, 72), ((1145, 248), 170, 80)]
# Blue (seminar) rooms on the plan, screen rectangles
TEAL = [(410, 340, 445, 370), (495, 312, 530, 342), (615, 316, 655, 346),
        (778, 322, 848, 368), (848, 322, 920, 368), (930, 265, 965, 295), (1192, 258, 1228, 290)]
CONNECTOR = ((322, 315), 14, 70)   # glass corridor V -> N (screen centre, width, length)


def teal_spans_m():
    out = []
    for x0, y0, x1, y1 in TEAL:
        (ax, az), (bx, bz) = to_m(x0, y0), to_m(x1, y1)
        out.append((min(ax, bx), max(ax, bx), (az + bz) / 2))
    return out


def build_n():
    blocks, rooms = [], []
    teal = teal_spans_m()
    counters = {0: 1, 1: 1, 2: 1}
    for (cx, cy), length, depth in SEGMENTS:
        x, z = to_m(cx, cy)
        w, d = length * S, depth * S
        blocks.append({"x": x, "z": z, "w": round(w, 2), "d": round(d, 2)})
        north_d, corridor_d = d * 0.38, d * 0.2
        south_d = d - north_d - corridor_d
        rows = [("north", z - d / 2 + north_d / 2, north_d), ("south", z + d / 2 - south_d / 2, south_d)]
        for floor in (0, 1, 2):
            for row, rz, rd in rows:
                x0, x_end = x - w / 2, x + w / 2
                while x_end - x0 > 1.5:
                    span = next((t for t in teal if t[0] < x0 + 2.5 < t[1] and abs(t[2] - rz) < rd), None)
                    if span:
                        x1, kind = min(span[1], x_end), "seminar"
                    else:
                        nxt = min([t[0] for t in teal if t[0] > x0 + 0.5 and abs(t[2] - rz) < rd] + [x_end])
                        x1, kind = min(x0 + 5.0, nxt, x_end), "office"
                        if x_end - x1 < 2.0 and not any(t[0] > x0 for t in teal if abs(t[2] - rz) < rd and t[0] < x_end):
                            x1 = x_end
                    rw = x1 - x0
                    area = rw * rd
                    rooms.append({
                        "id": f"N.{floor}.{counters[floor]:02d}", "floor": floor,
                        "x": round((x0 + x1) / 2, 2), "z": round(rz, 2), "w": round(rw, 2), "d": round(rd, 2),
                        "capacity": min(60, max(16, int(area / 2.0))) if kind == "seminar" else (2 if area < 25 else 4),
                        "type": kind, "bookable": kind == "seminar",
                        "name": "Seminar room" if kind == "seminar" else "Office"})
                    counters[floor] += 1
                    x0 = x1
    # stair / restroom towers sticking out on the north side (reference-screenshot rects)
    for x0, y0, x1, y1 in [(430, 286, 490, 305), (748, 244, 800, 268), (1058, 184, 1108, 205)]:
        (cx, cz) = to_m((x0 + x1) / 2, (y0 + y1) / 2)
        blocks.append({"x": cx, "z": cz, "w": round((x1 - x0) * S, 2), "d": round((y1 - y0) * S, 2)})
    (cx, cy), cw, cl = CONNECTOR
    x, z = to_m(cx, cy)
    return {"id": "N", "name": "Nordtrakt", "floors": [0, 1, 2], "floor_height": 3.8,
            "blocks": blocks, "rooms": rooms,
            "connectors": [{"x": x, "z": z, "w": round(cw * S, 2), "d": round(cl * S, 2), "floors": [0, 1]}],
            "source": "Traced from campusplan.aau.at (Nordtrakt, floor 1); room numbers approximate."}


# --- Building Z (Zentralgebäude). Traced from a second screenshot at the same zoom; N's label sits at (494,165)
# there and at (781,326) in the reference screenshot, so Z points are shifted by that offset first.
Z_SHIFT = (781 - 494, 326 - 165)
Z_BLOCKS = [(350, 300, 660, 485), (660, 315, 840, 485), (200, 380, 365, 535), (370, 485, 690, 685)]  # x0,y0,x1,y1
Z_ROOMS = [  # (x0, y0, x1, y1, type, name) on floor 1; repeated on floors 0 and 2 except where noted
    (352, 320, 415, 415, "seminar", "Lecture hall"), (415, 335, 462, 410, "seminar", "Lecture hall"),
    (582, 310, 650, 390, "seminar", "Lecture hall"), (665, 342, 730, 380, "seminar", "Seminar room"),
    (245, 452, 300, 530, "seminar", "Seminar room"), (300, 450, 355, 525, "seminar", "Seminar room"),
    (360, 415, 655, 482, "foyer", "Foyer"),
]
Z_OFFICE_ROWS = [(730, 318, 835, 345), (680, 440, 815, 478), (205, 392, 245, 530), (245, 388, 330, 420)]
Z_CONNECTORS = [(322, 165, 345, 300), (478, 200, 500, 300), (630, 150, 655, 300)]   # corridors up to N


def z_rect(x0, y0, x1, y1):
    """Screen rect (second screenshot) -> centre x, z and size w, d in metres (campus frame)."""
    (ax, az) = to_m(x0 + Z_SHIFT[0], y0 + Z_SHIFT[1])
    (bx, bz) = to_m(x1 + Z_SHIFT[0], y1 + Z_SHIFT[1])
    (cx, cz) = to_m((x0 + x1) / 2 + Z_SHIFT[0], (y0 + y1) / 2 + Z_SHIFT[1])
    return cx, cz, round(abs(x1 - x0) * S, 2), round(abs(y1 - y0) * S, 2)


def snap_connectors(connectors, north_blocks, south_blocks, overlap=1.0):
    """Stretch each north-south corridor so it runs from inside the northern building to inside the southern one."""
    def spans(blocks, x):
        return [b for b in blocks if b["x"] - b["w"] / 2 <= x <= b["x"] + b["w"] / 2]
    for c in connectors:
        z0, z1 = c["z"] - c["d"] / 2, c["z"] + c["d"] / 2
        north = [b["z"] + b["d"] / 2 for b in spans(north_blocks, c["x"])]
        south = [b["z"] - b["d"] / 2 for b in spans(south_blocks, c["x"]) if b["z"] - b["d"] / 2 > z0]
        if north:
            z0 = min(z0, max(north) - overlap)
        if south:
            z1 = min(south) + overlap
        c["z"], c["d"] = round((z0 + z1) / 2, 2), round(z1 - z0, 2)


def build_z():
    blocks = [dict(zip("xzwd", z_rect(*b))) for b in Z_BLOCKS]
    blocks[3]["open"] = True   # the Aula is one tall hall: no upper floor slabs
    rooms, n = [], {0: 1, 1: 1, 2: 1}

    def add(floor, x, z, w, d, kind, name):
        area = w * d
        cap = {"seminar": min(250, max(20, int(area / 1.6))), "hall": 300}.get(kind, 2 if area < 25 else 4)
        rooms.append({"id": f"Z.{floor}.{n[floor]:02d}", "floor": floor, "x": x, "z": z, "w": w, "d": d,
                      "capacity": cap if kind in ("seminar", "hall", "office") else 0, "type": kind,
                      "bookable": kind in ("seminar", "hall"), "name": name})
        n[floor] += 1

    for floor in (0, 1, 2):
        for x0, y0, x1, y1, kind, name in Z_ROOMS:
            add(floor, *z_rect(x0, y0, x1, y1), kind, name)
        for x0, y0, x1, y1 in Z_OFFICE_ROWS:   # split each row into ~5 m offices along its long side
            cx, cz, w, d = z_rect(x0, y0, x1, y1)
            along_x = w >= d
            length = w if along_x else d
            k = max(1, round(length / 5))
            for i in range(k):
                off = -length / 2 + (i + 0.5) * length / k
                add(floor, round(cx + off, 2) if along_x else cx, cz if along_x else round(cz + off, 2),
                    round(length / k, 2) if along_x else w, d if along_x else round(length / k, 2), "office", "Office")
    cx, cz, w, d = z_rect(525, 485, 690, 685)   # Aula floor area east of building L (L stands inside the hall)
    add(0, cx, cz, w, d, "hall", "Aula")     # the big glass hall south of Z, ground floor
    connectors = [dict(zip("xzwd", z_rect(*c)), floors=[0, 1]) for c in Z_CONNECTORS]
    snap_connectors(connectors, build_n()["blocks"], blocks)
    return {"id": "Z", "name": "Zentralgebäude", "floors": [0, 1, 2], "floor_height": 4.0,
            "blocks": blocks, "rooms": rooms, "connectors": connectors,
            "source": "Traced from campusplan.aau.at (Zentralgebäude, floor 1), simplified; floor 1 layout repeated "
                      "on floors 0 and 2; room numbers approximate."}


# --- Buildings L and S, traced from the same screenshot as Z (same Z_SHIFT). Each wing segment is a screen rect;
# rooms are generated along a central corridor, with the blue (seminar / lecture) rects placed where the plan shows them.
def build_wing(bid, name, segments, teal, floors, floor_height, extra=(), source="", conv=None):
    conv = conv or z_rect
    blocks, rooms, n = [], [], {f: 1 for f in floors}
    teal_m = [conv(*t) for t in teal]                        # (cx, cz, w, d)

    def add(floor, x, z, w, d, kind, rname):
        area = w * d
        cap = {"seminar": min(400, max(16, int(area / 1.6)))}.get(kind, 2 if area < 25 else 4)
        rooms.append({"id": f"{bid}.{floor}.{n[floor]:02d}", "floor": floor, "x": round(x, 2), "z": round(z, 2),
                      "w": round(w, 2), "d": round(d, 2), "capacity": cap, "type": kind,
                      "bookable": kind == "seminar", "name": rname})
        n[floor] += 1

    for rect in segments:
        cx, cz, w, d = conv(*rect)
        blocks.append({"x": cx, "z": cz, "w": w, "d": d})
        north_d, corr = d * 0.38, d * 0.2
        south_d = d - north_d - corr
        for floor in floors:
            for rz, rd in ((cz - d / 2 + north_d / 2, north_d), (cz + d / 2 - south_d / 2, south_d)):
                x0, x_end = cx - w / 2, cx + w / 2
                spans = sorted((t[0] - t[2] / 2, t[0] + t[2] / 2) for t in teal_m
                               if abs(t[1] - rz) < rd and t[0] + t[2] / 2 > x0 and t[0] - t[2] / 2 < x_end)
                while x_end - x0 > 1.5:
                    span = next((s for s in spans if s[0] <= x0 + 1.0 < s[1]), None)
                    if span:
                        x1 = min(span[1], x_end)
                        add(floor, (x0 + x1) / 2, rz, x1 - x0, rd, "seminar", "Lecture hall" if (x1 - x0) * rd > 60 else "Seminar room")
                    else:
                        nxt = min([s[0] for s in spans if s[0] > x0 + 0.5] + [x_end])
                        x1 = min(x0 + 5.0, nxt)
                        if x_end - x1 < 2.0 and nxt == x_end:
                            x1 = x_end
                        add(floor, (x0 + x1) / 2, rz, x1 - x0, rd, "office", "Office")
                    x0 = x1
    for rect, kind, rname, rfloors in extra:
        cx, cz, w, d = conv(*rect)
        blocks.append({"x": cx, "z": cz, "w": w, "d": d})
        for f in rfloors:
            add(f, cx, cz, w, d, kind, rname)
    return {"id": bid, "name": name, "floors": list(floors), "floor_height": floor_height,
            "blocks": blocks, "rooms": rooms, "source": source}


def build_l():
    # small block standing inside the Aula hall, 4 storeys
    return build_wing("L", "Hörsaaltrakt L", [(420, 470, 520, 590)], [(455, 555, 500, 588)], (0, 1, 2, 3), 3.8,
                      source="Traced from campusplan.aau.at (building L, floor 1); room numbers approximate.")


def zm(px, py):
    """Point in the Z screenshot -> campus metres."""
    return to_m(px + Z_SHIFT[0], py + Z_SHIFT[1])


def build_s():
    """South wing: straight west part, fan-shaped main lecture hall, and an east part that curves to the north-east."""
    floors = (0, 1, 2)
    s = build_wing("S", "Südtrakt", [(75, 672, 390, 768)], [(172, 688, 200, 720), (258, 690, 340, 765)], floors, 3.8,
                   source="Traced from campusplan.aau.at (Südtrakt, floor 1); room numbers approximate.")
    n = {f: 1 + sum(r["floor"] == f for r in s["rooms"]) for f in floors}

    def add(floor, poly, kind, name, angle, w, d):
        cx = sum(p[0] for p in poly) / len(poly)
        cz = sum(p[1] for p in poly) / len(poly)
        area = w * d
        s["rooms"].append({"id": f"S.{floor}.{n[floor]:02d}", "floor": floor, "x": round(cx, 2), "z": round(cz, 2),
                           "w": round(w, 2), "d": round(d, 2), "angle": round(angle, 4),
                           "poly": [[round(x, 2), round(z, 2)] for x, z in poly],
                           "capacity": min(400, max(16, int(area / 1.6))) if kind == "seminar" else (2 if area < 25 else 4),
                           "type": kind, "bookable": kind == "seminar", "name": name})
        n[floor] += 1

    # fan-shaped main lecture hall (outline from the plan), 2 storeys tall, one room
    fan = [zm(425, 690), zm(527, 688), zm(548, 800)] + \
          [zm(476 + 72 * math.cos(a), 800 + 16 * math.sin(a)) for a in [i * math.pi / 8 for i in range(1, 8)]] + \
          [zm(402, 800)]
    s["blocks"].append({"poly": [list(p) for p in fan], "floors": [0, 1], "open": True})
    xs, zs = [p[0] for p in fan], [p[1] for p in fan]
    add(0, fan, "seminar", "Main lecture hall", 0.0, max(xs) - min(xs), max(zs) - min(zs))

    # curved east part: quadratic Bezier centre line, rooms on both sides of a central corridor
    p0, p1, p2 = [zm(*p) for p in ((545, 700), (775, 682.5), (1005, 612))]
    half = 48 * S
    steps = 18
    centre, normal = [], []
    for i in range(steps + 1):
        t = i / steps
        cx = (1 - t) ** 2 * p0[0] + 2 * (1 - t) * t * p1[0] + t * t * p2[0]
        cz = (1 - t) ** 2 * p0[1] + 2 * (1 - t) * t * p1[1] + t * t * p2[1]
        tx = 2 * (1 - t) * (p1[0] - p0[0]) + 2 * t * (p2[0] - p1[0])
        tz = 2 * (1 - t) * (p1[1] - p0[1]) + 2 * t * (p2[1] - p1[1])
        ln = math.hypot(tx, tz)
        centre.append((cx, cz))
        normal.append((-tz / ln, tx / ln))        # points to the south side
    off = lambda i, o: (centre[i][0] + normal[i][0] * o, centre[i][1] + normal[i][1] * o)
    s["blocks"].append({"poly": [list(off(i, -half)) for i in range(steps + 1)] +
                                [list(off(i, half)) for i in range(steps, -1, -1)]})
    teal = [z_rect(*t) for t in [(580, 655, 685, 740), (735, 637, 785, 670), (748, 682, 797, 715)]]
    in_teal = lambda p: next((k for k, (tx, tz, tw, td) in enumerate(teal)
                              if abs(p[0] - tx) < tw / 2 and abs(p[1] - tz) < td / 2), None)
    bands = {"north": (-half, -half + 2 * half * 0.38), "south": (half - 2 * half * 0.42, half)}
    for floor in floors:
        cells = {}   # (band, i) -> teal index or None
        for band, (o0, o1) in bands.items():
            for i in range(steps):
                mid = off(i, (o0 + o1) / 2)
                mid = ((mid[0] + off(i + 1, (o0 + o1) / 2)[0]) / 2, (mid[1] + off(i + 1, (o0 + o1) / 2)[1]) / 2)
                cells[band, i] = in_teal(mid)
        done = set()
        for band, (o0, o1) in bands.items():
            i = 0
            while i < steps:
                k = cells[band, i]
                j = i + 1
                while j < steps and k is not None and cells[band, j] == k:
                    j += 1
                if (band, i) in done:
                    i = j
                    continue
                lo, hi = o0, o1
                if k is not None and all(cells["north", m] == k and cells["south", m] == k for m in range(i, j)):
                    lo, hi = -half, half                        # one hall spanning the whole depth
                    done.update(("south", m) for m in range(i, j))
                poly = [off(i, lo), off(j, lo), off(j, hi), off(i, hi)]
                (ax, az), (bx, bz) = centre[i], centre[j]
                length, angle = math.hypot(bx - ax, bz - az), math.atan2(bz - az, bx - ax)
                kind = "seminar" if k is not None else "office"
                name = ("Lecture hall" if (hi - lo) * length > 60 else "Seminar room") if k is not None else "Office"
                add(floor, poly, kind, name, angle, length, hi - lo)
                i = j
    return s


def build_v():
    v = json.loads((HERE / "building_v_rooms.json").read_text(encoding="utf-8"))
    block = {"x": 0.0, "z": 0.0, "w": v["outer"]["w"], "d": v["outer"]["d"], "courtyard": v["courtyard"]}
    return {"id": "V", "name": v["name"], "floors": v["floors"], "floor_height": v["floor_height"],
            # low one-storey annex on the north-west side and the stem linking it (from the floor-0 plan)
            "blocks": [block, {"x": -16.7, "z": -19.8, "w": 15.0, "d": 3.9, "floors": [0]},
                       {"x": -20.0, "z": -15.6, "w": 3.4, "d": 4.5, "floors": [0]}],
            "rooms": v["rooms"], "source": v["source"]}


if __name__ == "__main__":
    campus = {"campus": "AAU Klagenfurt", "units": "metres; x east, z south; origin = centre of building V",
              "buildings": [build_v(), build_n(), build_z(), build_l(), build_s()]}
    from resolve_overlaps import resolve_blocks, resolve_rooms   # needs shapely (uv run --with shapely)
    resolve_blocks(campus["buildings"])
    print("dropped rooms:", resolve_rooms(campus["buildings"]))
    (HERE.parent.parent / "web" / "map3d" / "campus.json").write_text(json.dumps(campus, indent=1), encoding="utf-8")
    for b in campus["buildings"]:
        print(b["id"], len(b["rooms"]), "rooms,", sum(r["bookable"] for r in b["rooms"]), "bookable")
