// Room V main page: campus map, room picker (picker.js), search, booking sheet and "My bookings".
// Data: api.js (docs/PLAN.md, "Frontend flow"). Map: tom-claude's web/map3d/ when it is merged,
// otherwise the 2D plan in plan2d.js (same module API).
import * as api from "./api.js";
import { createPicker } from "./picker.js";
import { createPlan, layoutBuilding } from "./plan2d.js";

const POLL_MS = 5000;
const SLOT_REFRESH_TICKS = 6;   // the picker reloads every room's slots every 30 s
const DAY_LIMIT = 4;
const HORIZON_DAYS = 14;
const STATUS = { free: "Free", partial: "Shared", full: "Full", ghost: "Ghost booking", closed: "Closed" };
const PURPOSES = [
  { id: "quiet_study", label: "Quiet study", emoji: "📚", noise: "quiet" },
  { id: "group_study", label: "Group study", emoji: "🧠", noise: "moderate" },
  { id: "meeting", label: "Meeting", emoji: "💼", noise: "moderate" },
  { id: "gaming", label: "Gaming", emoji: "🎮", noise: "loud" },
  { id: "board_games", label: "Board games", emoji: "🎲", noise: "loud" },
  { id: "event", label: "Event", emoji: "🎉", noise: "loud" },
  { id: "custom", label: "Other", emoji: "✏️", noise: "moderate" },
];
const PURPOSE = Object.fromEntries(PURPOSES.map((p) => [p.id, p]));

const state = { user: null, rooms: [], mine: [], view: null, picker: null, sheet: null, myRatings: {} };
const $ = (id) => document.getElementById(id);

// ---------- Small helpers ----------

const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => `&#${c.charCodeAt(0)};`);
const pad = (n) => String(n).padStart(2, "0");
const dateKey = (d) => `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`;
const nowKey = () => { const d = new Date(); return `${dateKey(d)}T${pad(d.getHours())}:${pad(d.getMinutes())}`; };
const hm = (iso) => iso.slice(11, 16);
const hoursText = (h) => (h === 0.5 ? "30 min" : `${h} h`);
const purposeText = (b) => (b.purpose === "custom" && b.custom_purpose ? b.custom_purpose : PURPOSE[b.purpose]?.label ?? b.purpose);
const roomName = (id) => state.rooms.find((r) => r.id === id)?.name ?? "";

function dayLabel(key, long = false) {
  const today = new Date();
  const d = new Date(`${key}T12:00`);
  const diff = Math.round((d - new Date(`${dateKey(today)}T12:00`)) / 86400000);
  const text = d.toLocaleDateString("en-GB", { weekday: "short", day: "numeric", month: "short" });
  if (diff === 0) return long ? `Today, ${text}` : "Today";
  if (diff === 1) return long ? `Tomorrow, ${text}` : "Tomorrow";
  return text;
}

function minutesUntil(iso) {
  return Math.max(0, Math.round((new Date(iso) - new Date()) / 60000));
}

function handleAuth(err) {
  if (err.status === 401) {
    location.replace("login.html");
    return true;
  }
  return false;
}

// ---------- Toasts and confetti ----------

function toast(message, { error = false, action } = {}) {
  const el = document.createElement("div");
  el.className = `toast${error ? " error" : ""}`;
  el.innerHTML = `<span>${esc(message)}</span>`;
  if (action) {
    const b = document.createElement("button");
    b.className = "btn";
    b.textContent = action.label;
    b.addEventListener("click", () => { action.run(); dismiss(); });
    el.append(b);
  }
  $("toasts").append(el);
  const dismiss = () => { el.classList.add("out"); setTimeout(() => el.remove(), 260); };
  setTimeout(dismiss, error ? 6000 : 4500);
}

function confetti(fromEl) {
  const box = fromEl.getBoundingClientRect();
  const styles = getComputedStyle(document.documentElement);
  const colors = ["--brand", "--brand-2", "--free", "--shared", "--live"].map((v) => styles.getPropertyValue(v));
  for (let i = 0; i < 28; i++) {
    const c = document.createElement("i");
    c.className = "confetti";
    c.style.left = `${box.left + box.width / 2}px`;
    c.style.top = `${box.top + box.height / 2}px`;
    c.style.background = colors[i % colors.length];
    c.style.setProperty("--dx", `${(Math.random() - 0.5) * 420}px`);
    c.style.setProperty("--dy", `${-80 - Math.random() * 260}px`);
    c.style.setProperty("--r", `${Math.random() * 720 - 360}deg`);
    document.body.append(c);
    setTimeout(() => c.remove(), 1200);
  }
}

// ---------- Live rooms, map and picker ----------

async function refreshRooms() {
  try {
    state.rooms = await api.rooms();
  } catch (err) {
    if (!handleAuth(err)) toast(err.message, { error: true });
    return;
  }
  for (const r of state.rooms) state.view?.setStatus(r.id, r);
  state.picker.setRooms(state.rooms);
}

