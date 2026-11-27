// 2D floor plan of building V, used until claude-2's web/js/building3d.js exists.
// It offers the same module API as the 3D model (docs/PLAN.md, "3D module API"),
// so app.js does not care which one it gets.

const OUTER = { w: 60, d: 40 };
const YARD = { w: 30, d: 16 };
const GAP = 0.9;

// Until web/data/building_v.json exists, place the API's rooms in a ring around the courtyard,
// clockwise from the top-left corner.
export function layoutBuilding(rooms) {
  const n = rooms.length;
  const side = Math.max(1, Math.round(n * 0.15));
  const top = Math.ceil((n - 2 * side) / 2);
  const bottom = n - 2 * side - top;
  const ringZ = (OUTER.d / 2 + YARD.d / 2) / 2;
  const ringX = (OUTER.w / 2 + YARD.w / 2) / 2;
  const depth = (OUTER.d - YARD.d) / 2 - GAP;
  const width = (OUTER.w - YARD.w) / 2 - GAP;
  const cells = [];
  const row = (count, z, reverse) => {
    const w = OUTER.w / count;
    for (let i = 0; i < count; i++) {
      const k = reverse ? count - 1 - i : i;
      cells.push({ x: -OUTER.w / 2 + w * (k + 0.5), z, w: w - GAP, d: depth });
    }
  };
  const column = (count, x, reverse) => {
    const d = YARD.d / count;
    for (let i = 0; i < count; i++) {
      const k = reverse ? count - 1 - i : i;
      cells.push({ x, z: -YARD.d / 2 + d * (k + 0.5), w: width, d: d - GAP });
    }
  };
  row(top, -ringZ, false);
  column(side, ringX, false);
  row(bottom, ringZ, true);
  column(side, -ringX, true);
  return {
    building: "V", outer: OUTER, courtyard: YARD, floor_height: 4,
    rooms: rooms.map((r, i) => ({ id: r.id, floor: r.floor, name: r.name, capacity: r.capacity, ...cells[i] })),
  };
}

const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => `&#${c.charCodeAt(0)};`);

export function createPlan(el, building) {
  const rooms = building.rooms.filter((r) => r.floor === 1 && r.w && r.d);
  const outer = building.outer || OUTER;
  const yard = building.courtyard || YARD;
  const statuses = {};
  let focused = null;
  let onClick = () => {};
  let queued = false;

  function roomSvg(r) {
    const s = statuses[r.id] || {};
    const cls = ["room", s.status || "free", s.noise_class === "loud" ? "loud" : "", r.id === focused ? "selected" : ""];
    const x = r.x - r.w / 2;
    const y = r.z - r.d / 2;
    const maxChars = Math.floor(r.w / 1.05);
    const name = r.name && r.name.length > maxChars ? `${r.name.slice(0, maxChars - 1)}…` : r.name;
    const live = s.live ? `<circle class="live-dot" cx="${x + r.w - 1.6}" cy="${y + 1.6}" r=".8"/>` : "";
    return `<g class="${cls.join(" ")}" data-room="${esc(r.id)}" tabindex="0" role="button" aria-label="${esc(r.id)} ${esc(r.name)}">
      <rect class="base" x="${x}" y="${y + 1.3}" width="${r.w}" height="${r.d}" rx="1.2"/>
      <rect class="top" x="${x}" y="${y}" width="${r.w}" height="${r.d}" rx="1.2"/>
      <text class="rid" x="${r.x}" y="${r.z - 1}">${esc(r.id.replace(/^V\./, ""))}</text>
      <text class="rname" x="${r.x}" y="${r.z + 2}">${esc(name)}</text>${live}</g>`;
  }

  function render() {
    queued = false;
    const pad = 3;
    el.innerHTML = `<span class="building-note">Floor plan preview · the 3D model is on its way</span>
      <div class="plan ${focused ? "focused" : ""}">
        <svg viewBox="${-outer.w / 2 - pad} ${-outer.d / 2 - pad} ${outer.w + pad * 2} ${outer.d + pad * 2 + 1.5}" role="group" aria-label="Floor 1 of building V">
          <rect class="slab" x="${-outer.w / 2 - 1}" y="${-outer.d / 2 - 1}" width="${outer.w + 2}" height="${outer.d + 3}" rx="2.5"/>
          <rect class="yard" x="${-yard.w / 2}" y="${-yard.d / 2}" width="${yard.w}" height="${yard.d}" rx="1.5"/>
          <text class="yard-label" x="0" y="0.8">COURTYARD</text>
          ${rooms.map(roomSvg).join("")}
        </svg>
      </div>`;
  }

  function schedule() {
    if (!queued) {
      queued = true;
      queueMicrotask(render);
    }
  }

  el.addEventListener("click", (e) => {
    const g = e.target.closest("[data-room]");
    if (g) onClick(g.dataset.room);
  });
  el.addEventListener("keydown", (e) => {
    const g = e.target.closest("[data-room]");
    if (g && (e.key === "Enter" || e.key === " ")) {
      e.preventDefault();
      onClick(g.dataset.room);
    }
  });
  render();

  return {
    setStatus(id, s) {
      const next = { status: s.status, noise_class: s.noise_class, live: s.live };
      if (JSON.stringify(statuses[id]) === JSON.stringify(next)) return;
      statuses[id] = next;
      schedule();
    },
    focusRoom(id) {
      if (!rooms.some((r) => r.id === id)) return false;
      focused = id;
      schedule();
      return true;
    },
    showAll() { focused = null; schedule(); },
    setFloor() {},
    onRoomClick(cb) { onClick = cb; },
  };
}
