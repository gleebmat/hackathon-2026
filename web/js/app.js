// Campus Booking System main page: campus map, room picker (picker.js), search, booking sheet and "My bookings".
// Data: api.js (docs/PLAN.md, "Frontend flow"). Map: tom-claude's web/map3d/ when it is merged,
// otherwise the 2D plan in plan2d.js (same module API).
import * as api from "./api.js";
import { createPicker } from "./picker.js";
import { createPlan, layoutBuilding } from "./plan2d.js";
import { t, locale, people, applyStatic, langSwitch, lang, setLang } from "./i18n.js";
import { renderFooter } from "./footer.js";

const POLL_MS = 1000;            // map + room list: board changes show up within a second
const SLOT_REFRESH_TICKS = 30;  // the picker reloads every room's slots every 30 s
const DAY_LIMIT = 4;
const HORIZON_DAYS = 14;
const STATUS = { free: t("st_free"), partial: t("st_partial"), full: t("st_full"), ghost: t("st_ghost"), closed: t("st_closed"),
  unbookable: t("st_unbookable") };
const PURPOSES = [
  { id: "quiet_study", label: t("p_quiet_study"), icon: "book", noise: "quiet" },
  { id: "group_study", label: t("p_group_study"), icon: "bulb", noise: "moderate" },
  { id: "meeting", label: t("p_meeting"), icon: "briefcase", noise: "moderate" },
  { id: "gaming", label: t("p_gaming"), icon: "gamepad", noise: "loud" },
  { id: "board_games", label: t("p_board_games"), icon: "dice", noise: "loud" },
  { id: "event", label: t("p_event"), icon: "spark", noise: "loud" },
  { id: "custom", label: t("p_custom"), icon: "pencil", noise: "moderate" },
];
// Our own line icons (sprite in index.html) instead of emoji.
const ic = (name) => `<svg class="ic" aria-hidden="true"><use href="#ic-${name}"/></svg>`;
const PURPOSE = Object.fromEntries(PURPOSES.map((p) => [p.id, p]));

const state = { user: null, rooms: [], mine: [], view: null, picker: null, sheet: null, myRatings: {}, notes: [] };
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
  const text = d.toLocaleDateString(locale, { weekday: "short", day: "numeric", month: "short" });
  if (diff === 0) return long ? t("today_long", { d: text }) : t("today");
  if (diff === 1) return long ? t("tomorrow_long", { d: text }) : t("tomorrow");
  return text;
}

function minutesUntil(iso) {
  return Math.max(0, Math.round((new Date(iso) - new Date()) / 60000));
}

function handleAuth(err) {
  if (err.status === 401) {
    location.replace(`login.html${location.search}`);   // keeps ?room=… for after the login
    return true;
  }
  return false;
}

// ---------- Toasts and confetti ----------

function toast(message, { error = false, action, ms } = {}) {
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
  setTimeout(dismiss, ms || (error ? 6000 : 4500));
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
  applyingRoute = true;   // the map's start-up selection must not overwrite the address it is about to apply
  try {
    await buildView();
    applyMapRoute();      // ?building= / ?floor= from the address
  } finally {
    applyingRoute = false;
  }
}

async function buildView() {
  const el = $("building");
  try {
    const [{ createBuilding }, campus] = await Promise.all([
      import("../map3d/building3d.js"),
      fetch("map3d/campus.json").then((r) => { if (!r.ok) throw new Error("no campus.json"); return r.json(); }),
    ]);
    state.routes = campus.routes ?? {};
    state.view = createBuilding(el, campus, { labels: {
      all: t("map_all"), allBuildings: t("map_all_buildings"), allFloors: t("map_all_floors"),
      everyFloor: t("map_every_floor"), floor: t("map_floor"), floorTitle: t("map_floor_title"),
      entrance: t("map_entrance"), compass: t("map_compass").split(","), compassTitle: t("map_compass_title"),
      offices: t("map_offices"), officesTitle: t("map_offices_title") },
      onSelect: ({ building, floor }) => {
        if (routeParams().has("room")) return;   // focusing a room moves the map itself: not a choice to keep
        setRoute({ building, floor: floor === null ? "all" : floor === 1 ? null : floor });
      } });
    el.classList.add("is-3d");
  } catch {
    state.view = createPlan(el, (await api.building()) || layoutBuilding(state.rooms));
  }
  // The map also draws rooms that can't be booked (offices, WCs); only bookable ones open the sheet.
  state.view.onRoomClick((id) => {
    if (id.startsWith("machine:")) return showMachineInfo(id);
    if (state.rooms.some((r) => r.id === id)) openRoom(id);
  });
  state.view.onRoomHover?.(showMapTip);
  for (const r of state.rooms) state.view.setStatus(r.id, r);
  state.view.setFloor?.(1);   // open on floor 1 (the board room Z.1.04 is there); "All floors" shows everything
}