// The 3D campus map (web/map3d/, tom-claude) when it is there, otherwise the 2D floor plan.
async function createView() {
  const el = $("building");
  try {
    const [{ createBuilding }, campus] = await Promise.all([
      import("../map3d/building3d.js"),
      fetch("map3d/campus.json").then((r) => { if (!r.ok) throw new Error("no campus.json"); return r.json(); }),
    ]);
    state.view = createBuilding(el, campus);
    el.classList.add("is-3d");
  } catch {
    state.view = createPlan(el, (await api.building()) || layoutBuilding(state.rooms));
  }
  // The map also draws rooms that can't be booked (offices, WCs); only bookable ones open the sheet.
  state.view.onRoomClick((id) => { if (state.rooms.some((r) => r.id === id)) openRoom(id); });
  state.view.onRoomHover?.(showMapTip);
  for (const r of state.rooms) state.view.setStatus(r.id, r);
}

// Small tooltip that follows the pointer over a bookable room on the 3D map.
const STATUS_VAR = { free: "--free", partial: "--shared", full: "--full", ghost: "--ghost", closed: "--muted" };
function showMapTip(id, e) {
  const card = $("building").parentElement;
  let tip = card.querySelector(".map-tip");
  if (!tip) {
    tip = document.createElement("div");
    tip.className = "map-tip";
    card.append(tip);
  }
  const r = id && state.rooms.find((x) => x.id === id);
  if (!r || !e) { tip.classList.remove("on"); return; }
  tip.innerHTML = `<b>${esc(r.label || r.id)}</b>${esc(r.label ? `${r.id} · ${r.name}` : r.name)}` +
    `<i style="background:var(${STATUS_VAR[r.status] ?? "--muted"})"></i>${STATUS[r.status] ?? esc(r.status)}` +
    (r.status === "closed" ? "" : ` · ${r.seats_free}/${r.capacity} seats`);
  const box = card.getBoundingClientRect();
  const x = Math.min(e.clientX - box.left + 14, box.width - tip.offsetWidth - 8);
  tip.style.left = `${Math.max(8, x)}px`;
  tip.style.top = `${Math.max(8, e.clientY - box.top - tip.offsetHeight - 12)}px`;
  tip.classList.add("on");
}

// ---------- My bookings ----------

const upcoming = () => state.mine.filter((b) => b.status === "active" && b.end > nowKey())
  .sort((a, b) => a.start.localeCompare(b.start));

function usedHours(day, exceptId) {
  return state.mine.filter((b) => b.status === "active" && b.start.startsWith(day) && b.id !== exceptId)
    .reduce((sum, b) => sum + b.hours, 0);
}

async function refreshMine() {
  try {
    state.mine = await api.myBookings();
  } catch (err) {
    if (!handleAuth(err)) toast(err.message, { error: true });
    return;
  }
  const count = $("mine-count");
  const n = upcoming().length;
  if (count.textContent !== String(n)) {
    count.textContent = n;
    count.classList.remove("bump");
    void count.offsetWidth;
    count.classList.add("bump");
  }
  if ($("mine-drawer").open) renderMine();
}

function bookingCard(b, { actions = true } = {}) {
  const isNow = b.start <= nowKey() && nowKey() < b.end;
  const mode = b.mode === "full" ? "🔒 Private" : "👥 Open to share";
  const statusTag = b.status === "cancelled" ? `<span class="tag">Cancelled</span>`
    : b.status === "released" ? `<span class="tag">Released (nobody came)</span>`
    : isNow ? `<span class="tag now">Now</span>` : "";
  const ghost = b.ghost_release_at
    ? `<div class="ghost-alert">👻 Nobody detected. Released at ${hm(b.ghost_release_at)} (in ${minutesUntil(b.ghost_release_at)} min) unless someone shows up.</div>`
    : "";
  const left = DAY_LIMIT - usedHours(b.start.slice(0, 10));
  const buttons = actions && b.status === "active" && b.end > nowKey() ? `<div class="booking-actions">
      <button class="btn btn-sm" type="button" data-action="add" data-id="${b.id}" ${left < 0.5 ? "disabled title=\"4 h used on this day\"" : ""}>+ Add time</button>
      <button class="btn btn-sm btn-danger" type="button" data-action="cancel" data-id="${b.id}">Cancel</button></div>` : "";
  return `<article class="booking ${isNow && b.status === "active" ? "now" : ""}">
    <div class="booking-top">
      <div><div class="booking-time">${hm(b.start)}–${hm(b.end)}</div>
        <div class="booking-room">${esc(b.room_id)} · ${esc(roomName(b.room_id))}</div></div>
      ${statusTag}
    </div>
    <div class="booking-tags">
      <span class="tag">${PURPOSE[b.purpose]?.emoji ?? ""} ${esc(purposeText(b))}</span>
      <span class="tag">${mode}</span>
      <span class="tag">${b.seats} ${b.seats === 1 ? "person" : "people"}</span>
      <span class="tag">${hoursText(b.hours)}</span>
    </div>
    ${ghost}${buttons}${rateRow(b)}
  </article>`;
}

