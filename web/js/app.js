// Room V dashboard: search, building view, room panel and room list.
// All data comes through api.js (real backend or mock). The building view is claude-2's
// building3d.js when it exists, otherwise a 2D placeholder with the same module API.
import * as api from "./api.js";

const POLL_MS = 5000;
const LIVE_ROOM = "V.1.07a";
const STATUS_LABEL = { free: "Free", partial: "Partly booked", full: "Fully booked" };
const PURPOSE_LABEL = {
  quiet_study: "Quiet study", group_study: "Group study", gaming: "Gaming", meeting: "Meeting",
  board_games: "Board games", event: "Event", custom: "Custom",
};

const state = { building: null, rooms: [], selected: null, detail: null, floor: null, view: null, error: null };
const $ = (id) => document.getElementById(id);

function esc(value) {
  return String(value ?? "").replace(/[&<>"']/g, (c) => `&#${c.charCodeAt(0)};`);
}

function time(iso) {
  return new Date(iso).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", hourCycle: "h23" });
}

function purpose(b) {
  return b.purpose === "custom" && b.custom_purpose ? b.custom_purpose : PURPOSE_LABEL[b.purpose] ?? b.purpose;
}

function roomById(id) {
  return state.rooms.find((r) => r.id === id);
}

function liveBadge(room) {
  if (room.live) return `<span class="live-badge" title="Measured by the PSOC Edge E84 board">LIVE</span>`;
  if (room.id === LIVE_ROOM) return `<span class="live-badge offline" title="No board data in the last 20 s">SENSOR OFFLINE</span>`;
  return "";
}

// ---------- 2D placeholder with the same API as building3d.js (PLAN.md) ----------

function createPlaceholder(el, building) {
  const floors = [...new Set(building.rooms.map((r) => r.floor))].sort();
  const statuses = {};
  let floor = null;
  let focused = null;
  let onClick = () => {};
  let queued = false;

  function plan(f) {
    const { w, d } = building.outer;
    const c = building.courtyard;
    const rooms = building.rooms.filter((r) => r.floor === f).map((r) => {
      const s = statuses[r.id] ?? {};
      const cls = ["room", s.status ?? "free", s.noise_class === "loud" ? "loud" : "", r.id === focused ? "selected" : ""];
      const live = s.live
        ? `<rect class="live-tag" x="${r.x + r.w / 2 - 7}" y="${r.z - r.d / 2 + 0.8}" width="6.2" height="3" rx="1"/>
           <text class="live-text" x="${r.x + r.w / 2 - 3.9}" y="${r.z - r.d / 2 + 2.4}">LIVE</text>`
        : "";
      return `<g data-room="${esc(r.id)}">
        <rect class="${cls.join(" ")}" x="${r.x - r.w / 2}" y="${r.z - r.d / 2}" width="${r.w}" height="${r.d}" rx="0.8">
          <title>${esc(r.id)} · ${esc(r.name)}</title></rect>
        <text class="room-label" x="${r.x}" y="${r.z}">${esc(r.id.replace(/^V\./, ""))}</text>${live}</g>`;
    }).join("");
    return `<div class="plan"><div class="plan-title">Floor ${f}</div>
      <svg viewBox="${-w / 2 - 1} ${-d / 2 - 1} ${w + 2} ${d + 2}" role="img" aria-label="Floor ${f} plan">
        <rect class="outline" x="${-w / 2}" y="${-d / 2}" width="${w}" height="${d}" rx="1.5"/>
        <rect class="courtyard" x="${-c.w / 2}" y="${-c.d / 2}" width="${c.w}" height="${c.d}" rx="1"/>
        ${rooms}</svg></div>`;
  }

  function render() {
    queued = false;
    const shown = floor === null ? floors : [floor];
    el.innerHTML = `<span class="placeholder-note">2D placeholder · the 3D model (claude-2) replaces this</span>
      <div class="plans ${floor === null ? "all" : ""}">${shown.map(plan).join("")}</div>`;
    el.classList.toggle("focused", focused !== null);
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
  render();

  return {
    setStatus(id, s) { statuses[id] = s; schedule(); },
    focusRoom(id) {
      if (!building.rooms.some((r) => r.id === id)) return false;
      focused = id;
      schedule();
      return true;
    },
    showAll() { focused = null; schedule(); },
    setFloor(n) { floor = n; schedule(); },
    onRoomClick(cb) { onClick = cb; },
  };
}

async function createView(el, building) {
  try {
    const { createBuilding } = await import("./building3d.js");
    return createBuilding(el, building);
  } catch {
    return createPlaceholder(el, building);
  }
}

// ---------- Rendering ----------

function renderSource(source, buildingMock) {
  const badge = $("source-badge");
  badge.className = `source-badge ${source}`;
  badge.textContent = source === "api" ? "Live API" : "Mock data";
  badge.title = source === "api"
    ? `Room data from the backend${buildingMock ? "; building layout is mock data" : ""}`
    : "The backend is not reachable, so the UI shows made-up demo data";
}

function renderStats() {
  const count = (s) => state.rooms.filter((r) => r.status === s).length;
  const live = roomById(LIVE_ROOM);
  const liveValue = live
    ? `${Math.round(live.noise_db)} <small>dB · ${esc(live.noise_class)}</small>`
    : "–";
  $("stats").innerHTML = [
    ["Free rooms", `${count("free")} <small>of ${state.rooms.length}</small>`],
    ["Partly booked", count("partial")],
    ["Fully booked", count("full")],
    [`${LIVE_ROOM} noise ${live ? liveBadge(live) : ""}`, liveValue],
  ].map(([label, value]) => `<div class="card stat"><div class="stat-label">${label}</div>
    <div class="stat-value">${value}</div></div>`).join("");
}

function renderList() {
  const rooms = state.rooms.filter((r) => state.floor === null || r.floor === state.floor);
  $("room-list").innerHTML = rooms.map((r) => `
    <button type="button" class="room-row ${r.id === state.selected ? "selected" : ""}" data-room="${esc(r.id)}">
      <span class="room-id">${esc(r.id)}</span>
      <span class="room-name">${esc(r.name)} ${liveBadge(r)}</span>
      <span><span class="pill ${esc(r.status)}">${STATUS_LABEL[r.status] ?? esc(r.status)}</span></span>
      <span class="room-noise">${Math.round(r.noise_db)} dB · ${esc(r.noise_class)}</span>
      <span class="room-people">${r.people}/${r.capacity} people</span>
    </button>`).join("") || `<p class="muted">No rooms on this floor.</p>`;
}

function renderPanel() {
  const panel = $("room-panel");
  const room = state.detail?.id === state.selected ? state.detail : roomById(state.selected);
  if (!room) {
    panel.innerHTML = `<div class="panel-empty">
      <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M3 21V5a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v16M16 9h3a2 2 0 0 1 2 2v10M3 21h18M8 7h3M8 11h3M8 15h3"/></svg>
      <p><strong>No room selected</strong></p>
      <p>Search for a room or click one in the building to see its noise, people and bookings.</p></div>`;
    return;
  }
  const noisePct = Math.min(100, Math.max(4, ((room.noise_db - 30) / 60) * 100));
  const peoplePct = Math.min(100, (room.people / room.capacity) * 100);
  const now = Date.now();
  const today = (room.bookings_today ?? []).slice().sort((a, b) => Date.parse(a.start) - Date.parse(b.start));
  const bookings = today.length
    ? `<ul class="bookings">${today.map((b) => {
        const active = Date.parse(b.start) <= now && now < Date.parse(b.end);
        const seats = b.mode === "full" ? "Whole room" : `${b.seats} seats`;
        return `<li class="${active ? "now" : ""}"><span class="time">${time(b.start)}–${time(b.end)}</span>
          <span>${esc(purpose(b))} · ${seats}</span></li>`;
      }).join("")}</ul>`
    : `<p class="muted">${room.bookings_today ? "No bookings today." : "Loading bookings…"}</p>`;

  panel.innerHTML = `
    <div class="panel-head">
      <div>
        <div class="panel-title">${esc(room.id)}</div>
        <div class="panel-sub">${esc(room.name)} · Floor ${room.floor} · ${room.capacity} seats</div>
      </div>
    </div>
    <div class="panel-badges"><span class="pill ${esc(room.status)}">${STATUS_LABEL[room.status] ?? esc(room.status)}</span>${liveBadge(room)}</div>
    <section class="metrics">
      <div>
        <div class="metric"><span class="muted">Noise right now</span>
          <span class="metric-class ${esc(room.noise_class)}">${esc(room.noise_class)}</span></div>
        <div class="metric-value">${room.noise_db.toFixed(1)} dB</div>
        <div class="meter"><span class="${esc(room.noise_class)}" style="width:${noisePct}%"></span></div>
        <div class="scale"><span>quiet &lt; 40</span><span>moderate</span><span>loud &gt; 60</span></div>
      </div>
      <div>
        <div class="metric"><span class="muted">People (estimate)</span>
          <span class="muted">${room.live ? "from the board" : "simulated"}</span></div>
        <div class="metric-value">${room.people} <small class="muted">/ ${room.capacity}</small></div>
        <div class="meter"><span class="people" style="width:${peoplePct}%"></span></div>
      </div>
    </section>
    <section>
      <h3>Today's bookings</h3>
      ${bookings}
    </section>
    <button class="btn" type="button" disabled title="Comes in the next step">Book this room</button>`;
}

function renderAll() {
  renderStats();
  renderList();
  renderPanel();
  for (const r of state.rooms) state.view.setStatus(r.id, { status: r.status, noise_class: r.noise_class, live: r.live });
  $("updated").textContent = state.error
    ? `Update failed: ${state.error}`
    : `Updated ${new Date().toLocaleTimeString([], { hourCycle: "h23" })} · every ${POLL_MS / 1000} s`;
}

// ---------- Actions ----------

async function refresh() {
  try {
    state.rooms = await api.getRooms();
    if (state.selected) state.detail = await api.getRoom(state.selected);
    state.error = null;
  } catch (err) {
    state.error = err.message;
  }
  renderAll();
}

function setFloor(n) {
  state.floor = n;
  for (const b of $("floor-filter").querySelectorAll("button")) {
    b.classList.toggle("active", b.dataset.floor === (n === null ? "" : String(n)));
  }
  state.view.setFloor(n);
  renderList();
}

async function selectRoom(id) {
  const room = state.building.rooms.find((r) => r.id === id);
  if (!room) return;
  state.selected = id;
  state.detail = null;
  if (state.floor !== null && state.floor !== room.floor) setFloor(room.floor);
  state.view.focusRoom(id);
  $("search-input").value = id;
  $("search-msg").textContent = "";
  renderList();
  renderPanel();
  try {
    const detail = await api.getRoom(id);
    if (state.selected === id) state.detail = detail;
  } catch (err) {
    state.error = err.message;
  }
  if (state.selected === id) renderPanel();
}

function clearSelection() {
  state.selected = null;
  state.detail = null;
  state.view.showAll();
  $("search-input").value = "";
  $("search-msg").textContent = "";
  renderList();
  renderPanel();
}

function findRoom(query) {
  const norm = (s) => s.toLowerCase().replace(/\s+/g, "");
  const q = norm(query);
  const rooms = state.building.rooms;
  return rooms.find((r) => norm(r.id) === q)
    || rooms.find((r) => norm(r.id) === `v.${q}`)
    || rooms.find((r) => norm(r.id).includes(q))
    || rooms.find((r) => norm(r.name).includes(q));
}

function wireEvents() {
  $("search-form").addEventListener("submit", (e) => {
    e.preventDefault();
    const query = $("search-input").value.trim();
    if (!query) return clearSelection();
    const room = findRoom(query);
    if (room) selectRoom(room.id);
    else $("search-msg").textContent = `No room matches “${query}”.`;
  });
  $("search-input").addEventListener("keydown", (e) => {
    if (e.key === "Escape") clearSelection();
  });
  document.addEventListener("keydown", (e) => {
    if (e.key === "/" && document.activeElement?.tagName !== "INPUT") {
      e.preventDefault();
      $("search-input").focus();
    }
  });
  $("floor-filter").addEventListener("click", (e) => {
    const b = e.target.closest("button");
    if (b) setFloor(b.dataset.floor === "" ? null : Number(b.dataset.floor));
  });
  $("room-list").addEventListener("click", (e) => {
    const row = e.target.closest("[data-room]");
    if (row) selectRoom(row.dataset.room);
  });
}

async function main() {
  const source = await api.detectSource();
  const { data: building, mock: buildingMock } = await api.getBuilding();
  state.building = building;
  renderSource(source, buildingMock);
  $("room-ids").innerHTML = building.rooms
    .map((r) => `<option value="${esc(r.id)}">${esc(r.name)}, floor ${r.floor}</option>`).join("");
  state.view = await createView($("building"), building);
  state.view.onRoomClick(selectRoom);
  wireEvents();
  await refresh();
  setInterval(refresh, POLL_MS);
}

main();