// Small tooltip that follows the pointer over a bookable room or a coffee / vending machine on the 3D map.
const STATUS_VAR = { free: "--free", partial: "--shared", full: "--full", ghost: "--ghost", closed: "--muted", unbookable: "--unbookable" };
function showMapTip(id, e) {
  const card = $("building").parentElement;
  let tip = card.querySelector(".map-tip");
  if (!tip) {
    tip = document.createElement("div");
    tip.className = "map-tip";
    card.append(tip);
  }
  const m = id?.startsWith("machine:") && state.view?.machine?.(id);
  const r = id && state.rooms.find((x) => x.id === id);
  if ((!r && !m) || !e) { tip.classList.remove("on"); return; }
  tip.innerHTML = m ? `<b>${esc(t(`machine_${m.kind}`))}</b>${esc(t("machine_where", { b: m.building, floor: m.floor }))}` : `<b>${esc(r.label || r.id)}</b>${esc(r.label ? `${r.id} · ${r.name}` : r.name)}` +
    `<i style="background:var(${STATUS_VAR[r.status] ?? "--muted"})"></i>${STATUS[r.status] ?? esc(r.status)}` +
    (["closed", "unbookable"].includes(r.status) ? "" : ` · ${t("seats_of", { free: r.seats_free, cap: r.capacity })}`);
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

let mineJson = "";   // last bookings drawn: redraw only on a change, so a pending "Sure? Tap again" survives polling

async function refreshMine() {
  let json;
  try {
    state.mine = await api.myBookings();
    json = JSON.stringify(state.mine);
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
  if ($("mine-drawer").open && json !== mineJson) renderMine();
  mineJson = json;
}

function bookingCard(b, { actions = true } = {}) {
  const isNow = b.start <= nowKey() && nowKey() < b.end;
  const mode = t(b.mode === "full" ? "private_tag" : "share_tag");
  const statusTag = b.status === "cancelled" ? `<span class="tag">${t("cancelled")}</span>`
    : b.status === "released" ? `<span class="tag">${t("released")}</span>`
    : isNow ? `<span class="tag now">${t("now")}</span>` : "";
  const ghost = b.ghost_release_at
    ? `<div class="ghost-alert">${t("ghost_mine", { t: hm(b.ghost_release_at), m: minutesUntil(b.ghost_release_at) })}</div>`
    : "";
  const left = DAY_LIMIT - usedHours(b.start.slice(0, 10));
  const buttons = actions && b.status === "active" && b.end > nowKey() ? `<div class="booking-actions">
      <button class="btn btn-sm" type="button" data-action="add" data-id="${b.id}" ${left < 0.5 ? `disabled title="${t("day_used_up")}"` : ""}>${t("add_time")}</button>
      <button class="btn btn-sm" type="button" data-action="ics" data-id="${b.id}">${t("add_calendar")}</button>
      <button class="btn btn-sm btn-danger" type="button" data-action="cancel" data-id="${b.id}">${t("cancel")}</button></div>` : "";
  return `<article class="booking ${isNow && b.status === "active" ? "now" : ""}">
    <div class="booking-top">
      <div><div class="booking-time">${hm(b.start)}–${hm(b.end)}</div>
        <div class="booking-room">${esc(b.room_id)} · ${esc(roomName(b.room_id))}</div></div>
      ${statusTag}
    </div>
    <div class="booking-tags">
      <span class="tag">${ic(PURPOSE[b.purpose]?.icon ?? "pencil")} ${esc(purposeText(b))}</span>
      <span class="tag">${mode}</span>
      <span class="tag">${people(b.seats)}</span>
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
    data-room="${esc(b.room_id)}" data-stars="${n}" aria-label="${n > 1 ? t("n_stars", { n }) : t("n_stars_1")}">★</button>`).join("");
  return `<div class="rate-row"><span class="muted small">${t(mine ? "your_rating" : "rate_room")}</span><span class="stars-input">${stars}</span></div>`;
}

async function rateRoom(btn) {
  const room = btn.dataset.room, stars = Number(btn.dataset.stars);
  try {
    await api.rate(room, stars);
    state.myRatings[room] = stars;
    toast(t("rated", { room, n: stars }));
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
      <div class="day-head"><b>${esc(dayLabel(day, true))}</b><span class="hours">${t("hours_used", { used, limit: DAY_LIMIT })}</span></div>
      <div class="bar"><i style="width:${(used / DAY_LIMIT) * 100}%"></i></div>
      ${next.filter((b) => b.start.startsWith(day)).map((b) => bookingCard(b)).join("")}
    </section>`;
  }).join("");
  body.innerHTML = `
    ${favoritesHtml()}
    ${groups || `<div class="drawer-empty"><span class="empty-ic">${ic("cal")}</span><p><b>${t("no_upcoming")}</b></p><p>${t("no_upcoming_sub")}</p></div>`}
    <button class="btn btn-primary" type="button" data-action="find">${t("book_a_room")}</button>
    ${history.length ? `<details class="history"><summary>${t("history", { n: history.length })}</summary>
      ${history.map((b) => bookingCard(b, { actions: false })).join("")}</details>` : ""}`;
}

function openDrawer() {
  setRoute({ view: "bookings" }, { push: true });
  renderMine();
  $("mine-drawer").showModal();
  refreshMine();
}

async function cancelBooking(btn) {
  if (!btn.classList.contains("confirm")) {
    btn.classList.add("confirm");
    btn.textContent = t("sure");
    setTimeout(() => { if (btn.isConnected) { btn.classList.remove("confirm"); btn.textContent = t("cancel"); } }, 3500);
    return;
  }
  btn.disabled = true;
  try {
    const gone = state.mine.find((x) => x.id === Number(btn.dataset.id));
    await api.cancel(Number(btn.dataset.id));
    if (gone) notify(`cancelled-${gone.id}`, "cancelled", "note_cancelled",
      { room: gone.room_id, day: dayLabel(gone.start.slice(0, 10)), t: `${hm(gone.start)}–${hm(gone.end)}` }, gone.room_id, { toast: false });
    toast(t("booking_cancelled"));
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

// The card on the map: rooms that can't be booked (55+ seats) and the coffee / vending machines.
function infoBox() {
  const card = document.querySelector(".map-card");
  let box = card.querySelector(".map-info");
  if (!box) {
    box = document.createElement("div");
    box.className = "map-info";
    card.append(box);
    box.addEventListener("click", (e) => {
      const way = e.target.closest("[data-action=way]");
      if (way) return showWay(way.dataset.room);
      if (!e.target.closest(".map-info-x")) return;
      state.view?.clearRoute?.();
      box.classList.remove("on");
      if (box.dataset.kind === "machine") return;
      leaveRoute("room");
      state.view?.showAll();
    });
  }
  return box;
}

function showMachineInfo(id) {
  const m = state.view?.machine?.(id);
  if (!m) return;
  const box = infoBox();
  box.dataset.kind = "machine";
  box.innerHTML = `<button class="map-info-x" type="button" aria-label="Close">${ic("x")}</button>
    <div class="map-info-id"><span class="machine-dot ${esc(m.kind)}"></span>${esc(t(`machine_${m.kind}`))}</div>
    <div class="muted small">${esc(t("machine_where", { b: m.building, floor: m.floor }))}</div>
    <p class="map-info-note">${esc(t(`machine_${m.kind}_note`))}</p>`;
  box.classList.add("on");
}

// Rooms that can't be booked (55+ seats) get a small card on the map, not the booking panel.
function showRoomInfo(r) {
  closeSheet({ route: false });
  state.view?.focusRoom(r.id);
  const box = infoBox();
  box.dataset.kind = "room";
  box.innerHTML = `<button class="map-info-x" type="button" aria-label="Close">${ic("x")}</button>
    <div class="map-info-id">${esc(r.label || r.id)}</div>
    <div class="muted small">${esc(r.label ? `${r.id} · ${r.name}` : r.name)}</div>
    <div class="map-info-facts"><span>${ic("seat")} ${esc(t("seats_n", { n: r.capacity }))}</span>
      <span>${ic("sound")} ${Math.round(r.noise_db)} dB</span></div>
    <p class="map-info-note">${ic("lock")} ${esc(t("info_not_bookable"))}</p>${wayButton(r.id)}`;
  box.classList.add("on");
}

function hideRoomInfo() {
  document.querySelector(".map-info")?.classList.remove("on");
}

async function openRoom(id, opts) {
  closeSuggestions();
  setRoute({ room: id, view: null }, { push: !opts?.replaceRoute });
  state.view?.clearRoute?.();
  const known = state.rooms.find((r) => r.id === id);
  if (known && known.bookable === false) return showRoomInfo(known);
  hideRoomInfo();
  state.view?.focusRoom(id);
  state.sheet = newSheet(id, opts);
  const dlg = $("room-dialog");
  dlg.innerHTML = `
    <div class="sheet-head" id="sh-head"><div class="skeleton" style="min-height:60px;width:260px"></div></div>
    <div class="sheet-body">
      <div class="sheet-col">
        <div class="block" id="sh-now"></div>
        <div class="block"><div class="block-title"><h3>${t("pick_day")}</h3></div><div class="dates" id="sh-dates"></div></div>
        <div class="block">
          <div class="block-title"><h3>${t("pick_time")}</h3><span class="muted small">${t("tap_start_end")}</span></div>
          <div class="slots" id="sh-slots"><div class="skeleton" style="grid-column:1/-1;min-height:200px"></div></div>
          <div class="slot-legend">
            <span><i style="background:var(--free)"></i>${t("legend_free")}</span>
            <span><i style="background:var(--shared)"></i>${t("leg_shared_left")}</span>
            <span><i style="background:var(--full)"></i>${t("legend_full")}</span>
            <span><i style="background:var(--brand)"></i>${t("leg_yours")}</span>
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

function closeSheet({ route = true } = {}) {
  const dlg = $("room-dialog");
  if (dlg.hidden || dlg.classList.contains("closing")) return;
  if (route) leaveRoute("room");
  dlg.classList.add("closing");
  setTimeout(() => {
    dlg.classList.remove("closing");
    dlg.hidden = true;
    state.sheet = null;
    state.view?.clearRoute?.();
    applyingRoute = true;   // the map goes back to the building/floor in the address, without rewriting it
    try {
      state.view?.showAll();
      applyMapRoute();
    } finally {
      applyingRoute = false;
    }
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
  if (p.id === "event" && (!canFull || sh.mode === "partial")) return t("events_whole");
  if (sh.mode === "partial" && p.noise === "quiet" && noises.has("loud")) return t("loud_then");
  if (sh.mode === "partial" && p.noise === "loud" && noises.has("quiet")) return t("quiet_then");
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

// Ratings stay folded away until someone wants them.
function ratingBox(r) {
  const avg = r.rating != null
    ? `<span class="stars"><s style="--p:${(r.rating / 5) * 100}%">★★★★★</s>${r.rating.toFixed(1)}</span> <span class="muted small">${esc(t("ratings_n", { n: r.votes }))}</span>`
    : `<span class="muted">${esc(t("no_ratings"))}</span>`;
  const mine = r.my_rating ? `<div class="muted small">${esc(t("your_stars", { n: r.my_rating }))}</div>` : "";
  return `<details class="rating-box"><summary>${ic("star")} ${esc(t("ratings"))}</summary><div class="rating-body">${avg}${mine}</div></details>`;
}

function renderSheetHead() {
  const r = state.sheet.room;
  const live = r.live ? `<span class="live-badge">LIVE</span>` : "";
  const left = r.left_items > 0
    ? `<span class="left-badge" title="${esc(t("left_behind_title"))}">${t("left_behind")}</span>` : "";
  $("sh-head").innerHTML = `
    <div>
      <div class="sheet-title"><h2 id="room-title">${esc(r.label || r.id)}</h2><span class="muted">${esc(r.label ? `${r.id} · ${r.name}` : r.name)}</span></div>
      <div class="sheet-meta">
        <span class="pill ${esc(r.status)}">${STATUS[r.status] ?? esc(r.status)}</span>${live}${left}
        <span class="meta"><svg class="icon"><use href="#i-users"/></svg>${esc(occupancyText(r))}</span>
        <span class="meta"><svg class="icon"><use href="#i-sound"/></svg>${r.board && !r.live ? "— dB" : `${r.noise_db.toFixed(0)} dB · ${esc(t(`noise_${r.noise_class}`))}`}</span>
      </div>
    </div>
    <div class="sheet-tools">
      ${favButton(r)}
      ${wayButton(r.id)}
      <button class="btn btn-sm" type="button" data-action="share">${t("copy_link")}</button>
      <button class="icon-btn" type="button" data-action="close" aria-label="${t("close")}"><svg class="icon"><use href="#i-close"/></svg></button>
    </div>`;
  const now = r.bookings_now.length
    ? r.bookings_now.map((b) => `<div class="now-item"><span>${ic(b.shareable ? "users" : "lock")} ${people(b.seats)} · ${esc(PURPOSE[b.purpose]?.label ?? b.purpose)}</span>
        <span class="muted">${t(b.shareable ? "open_join" : "private_dot")}${t("until", { t: hm(b.end) })}</span></div>`).join("")
    : `<div class="now-item"><span>${t("nobody_booked")}</span></div>`;
  const ghost = r.status === "ghost" && r.ghost_release_at
    ? `<div class="ghost-alert" style="margin-top:8px">${t("ghost_room", { t: esc(r.ghost_release_at.slice(11, 19)) })}</div>` : "";
  $("sh-now").innerHTML = `<div class="block-title"><h3>${t("right_now")}</h3></div>${r.board ? boardCard(r) : ""}<div class="now-list">${now}</div>${sensorCheck(r)}${ghost}${ratingBox(r)}`;
}

// ---------- "Show the way": walking route on the 3D map ----------
// Routes come with the map (campus.json "routes", tools/campus3d/gen_routes.py): from the main entrance, or for far
// rooms from the nearest outside door, along corridors and stairs to the room's door.

function wayButton(id) {
  if (!state.routes?.[id] || !state.view?.showRoute) return "";
  return `<button class="btn btn-sm way-btn" type="button" data-action="way" data-room="${esc(id)}">${ic("pin")} ${esc(t("way_btn"))}</button>`;
}

function showWay(id) {
  const r = state.routes?.[id];
  if (!r) return;
  state.view.showRoute(r, { startLabel: t(r.from === "main" ? "way_start" : "way_door") });   // the main entrance has its own tag
  $("building").scrollIntoView({ behavior: "smooth", block: "center" });
  const floors = [...new Set(r.points.map((p) => p[2]))];
  const stairs = floors.length > 1 ? t("way_stairs", { n: r.points.at(-1)[2] }) : "";
  toast(t("way_info", { from: t(r.from === "main" ? "way_from_main" : "way_from_door"), m: Math.round(r.length),
    min: Math.max(1, Math.ceil(r.length / 72)), stairs }), { ms: 7000 });   // walking 1.2 m/s
}

// ---------- Favourite rooms (stored per account in the backend) ----------

function favButton(r) {
  const label = t(r.favorite ? "fav_remove" : "fav_add");
  const likes = r.likes ? `<span class="fav-n">${r.likes}</span>` : "";
  return `<button class="btn btn-sm fav-btn ${r.favorite ? "on" : ""}" type="button" data-action="fav" data-room="${esc(r.id)}"
    aria-pressed="${r.favorite}" aria-label="${esc(label)}" title="${esc(label)}">${ic("heart")}${likes}</button>`;
}

const favRooms = () => state.rooms.filter((r) => r.favorite);

function favoritesHtml() {
  const list = favRooms();
  const chips = list.map((r) => `<div class="fav-chip">
      <button type="button" class="fav-open" data-action="open-fav" data-room="${esc(r.id)}">
        <b>${esc(r.label || r.id)}</b><span class="pill ${esc(r.status)}">${STATUS[r.status] ?? esc(r.status)}</span>
        <span class="muted small">${esc(r.name)}</span></button>
      <button type="button" class="fav-x" data-action="fav" data-room="${esc(r.id)}" aria-label="${esc(t("fav_remove"))}" title="${esc(t("fav_remove"))}">${ic("heart")}</button>
    </div>`).join("");
  return `<section class="fav-group"><div class="day-head"><b>${t("favorites")}</b><span class="hours">${list.length || ""}</span></div>
    ${chips ? `<div class="fav-list">${chips}</div>` : `<p class="muted small">${t("no_favs")}</p>`}</section>`;
}

async function toggleFavorite(btn) {
  const id = btn.dataset.room;
  const room = state.rooms.find((r) => r.id === id);
  const on = !(room?.favorite ?? state.sheet?.room?.favorite);
  btn.disabled = true;
  try {
    const res = await (on ? api.like(id) : api.unlike(id));
    if (room) room.favorite = res.favorite;
    if (state.sheet?.roomId === id && state.sheet.room) {
      Object.assign(state.sheet.room, { favorite: res.favorite, likes: res.likes });
      renderSheetHead();
    }
    state.picker.setRooms(state.rooms);
    if ($("mine-drawer").open) renderMine();
    toast(t(on ? "fav_added" : "fav_removed", { room: room?.label || id }));
  } catch (err) {
    if (!handleAuth(err)) toast(err.message, { error: true });
  } finally {
    if (btn.isConnected) btn.disabled = false;
  }
}

// The board room's live card: a big head count, the noise with a meter and the last minute as a line.
const noiseLog = { room: null, values: [] };   // live noise samples of the open board room (~2 per second)
const PERSON_SVG = `<svg viewBox="0 0 24 24" aria-hidden="true"><circle cx="12" cy="7" r="4"/><path d="M4 21a8 8 0 0 1 16 0z"/></svg>`;
const CHIP_SVG = `<svg class="board-chip" viewBox="0 0 24 24" aria-hidden="true"><path d="M7 4v3M12 4v3M17 4v3M7 17v3M12 17v3M17 17v3M4 7h3M4 12h3M4 17h3M17 7h3M17 12h3M17 17h3"/><rect x="7" y="7" width="10" height="10" rx="2"/><circle cx="12" cy="12" r="2.2"/></svg>`;

function boardCard(r) {
  if (noiseLog.room !== r.id) Object.assign(noiseLog, { room: r.id, values: [] });
  if (!r.live) {
    noiseLog.values = [];
    return `<div class="board-card off"><div class="board-top">${CHIP_SVG}<b>${t("board_title")}</b></div>
      <p class="muted small">${t("board_off")}</p></div>`;
  }
  noiseLog.values.push(r.noise_db);
  if (noiseLog.values.length > 120) noiseLog.values.shift();
  const counted = r.sensor && r.counted;
  const n = r.sensor ? r.present : null;
  const big = n === null ? "—" : counted || n === 0 ? n : "1+";
  const label = n === null ? t("board_no_count") : counted || n === 0 ? t("board_people") : t("board_someone");
  const icons = counted && n > 0
    ? `<div class="people-icons">${PERSON_SVG.repeat(Math.min(n, 12))}${n > 12 ? `<span>+${n - 12}</span>` : ""}</div>` : "";
  const pct = Math.max(0, Math.min(100, ((r.noise_db - 30) / 60) * 100));
  const v = noiseLog.values;
  const lo = Math.min(...v) - 2, hi = Math.max(lo + 12, Math.max(...v) + 2);   // zoom to the minute's range
  const line = v.length > 1
    ? v.map((d, i) => `${((i / (v.length - 1)) * 120).toFixed(1)},${(28 - ((d - lo) / (hi - lo)) * 26).toFixed(1)}`).join(" ")
    : "";
  return `<div class="board-card">
    <div class="board-top">${CHIP_SVG}<b>${t("board_title")}</b><span class="live-badge">LIVE</span></div>
    <div class="board-stats">
      <div class="board-stat"><div class="big">${big}</div><div class="muted small">${esc(label)}</div>${icons}</div>
      <div class="board-stat"><div class="big ${esc(r.noise_class)}">${r.noise_db.toFixed(0)}<small> dB</small></div>
        <div class="muted small">${t("board_noise")} · ${esc(t(`noise_${r.noise_class}`))}</div>
        <div class="noise-meter"><i style="left:${pct.toFixed(1)}%"></i></div></div>
    </div>
    ${line ? `<div class="muted small">${t("board_minute")}</div><svg class="noise-line" viewBox="0 0 120 30" preserveAspectRatio="none"><polyline points="${line}"/></svg>` : ""}
    <p class="muted small board-hw">${t("board_hw")}</p>
  </div>`;
}

// Booked seats next to what the room's sensor actually sees. `counted` false = the board only knows yes/no.
// An empty room always reads "Nobody here": readings with and without a head count used to alternate between
// "0 people here now" and "Nobody here" for the same empty room.
function seenText(r) {
  if (!(r.present > 0)) return t("nobody_here");
  return r.counted ? t(r.present === 1 ? "here_one" : "here_many", { n: r.present }) : t("someone_here");
}

function occupancyText(r) {
  if (r.board && !r.sensor) return t(r.live ? "camera_unavailable" : "board_offline");
  if (!r.sensor) return t("here_max", { n: r.people, cap: r.capacity });
  return r.booked ? t("booked_for_seen", { b: r.booked, seen: seenText(r) }) : t("seen_max", { seen: seenText(r), cap: r.capacity });
}

function sensorCheck(r) {
  if (!r.sensor || !r.booked) return "";
  const match = r.counted ? r.present >= r.booked : r.present > 0;
  return `<div class="sensor-check ${r.present === 0 ? "empty" : match ? "ok" : "fewer"}">
    <span>${t("booked_for_b", { b: r.booked })}</span><span>${t("sensor_b", { s: esc(seenText(r)) })}</span></div>`;
}

function renderDates() {
  const today = new Date();
  const days = Array.from({ length: HORIZON_DAYS + 1 }, (_, i) => {
    const d = new Date(today.getFullYear(), today.getMonth(), today.getDate() + i);
    return { key: dateKey(d), top: i === 0 ? t("today") : d.toLocaleDateString(locale, { weekday: "short" }), day: d.getDate() };
  });
  $("sh-dates").innerHTML = days.map((d) => `<button type="button" class="date ${d.key === state.sheet.date ? "active" : ""}" data-date="${d.key}">
    <small>${d.top}</small><b>${d.day}</b></button>`).join("");
}

function renderSlots(popIndex) {
  const sh = state.sheet;
  const end = sh.start === null ? -1 : sh.start + sh.hours * 2;
  const past = sh.slots.filter((s) => s.status === "past").length;
  const note = past === sh.slots.length
    ? `<p class="muted small" style="grid-column:1/-1">${t("day_over")}</p>`
    : past ? `<p class="muted small" style="grid-column:1/-1;margin:0 0 4px">${t("earlier_over")}</p>` : "";
  $("sh-slots").innerHTML = note + sh.slots.map((s, i) => {
    if (s.status === "past") return "";
    const busy = busySlot(i);
    const inRange = i >= sh.start && i < end;
    let cls = s.status;
    let note = s.status === "partial" ? t("s_left", { n: s.seats_free }) : t(`s_${s.status}`);
    if (busy) {
      cls = "mine";
      note = t(busy.room_id === sh.roomId ? "s_yours" : "s_booked");
    }
    return `<button type="button" class="slot ${cls} ${inRange ? "in-range" : ""} ${i === sh.start ? "start" : ""} ${i === popIndex ? "just-picked" : ""}"
      data-slot="${i}" ${selectable(i) ? "" : "disabled"} title="${s.start}–${s.end}">${s.start}<small>${esc(note)}</small></button>`;
  }).join("");
}

function renderForm() {
  const sh = state.sheet;
  if (sh.room && sh.room.bookable === false) {   // lecture halls, Aula, atrium: 55+ seats (app/booking.py)
    $("sh-form").innerHTML = `<div class="block"><div class="info-note">${ic("lock")} ${t("not_bookable")}</div></div>`;
    return;
  }
  const r = range();
  const { canFull, maxSeats } = rules();
  const left = dayLeft();
  const when = r.length
    ? `<div class="when set"><b>${r[0].start} – ${r[r.length - 1].end}</b><span class="muted small">${esc(dayLabel(sh.date, true))} · ${hoursText(sh.hours)}</span></div>`
    : `<div class="when"><b>${t("pick_time")}</b><span class="muted small">${t(left >= 0.5 ? "tap_free_slot" : "used_4h")}</span></div>`;
  const durations = [0.5, 1, 1.5, 2, 2.5, 3, 3.5, 4].map((h) => `<button type="button" class="chip ${sh.start !== null && h === sh.hours ? "active" : ""}"
    data-hours="${h}" ${sh.start === null || h > maxHours(sh.start) ? "disabled" : ""}>${h === 0.5 ? "30m" : `${h}h`}</button>`).join("");
  const thisHours = r.length ? sh.hours : 0;
  const purposes = PURPOSES.map((p) => {
    const blocked = purposeBlocked(p);
    return `<button type="button" class="purpose ${sh.purpose === p.id ? "active" : ""}" data-purpose="${p.id}"
      ${blocked ? `disabled title="${esc(blocked)}"` : ""}>${ic(p.icon)}${p.label}</button>`;
  }).join("");
  const seatHint = t(sh.mode === "full" ? "seats_full" : "seats_share", { n: maxSeats });
  const alert = sh.error
    ? `<div class="alert" role="alert">${esc(sh.error)}${sh.suggestions.length ? `<div class="suggest"><span class="small" style="width:100%">${t("try_instead")}</span>
        ${sh.suggestions.map((id) => `<button type="button" class="btn btn-sm" data-suggest="${esc(id)}">${esc(id)} <span class="muted">${esc(roomName(id))}</span></button>`).join("")}</div>` : ""}</div>`
    : "";

  $("sh-form").innerHTML = `
    <div class="block"><span class="field-label">${t("when")}</span>${when}</div>
    <div class="block"><span class="field-label">${t("how_long")}</span><div class="durations">${durations}</div></div>
    <div class="block day-limit">
      <div class="row"><span class="muted">${esc(t("your_hours_on", { day: dayLabel(sh.date, true) }))}</span><b>${usedHours(sh.date) + thisHours} / ${DAY_LIMIT} h</b></div>
      <div class="bar"><i style="width:${((usedHours(sh.date) + thisHours) / DAY_LIMIT) * 100}%"></i></div>
    </div>
    <div class="block"><span class="field-label">${t("who_join")}</span>
      <div class="modes">
        <button type="button" class="mode ${sh.mode === "full" ? "active" : ""}" data-mode="full" ${r.length && !canFull ? "disabled" : ""}>
          ${ic("lock")}<b>${t("private_room")}</b><span>${t("private_room_sub")}</span></button>
        <button type="button" class="mode ${sh.mode === "partial" ? "active" : ""}" data-mode="partial">
          ${ic("users")}<b>${t("open_share")}</b><span>${t("open_share_sub")}</span></button>
      </div>
      ${r.length && !canFull ? `<p class="hint">${t("only_share")}</p>` : ""}
    </div>
    <div class="block people-row">
      <div><span class="field-label" style="margin:0">${t("how_many")}</span><span class="hint" style="margin:0">${esc(seatHint)}</span></div>
      <div class="stepper"><button type="button" data-seats="-1" ${sh.seats <= 1 ? "disabled" : ""} aria-label="${t("fewer")}">−</button>
        <output>${sh.seats}</output><button type="button" data-seats="1" ${sh.seats >= maxSeats ? "disabled" : ""} aria-label="${t("more")}">+</button></div>
    </div>
    <div class="block"><span class="field-label">${t("what_for")}</span><div class="purposes">${purposes}</div>
      ${sh.purpose === "custom" ? `<input class="text-input" id="custom" style="margin-top:8px" maxlength="80" placeholder="${esc(t("custom_ph"))}" value="${esc(sh.custom)}">` : ""}
    </div>
    ${alert ? `<div class="block">${alert}</div>` : ""}
    <div class="block"><button type="button" class="btn btn-primary btn-lg" data-action="book" ${canBook() ? "" : "disabled"}>
      ${sh.busy ? t("booking_busy") : r.length ? t("book_range", { a: r[0].start, b: r[r.length - 1].end }) : t("book")}</button></div>`;
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
    sh.error = t("limit_reached", { limit: DAY_LIMIT, day: dayLabel(sh.date) });
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
    notify(`booked-${b.id}`, "booked", "note_booked",
      { room: b.room_id, day: dayLabel(sh.date), t: `${hm(b.start)}–${hm(b.end)}` }, b.room_id, { toast: false });
    toast(t("booked_toast", { room: b.room_id, day: dayLabel(sh.date), a: hm(b.start), b: hm(b.end) }), { action: { label: t("my_bookings"), run: openDrawer } });
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
    if (t.dataset.action === "share") return copyRoomLink(sh.roomId);
    if (t.dataset.action === "way") return showWay(sh.roomId);
    if (t.dataset.action === "fav") return toggleFavorite(t);
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
        <span class="pill ${esc(r.status)}">${STATUS[r.status] && ["closed", "unbookable"].includes(r.status) ? STATUS[r.status] : t("n_free", { n: r.seats_free })}</span></li>`).join("")
    : `<li class="sug-empty">${t("no_match", { q: esc(q) })}</li>`;
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
      else if (input.value.trim()) api.search(input.value.trim(), 1).then((r) => (r[0] ? pick(r[0].id) : toast(t("no_room"), { error: true })));
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
  for (const b of $("modes").querySelectorAll("button")) b.classList.toggle("active", b.dataset.mode === (root.mode || "auto"));
}

function wireMenu() {
  const menu = $("menu");
  const avatar = $("avatar");
  const toggle = (open) => { menu.classList.toggle("hidden", !open); avatar.setAttribute("aria-expanded", String(open)); };
  avatar.addEventListener("click", (e) => { e.stopPropagation(); toggle(menu.classList.contains("hidden")); });
  document.addEventListener("click", (e) => { if (!menu.contains(e.target)) toggle(false); });
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

function closeDrawer({ route = true } = {}) {
  const drawer = $("mine-drawer");
  if (!drawer.open || drawer.classList.contains("closing")) return;
  if (route) leaveRoute("view");
  drawer.classList.add("closing");
  setTimeout(() => { drawer.classList.remove("closing"); drawer.close(); }, 200);
}

function wirePage() {
  $("mine-btn").addEventListener("click", openDrawer);
  const drawer = $("mine-drawer");
  drawer.addEventListener("cancel", (e) => { e.preventDefault(); closeDrawer(); });
  drawer.addEventListener("click", (e) => {
    if (e.target === drawer || e.target.closest("[data-close]")) return closeDrawer();
    const t = e.target.closest("button[data-action]");
    if (!t || t.disabled) return;
    if (t.dataset.action === "cancel") return cancelBooking(t);
    if (t.dataset.action === "rate") return rateRoom(t);
    if (t.dataset.action === "fav") return toggleFavorite(t);
    if (t.dataset.action === "open-fav") { closeDrawer({ route: false }); return openRoom(t.dataset.room, { replaceRoute: true }); }
    if (t.dataset.action === "find") { closeDrawer(); setTimeout(() => $("search-input").focus(), 220); return; }
    if (t.dataset.action === "ics") return downloadIcs(state.mine.find((x) => x.id === Number(t.dataset.id)));
    if (t.dataset.action === "add") {
      const b = state.mine.find((x) => x.id === Number(t.dataset.id));
      closeDrawer({ route: false });
      openRoom(b.room_id, { date: b.start.slice(0, 10), time: hm(b.end), hours: 1, mode: b.mode, seats: b.seats,
        purpose: b.purpose, custom: b.custom_purpose || "", replaceRoute: true });
    }
  });
}

// ---------- Page addresses ----------
// Every view has its own address, so reloads, shared links and the browser's back button land on the same view:
//   ?room=Z.1.04  a room        ?view=bookings  My bookings
//   ?building=Z   map building  ?floor=2 | all  map floor (default 1)   ?date=2026-12-01  calendar day (default today)
// Opening a room or My bookings adds a history step (Back closes it); map and day changes only update the address.
let applyingRoute = false;
const routeParams = () => new URLSearchParams(location.search);

function setRoute(changes, { push = false } = {}) {
  if (applyingRoute) return;
  const p = routeParams();
  for (const [k, v] of Object.entries(changes)) {
    if (v === null || v === undefined || v === "") p.delete(k);
    else p.set(k, v);
  }
  const qs = p.toString(), url = `${location.pathname}${qs ? `?${qs}` : ""}`;
  if (url === `${location.pathname}${location.search}`) return;
  if (push) history.pushState({ pushed: true }, "", url);
  else history.replaceState(history.state, "", url);
}

// A view closed by its own button: step back if we opened it (so Back doesn't reopen it), else drop it from the address.
function leaveRoute(key) {
  if (applyingRoute || !routeParams().has(key)) return;
  if (history.state?.pushed) history.back();
  else setRoute({ [key]: null });
}

function applyMapRoute() {
  const p = routeParams(), view = state.view;
  if (!view?.setBuilding) return;
  const b = p.get("building");
  if (b && view.buildings?.().some((x) => x.id === b)) view.setBuilding(b);
  else if (!b) view.setBuilding(null);
  const f = p.get("floor");
  if (f === "all") view.setFloor(null);
  else if (f !== null && /^\d+$/.test(f)) view.setFloor(Number(f));
}

function applyRoute() {
  applyingRoute = true;
  try {
    const p = routeParams();
    const date = p.get("date");
    if (!date || !state.picker.setDate(date)) state.picker.setDate(dateKey(new Date()));
    const room = p.get("room");
    if (room && state.rooms.some((r) => r.id === room)) {
      if (state.sheet?.roomId !== room) openRoom(room);
    } else {
      const sheetOpen = Boolean(state.sheet);   // a closing sheet restores the map from the address itself
      if (sheetOpen) closeSheet({ route: false });
      if (document.querySelector(".map-info.on")) { hideRoomInfo(); state.view?.showAll(); }
      if (!sheetOpen) applyMapRoute();
    }
    const drawer = $("mine-drawer");
    if (p.get("view") === "bookings") { if (!drawer.open) openDrawer(); }
    else if (drawer.open) closeDrawer({ route: false });
  } finally {
    applyingRoute = false;
  }
}

// ---------- Share link, calendar file, shortcuts ----------

async function copyRoomLink(id) {
  const url = `${location.origin}${location.pathname}?room=${encodeURIComponent(id)}`;
  try {
    await navigator.clipboard.writeText(url);
    toast(t("link_copied"));
  } catch {
    prompt(t("copy_link"), url);   // clipboard blocked (http, old browser): let the user copy it
  }
}

// One booking as an .ics file (local time), so it can be added to any calendar app.
function downloadIcs(b) {
  if (!b) return;
  const stamp = (iso) => iso.replace(/[-:]/g, "").slice(0, 15) + (iso.length <= 16 ? "00" : "");
  const room = `${b.room_id} ${roomName(b.room_id)}`.trim();
  const ics = ["BEGIN:VCALENDAR", "VERSION:2.0", "PRODID:-//Campus Booking System//AAU//EN", "BEGIN:VEVENT",
    `UID:roomv-${b.id}@aau`, `DTSTAMP:${new Date().toISOString().replace(/[-:]/g, "").slice(0, 15)}Z`,
    `DTSTART:${stamp(b.start)}`, `DTEND:${stamp(b.end)}`, `SUMMARY:${purposeText(b)} · ${room}`,
    `LOCATION:${room}, Universität Klagenfurt`, "END:VEVENT", "END:VCALENDAR"].join("\r\n");
  const a = document.createElement("a");
  a.href = URL.createObjectURL(new Blob([ics], { type: "text/calendar" }));
  a.download = `room-v-${b.room_id}-${b.start.slice(0, 10)}.ics`;
  a.click();
  setTimeout(() => URL.revokeObjectURL(a.href), 1000);
}

function wireHelp() {
  const help = $("help-dialog");
  help.addEventListener("click", (e) => { if (e.target === help || e.target.closest("[data-close]")) help.close(); });
  $("footer").addEventListener("click", (e) => { if (e.target.closest('[data-action="shortcuts"]')) help.showModal(); });
  document.addEventListener("keydown", (e) => {
    const typing = ["INPUT", "TEXTAREA"].includes(document.activeElement?.tagName);
    if (typing || e.ctrlKey || e.metaKey || e.altKey) return;
    if (e.key === "?") { e.preventDefault(); help.open ? help.close() : help.showModal(); }
    else if ((e.key === "l" || e.key === "L") && !document.querySelector("dialog[open]")) setLang(lang === "de" ? "en" : "de");
  });
}

// ---------- Room assistant ----------

function wireAssistant() {
  const input = $("ask-input");
  const panel = $("assistant");
  const fab = $("ask-fab");
  const setOpen = (open) => {
    panel.hidden = !open;
    fab.classList.toggle("on", open);
    fab.setAttribute("aria-expanded", String(open));
    if (open) setTimeout(() => input.focus(), 60);
  };
  fab.addEventListener("click", () => setOpen(panel.hidden));
  panel.querySelector(".ask-x").addEventListener("click", () => setOpen(false));
  document.addEventListener("keydown", (e) => { if (e.key === "Escape" && !panel.hidden) setOpen(false); });
  $("ask-examples").innerHTML = ["ask_ex1", "ask_ex2"]
    .map((k) => `<button class="ask-example" type="button">${esc(t(k))}</button>`).join("");
  $("ask-examples").addEventListener("click", (e) => {
    const b = e.target.closest(".ask-example");
    if (!b) return;
    input.value = b.textContent;
    ask(input.value);
  });
  $("ask-form").addEventListener("submit", (e) => {
    e.preventDefault();
    if (input.value.trim()) ask(input.value.trim());
  });
  $("ask-answer").addEventListener("click", (e) => {
    const b = e.target.closest("button[data-ask-room]");
    if (!b) return;
    const u = state.asked;
    setOpen(false);
    openRoom(b.dataset.askRoom, { date: u.date, time: u.time, hours: u.hours, mode: u.mode, seats: u.seats, purpose: u.purpose });
  });
}

let askSeq = 0;   // only the newest question's answer is shown

async function ask(text) {
  const box = $("ask-answer");
  const seq = ++askSeq;
  box.hidden = false;
  box.innerHTML = `<p class="muted">${t("ask_thinking")}</p>`;
  let res;
  try {
    res = await api.ask(text);
  } catch (err) {
    if (seq !== askSeq) return;
    if (!handleAuth(err)) box.innerHTML = `<p class="ask-problem">${esc(err.message)}</p>`;
    return;
  }
  if (seq !== askSeq) return;
  const u = res.understood;
  state.asked = u;
  const end = new Date(`${u.date}T${u.time}`);
  end.setMinutes(end.getMinutes() + u.hours * 60);
  const p = PURPOSE[u.purpose];
  const chips = [
    `${ic("cal")} ${esc(dayLabel(u.date))} · ${u.time}–${pad(end.getHours())}:${pad(end.getMinutes())}`,
    `${ic("users")} ${esc(people(u.seats))}`,
    `${ic(p?.icon ?? "pencil")} ${esc(p?.label ?? u.purpose)}`,
    esc(t(u.mode === "full" ? "private_tag" : "share_tag")),
    u.building ? `${ic("building")} ${esc(t("ask_building", { b: u.building }))}` : "",
  ].filter(Boolean).map((c) => `<span class="ask-chip">${c}</span>`).join("");
  const problem = res.problem ? `<p class="ask-problem">${esc(t(`ask_${res.problem === "none_free" ? "none" : res.problem}`))}</p>` : "";
  const rooms = res.rooms.map((r) => `
    <div class="ask-room">
      <div><b>${esc(r.label || r.id)}</b> <span class="muted small">${esc(r.label ? `${r.id} · ${r.name}` : r.name)}</span></div>
      <div class="ask-reasons">
        <span class="noise-${esc(r.noise_class)}">${ic("sound")} ${esc(t(`noise_${r.noise_class}`))} · ${r.noise_db.toFixed(0)} dB</span>
        <span>${ic("seat")} ${esc(t("ask_seats_free", { n: r.seats_free }))}</span>
        ${r.rating ? `<span>${ic("star")} ${r.rating}</span>` : ""}
        ${r.board && r.live ? `<span class="live-badge">${esc(t("ask_live"))}</span>` : ""}
      </div>
      <button class="btn btn-primary btn-sm" type="button" data-ask-room="${esc(r.id)}">${t("ask_book")}</button>
    </div>`).join("");
  box.innerHTML = `<div class="ask-understood"><span class="muted small">${t("ask_understood")}:</span>${chips}</div>${problem}
    ${rooms ? `<div class="muted small ask-best">${t("ask_best")}</div><div class="ask-rooms">${rooms}</div>` : ""}`;
}

// ---------- Smart alerts: what the sensors mean for your own bookings ----------

// Notification center (bell next to My bookings): reminders and sensor alerts for your own bookings. Stored per
// user in this browser, so every notice comes once, also across reloads; texts are kept as keys, so they follow the
// language switch.
const NOTES_MAX = 40;
const notesKey = () => `roomv-notes-${state.user?.email ?? ""}`;

function loadNotes() {
  try { state.notes = JSON.parse(localStorage.getItem(notesKey()) || "[]"); } catch { state.notes = []; }
}

function saveNotes() {
  try { localStorage.setItem(notesKey(), JSON.stringify(state.notes.slice(0, NOTES_MAX))); } catch { /* private mode */ }
}

function agoText(at) {
  const m = Math.round((Date.now() - at) / 60000);
  return m < 1 ? t("just_now") : m < 60 ? t("min_ago", { m }) : t("h_ago", { h: Math.round(m / 60) });
}

function renderNotes() {
  const unread = state.notes.filter((n) => !n.read).length;
  const count = $("notes-count");
  count.textContent = unread;
  count.classList.toggle("hidden", !unread);
  $("notes-list").innerHTML = state.notes.length
    ? state.notes.map((n) => `<li class="note ${n.read ? "" : "unread"} ${esc(n.kind)}" data-room="${esc(n.room ?? "")}">
        <span class="note-icon">${ic(NOTE_ICON[n.kind] ?? "bell")}</span>
        <span><span class="note-text">${esc(t(n.msg, n.vars))}</span><span class="muted small">${esc(agoText(n.at))}</span></span></li>`).join("")
    : `<li class="note-empty muted small">${t("notes_empty")}</li>`;
}

const NOTE_ICON = { soon: "clock", ending: "hourglass", over: "done", ghost: "ghost", released: "ban", loud: "sound", left: "bag",
  booked: "check", cancelled: "trash" };

/** Adds a notification once (by key). `at` = when it happened (default now); only fresh ones (< 15 min) pop up. */
function notify(key, kind, msg, vars, room, { toast: show = true, at = Date.now() } = {}) {
  if (state.notes.some((n) => n.key === key)) return;
  at = Math.min(at, Date.now());
  show = show && Date.now() - at < 15 * 60000;
  state.notes.unshift({ key, kind, msg, vars, room, at, read: false });
  state.notes.sort((a, b) => b.at - a.at);
  state.notes.length = Math.min(state.notes.length, NOTES_MAX);
  saveNotes();
  renderNotes();
  if (show) toast(t(msg, vars), { ms: 10000, action: room ? { label: t("alert_open"), run: () => openRoom(room) } : undefined });
}

function wireNotes() {
  const panel = $("notes-panel");
  const btn = $("notes-btn");
  const toggle = (open) => { panel.classList.toggle("hidden", !open); btn.setAttribute("aria-expanded", String(open)); };
  btn.addEventListener("click", (e) => { e.stopPropagation(); toggle(panel.classList.contains("hidden")); renderNotes(); });
  document.addEventListener("click", (e) => { if (!panel.contains(e.target) && e.target !== btn) toggle(false); });
  $("notes-read").addEventListener("click", () => { for (const n of state.notes) n.read = true; saveNotes(); renderNotes(); });
  $("notes-list").addEventListener("click", (e) => {
    const li = e.target.closest(".note");
    if (!li) return;
    const n = state.notes.find((x) => x.room === li.dataset.room && !x.read) ?? state.notes.find((x) => x.room === li.dataset.room);
    if (n) { n.read = true; saveNotes(); renderNotes(); }
    if (li.dataset.room) { toggle(false); openRoom(li.dataset.room); }
  });
  loadNotes();
  renderNotes();
}

const minutesKey = (ms) => { const d = new Date(Date.now() + ms); return `${dateKey(d)}T${pad(d.getHours())}:${pad(d.getMinutes())}`; };

function checkAlerts() {
  const now = nowKey();
  const in10 = minutesKey(10 * 60000);
  const ago15 = minutesKey(-15 * 60000);
  const ago12h = minutesKey(-12 * 3600000);
  for (const b of state.mine) {
    const room = state.rooms.find((r) => r.id === b.room_id);
    const name = room ? room.label || room.id : b.room_id;
    const when = `${hm(b.start)}–${hm(b.end)}`;
    if (b.status === "released" && b.end > ago12h) {
      notify(`released-${b.id}`, "released", "note_released", { room: name, t: when }, b.room_id,
        { at: b.ghost_release_at ? new Date(b.ghost_release_at).getTime() : new Date(b.start).getTime() });
      continue;
    }
    if (b.status !== "active") continue;
    if (b.start > now && b.start <= in10) notify(`soon-${b.id}`, "soon", "note_soon", { room: name, t: hm(b.start) }, b.room_id);
    if (b.start <= now && b.end > now) {
      if (b.end <= in10) {
        notify(`ending-${b.id}`, "ending", "note_ending", { room: name, m: minutesUntil(`${b.end}`), t: hm(b.end) }, b.room_id);
      }
      if (b.ghost_release_at) notify(`ghost-${b.id}`, "ghost", "note_ghost", { room: name, t: hm(b.ghost_release_at) }, b.room_id);
      if (room && PURPOSE[b.purpose]?.noise === "quiet" && room.board && room.live && room.noise_class !== "quiet") {
        notify(`loud-${b.id}`, "loud", "alert_loud", { room: name, db: room.noise_db.toFixed(0) }, b.room_id);
      }
    } else if (b.end <= now && b.end > ago15) {
      notify(`over-${b.id}`, "over", "note_over", { room: name, t: hm(b.end) }, b.room_id, { at: new Date(b.end).getTime() });
      if (room?.left_items > 0) notify(`left-${b.id}`, "left", "alert_left", { room: name }, b.room_id);
    }
  }
}

// A soft glow on the page background follows the pointer (CSS hides it on touch screens and reduced motion).
function wireCursorGlow() {
  const glow = $("cursor-glow");
  let frame = 0;
  document.addEventListener("pointermove", (e) => {
    if (e.pointerType !== "mouse" || frame) return;
    frame = requestAnimationFrame(() => {
      frame = 0;
      glow.style.setProperty("--gx", `${e.clientX}px`);
      glow.style.setProperty("--gy", `${e.clientY}px`);
      glow.classList.add("on");
    });
  });
  document.documentElement.addEventListener("pointerleave", () => glow.classList.remove("on"));
}

async function main() {
  document.title = t("title_app");
  applyStatic();
  langSwitch($("top-lang"));
  langSwitch($("menu-lang"));
  renderFooter($("footer"));
  wireHelp();
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
  wireCursorGlow();
  wireSearch();
  wireSheet();
  wirePage();
  wireNotes();
  wireAssistant();
  state.picker = createPicker($("picker"), {
    onOpen: (id, opts) => openRoom(id, opts),
    onError: (err) => { if (!handleAuth(err)) toast(err.message, { error: true }); },
    onDate: (key) => setRoute({ date: key === dateKey(new Date()) ? null : key }),
  });
  await Promise.all([refreshRooms(), refreshMine()]);
  await createView();
  // The address decides what is open (a shared link, a reload); Back and Forward go through it too.
  applyRoute();
  addEventListener("popstate", applyRoute);
  // Refresh just the visible sensor panel between full campus polls.
  let sensorPending = false;
  setInterval(async () => {
    const sh = state.sheet;
    if (sensorPending || !sh?.room?.board || sh.busy || document.hidden) return;
    sensorPending = true;
    try {
      const room = await api.room(sh.roomId);
      if (state.sheet === sh) {
        sh.room = room;
        renderSheetHead();
      }
    } catch (err) {
      handleAuth(err);
    } finally {
      sensorPending = false;
    }
  }, 500);
  let tick = 0;
  let polling = false;   // a slow answer must not pile up requests
  setInterval(async () => {
    if (polling || document.hidden) return;
    polling = true;
    try {
      await Promise.all([refreshRooms(), refreshMine()]);
      checkAlerts();
      if (state.sheet && !state.sheet.busy) await loadSheetData();
      if (++tick % SLOT_REFRESH_TICKS === 0) state.picker.refresh();
    } finally {
      polling = false;
    }
  }, POLL_MS);
}

main();