// Once a booking has started, its room can be rated (the backend checks the same rule).
function rateRow(b) {
  if (b.status !== "active" || b.start > nowKey()) return "";
  const mine = state.myRatings[b.room_id] ?? b.my_rating ?? 0;
  const stars = [1, 2, 3, 4, 5].map((n) => `<button type="button" class="star ${n <= mine ? "on" : ""}" data-action="rate"
    data-room="${esc(b.room_id)}" data-stars="${n}" aria-label="${n} star${n > 1 ? "s" : ""}">★</button>`).join("");
  return `<div class="rate-row"><span class="muted small">${mine ? "Your rating" : "Rate this room"}</span><span class="stars-input">${stars}</span></div>`;
}

async function rateRoom(btn) {
  const room = btn.dataset.room, stars = Number(btn.dataset.stars);
  try {
    await api.rate(room, stars);
    state.myRatings[room] = stars;
    toast(`Thanks! You rated ${room} ${stars}★`);
    renderMine();
    await refreshRooms();
    state.picker.refresh();
  } catch (err) {
    if (!handleAuth(err)) toast(err.message, { error: true });
  }
}

function renderMine() {
  const body = $("mine-body");
  const next = upcoming();
  const days = [...new Set(next.map((b) => b.start.slice(0, 10)))];
  const history = state.mine.filter((b) => !next.includes(b)).slice(0, 12);
  const groups = days.map((day) => {
    const used = usedHours(day);
    return `<section class="day-group">
      <div class="day-head"><b>${esc(dayLabel(day, true))}</b><span class="hours">${used} of ${DAY_LIMIT} h used</span></div>
      <div class="bar"><i style="width:${(used / DAY_LIMIT) * 100}%"></i></div>
      ${next.filter((b) => b.start.startsWith(day)).map((b) => bookingCard(b)).join("")}
    </section>`;
  }).join("");
  body.innerHTML = `
    ${groups || `<div class="drawer-empty"><div class="big">🗓️</div><p><b>No upcoming bookings</b></p><p>Find a room and grab a slot.</p></div>`}
    <button class="btn btn-primary" type="button" data-action="find">Book a room</button>
    ${history.length ? `<details class="history"><summary>Past and cancelled (${history.length})</summary>
      ${history.map((b) => bookingCard(b, { actions: false })).join("")}</details>` : ""}`;
}

function openDrawer() {
  renderMine();
  $("mine-drawer").showModal();
  refreshMine();
}

async function cancelBooking(btn) {
  if (!btn.classList.contains("confirm")) {
    btn.classList.add("confirm");
    btn.textContent = "Sure? Tap again";
    setTimeout(() => { if (btn.isConnected) { btn.classList.remove("confirm"); btn.textContent = "Cancel"; } }, 3500);
    return;
  }
  btn.disabled = true;
  try {
    await api.cancel(Number(btn.dataset.id));
    toast("Booking cancelled");
    await Promise.all([refreshMine(), refreshRooms()]);
    state.picker.refresh();
    if (state.sheet) loadSheetData();
  } catch (err) {
    if (!handleAuth(err)) toast(err.message, { error: true });
    btn.disabled = false;
  }
}

// ---------- Booking sheet ----------

function newSheet(id, opts = {}) {
  return {
    roomId: id, room: null, date: opts.date || dateKey(new Date()), slots: null,
    start: null, hours: opts.hours || 1, wantTime: opts.time || null,
    mode: opts.mode || null, seats: opts.seats || 1, purpose: opts.purpose || null, custom: opts.custom || "",
    error: null, suggestions: [], busy: false,
  };
}

async function openRoom(id, opts) {
  closeSuggestions();
  state.view?.focusRoom(id);
  state.sheet = newSheet(id, opts);
  const dlg = $("room-dialog");
  dlg.innerHTML = `
    <div class="sheet-head" id="sh-head"><div class="skeleton" style="min-height:60px;width:260px"></div></div>
    <div class="sheet-body">
      <div class="sheet-col">
        <div class="block" id="sh-now"></div>
        <div class="block"><div class="block-title"><h3>Pick a day</h3></div><div class="dates" id="sh-dates"></div></div>
        <div class="block">
          <div class="block-title"><h3>Pick a time</h3><span class="muted small">Tap a start, then an end</span></div>
          <div class="slots" id="sh-slots"><div class="skeleton" style="grid-column:1/-1;min-height:200px"></div></div>
          <div class="slot-legend">
            <span><i style="background:var(--free)"></i>Free</span>
            <span><i style="background:var(--shared)"></i>Shared, seats left</span>
            <span><i style="background:var(--full)"></i>Full</span>
            <span><i style="background:var(--brand)"></i>Your booking</span>
          </div>
        </div>
      </div>
      <div class="sheet-col" id="sh-form"></div>
    </div>`;
  if (dlg.hidden) {
    dlg.hidden = false;
    dlg.classList.remove("closing");
    dlg.classList.add("opening");
    setTimeout(() => dlg.classList.remove("opening"), 500);
  }
  // Bring the map into view so the fly-to animation is seen; the panel sits right under it.
  document.querySelector(".map-card").scrollIntoView({ behavior: "smooth", block: "start" });
  renderDates();
  await loadSheetData();
}

async function loadSheetData() {
  const sh = state.sheet;
  if (!sh) return;
  try {
    const [room, avail] = await Promise.all([api.room(sh.roomId), api.availability(sh.roomId, sh.date)]);
    if (state.sheet !== sh) return;
    sh.room = room;
    sh.slots = avail.slots;
  } catch (err) {
    if (!handleAuth(err)) toast(err.message, { error: true });
    return;
  }
  if (sh.wantTime) {
    const i = sh.slots.findIndex((s) => s.start === sh.wantTime);
    sh.wantTime = null;
    if (i >= 0 && selectable(i)) {
      const keep = sh.hours;
      sh.start = i;
      sh.hours = Math.max(0.5, Math.min(keep, maxHours(i)));
    }
  }
  fixSelection();
  renderSheetHead();
  renderSlots();
  if (!$("sh-form")?.contains(document.activeElement) || document.activeElement?.tagName !== "INPUT") renderForm();
}

function closeSheet() {
  const dlg = $("room-dialog");
  if (dlg.hidden || dlg.classList.contains("closing")) return;
  dlg.classList.add("closing");
  setTimeout(() => {
    dlg.classList.remove("closing");
    dlg.hidden = true;
    state.sheet = null;
    state.view?.showAll();
  }, 220);
}

// Slot rules (mirror app/booking.py so the form only offers what the backend accepts).
function busySlot(i) {
  const sh = state.sheet;
  const s = sh.slots[i];
  const t0 = `${sh.date}T${s.start}`;
  const t1 = `${sh.date}T${s.end}`;
  return state.mine.find((b) => b.status === "active" && b.start < t1 && b.end > t0) || null;
}

function selectable(i) {
  const s = state.sheet.slots[i];
  return !!s && (s.status === "free" || s.status === "partial") && !busySlot(i);
}

function dayLeft() {
  return DAY_LIMIT - usedHours(state.sheet.date);
}

function maxHours(i) {
  let n = 0;
  while (selectable(i + n) && (n + 1) / 2 <= DAY_LIMIT) n++;
  return Math.min(n / 2, dayLeft());
}

function range() {
  const sh = state.sheet;
  if (sh.start === null) return [];
  return sh.slots.slice(sh.start, sh.start + sh.hours * 2);
}

function rules() {
  const sh = state.sheet;
  const r = range();
  const cap = sh.room?.capacity ?? 1;
  const canFull = r.length > 0 && r.every((s) => s.status === "free");
  const shareSeats = r.length ? Math.min(...r.map((s) => s.seats_free)) : cap;
  const noises = new Set(r.map((s) => s.noise).filter(Boolean));
  const maxSeats = sh.mode === "full" ? cap : shareSeats;
  return { canFull, maxSeats, noises };
}

function purposeBlocked(p) {
  const sh = state.sheet;
  const { canFull, noises } = rules();
  if (p.id === "event" && (!canFull || sh.mode === "partial")) return "Events need the whole room";
  if (sh.mode === "partial" && p.noise === "quiet" && noises.has("loud")) return "Someone booked a loud activity then";
  if (sh.mode === "partial" && p.noise === "loud" && noises.has("quiet")) return "Someone booked quiet study then";
  return null;
}

function fixSelection() {
  const sh = state.sheet;
  if (sh.start !== null && (!selectable(sh.start) || maxHours(sh.start) < 0.5)) sh.start = null;
  if (sh.start !== null) sh.hours = Math.max(0.5, Math.min(sh.hours, maxHours(sh.start)));
  const { canFull, maxSeats } = rules();
  if (sh.start !== null && (!sh.mode || (sh.mode === "full" && !canFull))) sh.mode = canFull ? "full" : "partial";
  sh.seats = Math.max(1, Math.min(sh.seats, maxSeats || 1));
  if (sh.purpose && purposeBlocked(PURPOSE[sh.purpose])) sh.purpose = null;
}

function renderSheetHead() {
  const r = state.sheet.room;
  const live = r.live ? `<span class="live-badge">LIVE</span>` : "";
  const left = r.left_items > 0
    ? `<span class="left-badge" title="Counted by the board after people left">🎒 ${r.left_items} item${r.left_items === 1 ? "" : "s"} left behind</span>` : "";
  $("sh-head").innerHTML = `
    <div>
      <div class="sheet-title"><h2 id="room-title">${esc(r.label || r.id)}</h2><span class="muted">${esc(r.label ? `${r.id} · ${r.name}` : r.name)}</span></div>
      <div class="sheet-meta">
        <span class="pill ${esc(r.status)}">${STATUS[r.status] ?? esc(r.status)}</span>${live}${left}
        <span class="meta"><svg class="icon"><use href="#i-users"/></svg>${r.people} here · ${r.capacity} max</span>
        <span class="meta"><svg class="icon"><use href="#i-sound"/></svg>${r.noise_db.toFixed(0)} dB · ${esc(r.noise_class)}</span>
      </div>
    </div>
    <button class="icon-btn" type="button" data-action="close" aria-label="Close"><svg class="icon"><use href="#i-close"/></svg></button>`;
  const now = r.bookings_now.length
    ? r.bookings_now.map((b) => `<div class="now-item"><span>${b.shareable ? "👥" : "🔒"} ${b.seats} ${b.seats === 1 ? "person" : "people"} · ${esc(PURPOSE[b.purpose]?.label ?? b.purpose)}</span>
        <span class="muted">${b.shareable ? "open to join · " : "private · "}until ${hm(b.end)}</span></div>`).join("")
    : `<div class="now-item"><span>✨ Nobody has booked it right now</span></div>`;
  const ghost = r.status === "ghost" && r.ghost_release_at
    ? `<div class="ghost-alert" style="margin-top:8px">👻 Booked, but nobody is here. Frees up at ${hm(r.ghost_release_at)} unless someone shows up.</div>` : "";
  $("sh-now").innerHTML = `<div class="block-title"><h3>Right now</h3></div><div class="now-list">${now}</div>${ghost}`;
}

function renderDates() {
  const today = new Date();
  const days = Array.from({ length: HORIZON_DAYS + 1 }, (_, i) => {
    const d = new Date(today.getFullYear(), today.getMonth(), today.getDate() + i);
    return { key: dateKey(d), top: i === 0 ? "Today" : d.toLocaleDateString("en-GB", { weekday: "short" }), day: d.getDate() };
  });
  $("sh-dates").innerHTML = days.map((d) => `<button type="button" class="date ${d.key === state.sheet.date ? "active" : ""}" data-date="${d.key}">
    <small>${d.top}</small><b>${d.day}</b></button>`).join("");
}

function renderSlots(popIndex) {
  const sh = state.sheet;
  const end = sh.start === null ? -1 : sh.start + sh.hours * 2;
  const past = sh.slots.filter((s) => s.status === "past").length;
  const note = past === sh.slots.length
    ? `<p class="muted small" style="grid-column:1/-1">This day is over. Pick another one.</p>`
    : past ? `<p class="muted small" style="grid-column:1/-1;margin:0 0 4px">Earlier slots today are over.</p>` : "";
  $("sh-slots").innerHTML = note + sh.slots.map((s, i) => {
    if (s.status === "past") return "";
    const busy = busySlot(i);
    const inRange = i >= sh.start && i < end;
    let cls = s.status;
    let note = s.status === "free" ? "free" : s.status === "partial" ? `${s.seats_free} left` : s.status;
    if (busy) {
      cls = "mine";
      note = busy.room_id === sh.roomId ? "yours" : "booked";
    }
    return `<button type="button" class="slot ${cls} ${inRange ? "in-range" : ""} ${i === sh.start ? "start" : ""} ${i === popIndex ? "just-picked" : ""}"
      data-slot="${i}" ${selectable(i) ? "" : "disabled"} title="${s.start}–${s.end}">${s.start}<small>${esc(note)}</small></button>`;
  }).join("");
}

function renderForm() {
  const sh = state.sheet;
  const r = range();
  const { canFull, maxSeats } = rules();
  const left = dayLeft();
  const when = r.length
    ? `<div class="when set"><b>${r[0].start} – ${r[r.length - 1].end}</b><span class="muted small">${esc(dayLabel(sh.date, true))} · ${hoursText(sh.hours)}</span></div>`
    : `<div class="when"><b>Pick a time</b><span class="muted small">${left >= 0.5 ? "Tap a free time slot to start" : "You've used your 4 h on this day. Try another day."}</span></div>`;
  const durations = [0.5, 1, 1.5, 2, 2.5, 3, 3.5, 4].map((h) => `<button type="button" class="chip ${sh.start !== null && h === sh.hours ? "active" : ""}"
    data-hours="${h}" ${sh.start === null || h > maxHours(sh.start) ? "disabled" : ""}>${h === 0.5 ? "30m" : `${h}h`}</button>`).join("");
  const thisHours = r.length ? sh.hours : 0;
  const purposes = PURPOSES.map((p) => {
    const blocked = purposeBlocked(p);
    return `<button type="button" class="purpose ${sh.purpose === p.id ? "active" : ""}" data-purpose="${p.id}"
      ${blocked ? `disabled title="${esc(blocked)}"` : ""}><span class="emoji">${p.emoji}</span>${p.label}</button>`;
  }).join("");
  const seatHint = sh.mode === "full" ? `Up to ${maxSeats}, the room's limit`
    : `Up to ${maxSeats} · seats still free at that time`;
  const alert = sh.error
    ? `<div class="alert" role="alert">${esc(sh.error)}${sh.suggestions.length ? `<div class="suggest"><span class="small" style="width:100%">Try one of these instead:</span>
        ${sh.suggestions.map((id) => `<button type="button" class="btn btn-sm" data-suggest="${esc(id)}">${esc(id)} <span class="muted">${esc(roomName(id))}</span></button>`).join("")}</div>` : ""}</div>`
    : "";

  $("sh-form").innerHTML = `
    <div class="block"><span class="field-label">When</span>${when}</div>
    <div class="block"><span class="field-label">How long</span><div class="durations">${durations}</div></div>
    <div class="block day-limit">
      <div class="row"><span class="muted">Your hours on ${esc(dayLabel(sh.date, true))}</span><b>${usedHours(sh.date) + thisHours} / ${DAY_LIMIT} h</b></div>
      <div class="bar"><i style="width:${((usedHours(sh.date) + thisHours) / DAY_LIMIT) * 100}%"></i></div>
    </div>
    <div class="block"><span class="field-label">Who can join?</span>
      <div class="modes">
        <button type="button" class="mode ${sh.mode === "full" ? "active" : ""}" data-mode="full" ${r.length && !canFull ? "disabled" : ""}>
          <span class="emoji">🔒</span><b>Private room</b><span>Only you and your group.</span></button>
        <button type="button" class="mode ${sh.mode === "partial" ? "active" : ""}" data-mode="partial">
          <span class="emoji">👥</span><b>Open to share</b><span>Others can join until it's full.</span></button>
      </div>
      ${r.length && !canFull ? `<p class="hint">Someone already booked part of this time, so you can only share it.</p>` : ""}
    </div>
    <div class="block people-row">
      <div><span class="field-label" style="margin:0">How many people?</span><span class="hint" style="margin:0">${esc(seatHint)}</span></div>
      <div class="stepper"><button type="button" data-seats="-1" ${sh.seats <= 1 ? "disabled" : ""} aria-label="Fewer">−</button>
        <output>${sh.seats}</output><button type="button" data-seats="1" ${sh.seats >= maxSeats ? "disabled" : ""} aria-label="More">+</button></div>
    </div>
    <div class="block"><span class="field-label">What for?</span><div class="purposes">${purposes}</div>
      ${sh.purpose === "custom" ? `<input class="text-input" id="custom" style="margin-top:8px" maxlength="80" placeholder="Describe it, e.g. Thesis writing" value="${esc(sh.custom)}">` : ""}
    </div>
    ${alert ? `<div class="block">${alert}</div>` : ""}
    <div class="block"><button type="button" class="btn btn-primary btn-lg" data-action="book" ${canBook() ? "" : "disabled"}>
      ${sh.busy ? "Booking…" : r.length ? `Book ${r[0].start}–${r[r.length - 1].end}` : "Book"}</button></div>`;
}

function canBook() {
  const sh = state.sheet;
  return !sh.busy && sh.start !== null && sh.purpose && (sh.purpose !== "custom" || sh.custom.trim()) && sh.mode;
}

function update(popIndex) {
  fixSelection();
  renderSlots(popIndex);
  renderForm();
}

function onSlot(i) {
  const sh = state.sheet;
  sh.error = null;
  if (dayLeft() < 0.5) {
    sh.error = `You've already booked ${DAY_LIMIT} h on ${dayLabel(sh.date)}. Pick another day.`;
    return update();
  }
  const end = sh.start === null ? -1 : sh.start + maxHours(sh.start) * 2;
  if (sh.start === null || i < sh.start || i >= end) {
    sh.start = i;
    sh.hours = Math.min(1, maxHours(i));
  } else if (i === sh.start) {
    sh.start = null;
  } else {
    sh.hours = (i - sh.start + 1) / 2;
  }
  update(i);
}

async function submitBooking(btn) {
  const sh = state.sheet;
  const r = range();
  sh.busy = true;
  sh.error = null;
  renderForm();
  try {
    const b = await api.book({
      room_id: sh.roomId, start: `${sh.date}T${r[0].start}`, hours: sh.hours, mode: sh.mode, seats: sh.seats,
      purpose: sh.purpose, custom_purpose: sh.purpose === "custom" ? sh.custom.trim() : null,
    });
    confetti(btn);
    toast(`Booked ${b.room_id}, ${dayLabel(sh.date)} ${hm(b.start)}–${hm(b.end)} 🎉`, { action: { label: "My bookings", run: openDrawer } });
    closeSheet();
    refreshMine();
    refreshRooms();
    state.picker.refresh();
  } catch (err) {
    if (handleAuth(err)) return;
    sh.busy = false;
    sh.error = err.message;
    sh.suggestions = err.status === 409 ? err.suggestions : [];
    await refreshMine();
    await loadSheetData();
  }
}

function wireSheet() {
  const dlg = $("room-dialog");
  document.addEventListener("keydown", (e) => {
    if (e.key === "Escape" && !dlg.hidden && !$("mine-drawer").open) closeSheet();
  });
  dlg.addEventListener("click", (e) => {
    const sh = state.sheet;
    if (!sh) return;
    const t = e.target.closest("button");
    if (!t || t.disabled) return;
    if (t.dataset.action === "close") return closeSheet();
    if (t.dataset.date) {
      sh.date = t.dataset.date;
      sh.start = null;
      sh.error = null;
      renderDates();
      t.scrollIntoView({ block: "nearest", inline: "nearest", behavior: "smooth" });
      return loadSheetData();
    }
    if (t.dataset.slot) return onSlot(Number(t.dataset.slot));
    if (!sh.slots) return;
    if (t.dataset.hours) { sh.hours = Number(t.dataset.hours); return update(sh.start); }
    if (t.dataset.mode) {
      sh.mode = t.dataset.mode;
      return update();
    }
    if (t.dataset.seats) { sh.seats += Number(t.dataset.seats); return update(); }
    if (t.dataset.purpose) {
      sh.purpose = t.dataset.purpose;
      if (sh.purpose === "event") sh.mode = "full";
      update();
      if (sh.purpose === "custom") $("custom")?.focus();
      return;
    }
    if (t.dataset.suggest) {
      return openRoom(t.dataset.suggest, {
        date: sh.date, time: range()[0]?.start, hours: sh.hours, mode: sh.mode, seats: sh.seats, purpose: sh.purpose, custom: sh.custom,
      });
    }
    if (t.dataset.action === "book") return submitBooking(t);
  });
  dlg.addEventListener("input", (e) => {
    if (e.target.id !== "custom" || !state.sheet) return;
    state.sheet.custom = e.target.value;
    const btn = dlg.querySelector('[data-action="book"]');
    if (btn) btn.disabled = !canBook();
  });
}

// ---------- Search with suggestions ----------

const search = { results: [], active: -1, seq: 0, timer: null };

function highlight(text, q) {
  const i = text.toLowerCase().indexOf(q.toLowerCase());
  if (!q || i < 0) return esc(text);
  return `${esc(text.slice(0, i))}<mark>${esc(text.slice(i, i + q.length))}</mark>${esc(text.slice(i + q.length))}`;
}

function renderSuggestions(q) {
  const list = $("search-list");
  list.innerHTML = search.results.length
    ? search.results.map((r, i) => `<li role="option" id="sug-${i}" data-room="${esc(r.id)}" aria-selected="${i === search.active}">
        <span class="sug-id">${highlight(r.id, q)}</span><span class="sug-name">${highlight(r.name, q)}</span>
        <span class="pill ${esc(r.status)}">${r.status === "closed" ? "Closed" : `${r.seats_free} free`}</span></li>`).join("")
    : `<li class="sug-empty">No room matches “${esc(q)}”</li>`;
  list.classList.remove("hidden");
  $("search-input").setAttribute("aria-expanded", "true");
  $("search-input").setAttribute("aria-activedescendant", search.active >= 0 ? `sug-${search.active}` : "");
}

function closeSuggestions() {
  $("search-list").classList.add("hidden");
  $("search-input").setAttribute("aria-expanded", "false");
  search.active = -1;
}

function pick(id) {
  $("search-input").value = id;
  closeSuggestions();
  $("search-input").blur();
  openRoom(id);
}

function wireSearch() {
  const input = $("search-input");
  input.addEventListener("input", () => {
    clearTimeout(search.timer);
    const q = input.value.trim();
    if (!q) return closeSuggestions();
    search.timer = setTimeout(async () => {
      const seq = ++search.seq;
      try {
        const results = await api.search(q);
        if (seq !== search.seq) return;
        search.results = results;
        search.active = results.length ? 0 : -1;
        renderSuggestions(q);
      } catch (err) {
        handleAuth(err);
      }
    }, 150);
  });
  input.addEventListener("keydown", (e) => {
    const n = search.results.length;
    const open = !$("search-list").classList.contains("hidden");
    if (e.key === "ArrowDown" && open && n) { e.preventDefault(); search.active = (search.active + 1) % n; renderSuggestions(input.value.trim()); }
    else if (e.key === "ArrowUp" && open && n) { e.preventDefault(); search.active = (search.active - 1 + n) % n; renderSuggestions(input.value.trim()); }
    else if (e.key === "Enter") {
      e.preventDefault();
      if (open && search.results[search.active]) pick(search.results[search.active].id);
      else if (input.value.trim()) api.search(input.value.trim(), 1).then((r) => (r[0] ? pick(r[0].id) : toast("No room found", { error: true })));
    } else if (e.key === "Escape") { closeSuggestions(); input.blur(); }
  });
  input.addEventListener("focus", () => { if (input.value.trim() && search.results.length) renderSuggestions(input.value.trim()); });
  input.addEventListener("blur", () => setTimeout(closeSuggestions, 120));
  $("search-list").addEventListener("mousedown", (e) => {
    const li = e.target.closest("[data-room]");
    if (li) { e.preventDefault(); pick(li.dataset.room); }
  });
  document.addEventListener("keydown", (e) => {
    if (e.key === "/" && !["INPUT", "TEXTAREA"].includes(document.activeElement?.tagName) && !document.querySelector("dialog[open]")) {
      e.preventDefault();
      input.focus();
    }
  });
}

// ---------- Profile menu and theme ----------

function save(key, value) {
  try { localStorage.setItem(key, value); } catch { /* private mode: the choice just isn't remembered */ }
}

function syncThemeButtons() {
  const root = document.documentElement.dataset;
  for (const b of document.querySelectorAll("[data-theme]")) b.classList.toggle("active", b.dataset.theme === (root.theme || "violet"));
  for (const b of $("modes").querySelectorAll("button")) b.classList.toggle("active", b.dataset.mode === (root.mode || "auto"));
}

function wireMenu() {
  const menu = $("menu");
  const avatar = $("avatar");
  const toggle = (open) => { menu.classList.toggle("hidden", !open); avatar.setAttribute("aria-expanded", String(open)); };
  avatar.addEventListener("click", (e) => { e.stopPropagation(); toggle(menu.classList.contains("hidden")); });
  document.addEventListener("click", (e) => { if (!menu.contains(e.target)) toggle(false); });
  $("swatches").addEventListener("click", (e) => {
    const b = e.target.closest("[data-theme]");
    if (!b) return;
    document.documentElement.dataset.theme = b.dataset.theme;
    save("roomv-theme", b.dataset.theme);
    syncThemeButtons();
  });
  $("modes").addEventListener("click", (e) => {
    const b = e.target.closest("[data-mode]");
    if (!b) return;
    document.documentElement.dataset.mode = b.dataset.mode;
    save("roomv-mode", b.dataset.mode);
    syncThemeButtons();
  });
  $("logout").addEventListener("click", async () => {
    try { await api.logout(); } finally { location.replace("login.html"); }
  });
  syncThemeButtons();
}

// ---------- Start ----------

function wirePage() {
  $("mine-btn").addEventListener("click", openDrawer);
  const drawer = $("mine-drawer");
  const closeDrawer = () => {
    drawer.classList.add("closing");
    setTimeout(() => { drawer.classList.remove("closing"); drawer.close(); }, 200);
  };
  drawer.addEventListener("cancel", (e) => { e.preventDefault(); closeDrawer(); });
  drawer.addEventListener("click", (e) => {
    if (e.target === drawer || e.target.closest("[data-close]")) return closeDrawer();
    const t = e.target.closest("button[data-action]");
    if (!t || t.disabled) return;
    if (t.dataset.action === "cancel") return cancelBooking(t);
    if (t.dataset.action === "rate") return rateRoom(t);
    if (t.dataset.action === "find") { closeDrawer(); setTimeout(() => $("search-input").focus(), 220); return; }
    if (t.dataset.action === "add") {
      const b = state.mine.find((x) => x.id === Number(t.dataset.id));
      closeDrawer();
      openRoom(b.room_id, { date: b.start.slice(0, 10), time: hm(b.end), hours: 1, mode: b.mode, seats: b.seats, purpose: b.purpose, custom: b.custom_purpose || "" });
    }
  });
}

async function main() {
  try {
    state.user = await api.me();
  } catch (err) {
    if (!handleAuth(err)) toast(err.message, { error: true });
    return;
  }
  $("avatar").textContent = (state.user.name || state.user.email).trim()[0].toUpperCase();
  $("user-name").textContent = state.user.name;
  $("user-email").textContent = state.user.email;
  wireMenu();
  wireSearch();
  wireSheet();
  wirePage();
  state.picker = createPicker($("picker"), {
    onOpen: (id, opts) => openRoom(id, opts),
    onError: (err) => { if (!handleAuth(err)) toast(err.message, { error: true }); },
  });
  await Promise.all([refreshRooms(), refreshMine()]);
  await createView();
  let tick = 0;
  setInterval(async () => {
    await Promise.all([refreshRooms(), refreshMine()]);
    if (state.sheet && !state.sheet.busy) loadSheetData();
    if (++tick % SLOT_REFRESH_TICKS === 0) state.picker.refresh();
  }, POLL_MS);
}

main();
