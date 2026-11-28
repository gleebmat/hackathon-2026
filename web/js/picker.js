// Room picker under the map: an always-visible calendar (day, start time, duration), then at most 3 room cards
// with arrows. Without a picked time, a card says whether the room has free time left that day;
// with one, it shows the exact status for that range. Data: /api/rooms (live state) and
// /api/rooms/{id}/availability (30-min slots), per docs/PLAN.md.
import * as api from "./api.js";
import { t, locale, people } from "./i18n.js";

const OPEN_HOUR = 0;
const SLOTS = 48;
const HORIZON_DAYS = 14;
const DURATIONS = [0.5, 1, 2, 3, 4];
const NOISE = ["quiet", "moderate", "loud"];
const RANK = { free: 0, partial: 1, full: 5, closed: 9 };

const pad = (n) => String(n).padStart(2, "0");
const dateKey = (d) => `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`;
const slotTime = (i) => `${pad(OPEN_HOUR + Math.floor(i / 2))}:${i % 2 ? "30" : "00"}`;
const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => `&#${c.charCodeAt(0)};`);
const todayKey = () => dateKey(new Date());

function currentSlot() {
  const now = new Date();
  return (now.getHours() - OPEN_HOUR) * 2 + (now.getMinutes() >= 30 ? 1 : 0);
}

function dayName(key) {
  if (key === todayKey()) return t("today_lower");
  return new Date(`${key}T12:00`).toLocaleDateString(locale, { weekday: "short", day: "numeric", month: "short" });
}

export function createPicker(root, { onOpen, onError }) {
  const $ = (sel) => root.querySelector(sel);
  const state = {
    date: todayKey(), start: null, hours: 1, page: 0,
    rooms: [], slots: {}, month: null, loadedFor: null,
  };
  const perPage = () => (matchMedia("(max-width: 760px)").matches ? 1 : 3);
  const touch = matchMedia("(hover: none)").matches;
  const rangeText = () => `${slotTime(state.start)}–${slotTime(state.start + state.hours * 2)}`;

  // ---------- Data ----------

  async function loadSlots() {
    const key = state.date;
    const cal = await api.calendar(key).catch(() => null);  // every room's slots for the day in one call
    if (key !== state.date || !cal) return;
    state.slots = {};
    for (const r of state.rooms) if (r.status !== "closed" && cal.rooms[r.id]) state.slots[r.id] = cal.rooms[r.id].slots;
    state.loadedFor = key;
  }

  function expected(slots) {
    const worst = slots.map((s) => s.noise).filter(Boolean).sort((a, b) => NOISE.indexOf(b) - NOISE.indexOf(a))[0];
    return { cls: worst || "quiet", text: t(`exp_${worst || "quiet"}`) };
  }

  function cardState(room) {
    const slots = state.slots[room.id];
    if (room.status === "closed" || !slots) return { kind: "closed", main: t("st_closed"), sub: t("closed_on", { day: dayName(state.date) }), noise: null };
    const isToday = state.date === todayKey();
    const live = { cls: room.noise_class, text: t("db_now", { n: Math.round(room.noise_db) }), live: room.live };

    if (state.start === null) {
      const open = slots.filter((s) => s.status === "free" || s.status === "partial");
      const hours = open.length / 2;
      const noise = isToday ? live : expected(open);
      if (!hours) return { kind: "full", main: t("booked_out"), sub: t("no_time_left", { day: dayName(state.date) }), noise, hours };
      return { kind: "free", main: t(isToday ? "free_today" : "free_time"), sub: t("h_bookable", { h: hours }), noise, hours };
    }

    const range = slots.slice(state.start, state.start + state.hours * 2);
    const now = currentSlot();
    const includesNow = isToday && state.start <= now && now < state.start + state.hours * 2;
    const noise = includesNow ? live : expected(range);
    if (range.length < state.hours * 2 || range.some((s) => !["free", "partial"].includes(s.status))) {
      return { kind: "full", main: t("not_available"), sub: rangeText(), noise };
    }
    const left = Math.min(...range.map((s) => s.seats_free));
    const taken = room.capacity - left;
    if (taken > 0) {
      return { kind: "partial", main: t("shared_n", { who: people(taken) }), sub: t("seats_left", { n: left }), noise, people: taken };
    }
    return { kind: "free", main: t("st_free"), sub: t("all_seats", { n: room.capacity }), noise };
  }

  function sortedCards() {
    return state.rooms.map((room) => ({ room, st: cardState(room) })).sort((a, b) =>
      RANK[a.st.kind] - RANK[b.st.kind]
      || (b.st.hours ?? 0) - (a.st.hours ?? 0)
      || (a.st.people ?? 0) - (b.st.people ?? 0)
      || (b.room.rating ?? 0) - (a.room.rating ?? 0)
      || a.room.id.localeCompare(b.room.id));
  }

  // ---------- Rendering ----------

  function cardHtml({ room, st }) {
    const rating = room.rating != null
      ? `<div class="line"><span>${t("rating")}</span><span class="stars"><s style="--p:${(room.rating / 5) * 100}%">★★★★★</s>${room.rating.toFixed(1)}${room.votes ? ` <small>(${room.votes})</small>` : ""}</span></div>`
      : "";
    const noise = st.noise
      ? `<div class="line"><span>${t("noise")}</span><span class="noise ${esc(st.noise.cls)}"><span class="bars"><b></b><b></b><b></b></span>${esc(st.noise.text)}${st.noise.live ? ` <em class="live">LIVE</em>` : ""}</span></div>`
      : "";
    const action = st.kind === "closed" ? "" : `<span class="book">${st.kind === "full" ? t("other_times") : t("book")}</span>`;
    return `<button type="button" class="pick ${st.kind === "full" || st.kind === "closed" ? "dim" : ""}" data-room="${esc(room.id)}">
      <div class="pick-top"><div class="pick-id">${esc(room.id)}</div><div class="pick-name">${esc(room.name)}</div></div>
      <div class="pick-status"><div class="st-main ${st.kind}"><i></i>${esc(st.main)}</div><div class="st-sub">${esc(st.sub)}</div></div>
      <div class="pick-drawer"><div><div class="pick-drawer-in">${rating}${noise}${action}</div></div></div>
    </button>`;
  }

  function render(direction) {
    if (state.loadedFor !== state.date) {
      $(".picks").className = "picks";
      $(".picks").innerHTML = `<div class="skeleton"></div>`.repeat(perPage());
      renderHeading();
      return;
    }
    const list = sortedCards();
    const n = perPage();
    const pages = Math.max(1, Math.ceil(list.length / n));
    state.page = Math.min(state.page, pages - 1);
    const cards = $(".picks");
    const open = cards.querySelector(".pick.open")?.dataset.room;
    const draw = () => {
      const html = list.slice(state.page * n, state.page * n + n).map(cardHtml);
      const current = [...cards.children];
      const sameRooms = !direction && current.length === html.length
        && html.every((h, i) => h.includes(`data-room="${current[i].dataset.room}"`));
      if (sameRooms) {
        // Live refresh: swap only the cards whose content changed, so an open card stays open.
        html.forEach((h, i) => {
          if (current[i].dataset.html !== h) {
            const tmp = document.createElement("div");
            tmp.innerHTML = h;
            const fresh = tmp.firstElementChild;
            fresh.dataset.html = h;
            if (current[i].classList.contains("open")) fresh.classList.add("open");
            current[i].replaceWith(fresh);
          }
        });
      } else {
        cards.className = `picks${direction ? ` in-${direction}` : ""}`;
        cards.innerHTML = html.join("");
        [...cards.children].forEach((c, i) => { c.dataset.html = html[i]; });
        if (open) cards.querySelector(`[data-room="${CSS.escape(open)}"]`)?.classList.add("open");
        if (direction) setTimeout(() => { cards.className = "picks"; }, 650);
      }
      $(".prev").disabled = state.page === 0;
      $(".next").disabled = state.page >= pages - 1;
      $(".dots").innerHTML = Array.from({ length: pages }, (_, i) => `<i class="${i === state.page ? "on" : ""}"></i>`).join("");
    };
    if (direction && cards.children.length) {
      cards.className = `picks out-${direction}`;
      setTimeout(draw, 190);
    } else {
      draw();
    }
    renderHeading();
  }

  function renderHeading() {
    const day = dayName(state.date);
    const today = state.date === todayKey();
    $(".picker-title").textContent = state.start === null
      ? (today ? t("rooms_today") : t("rooms_on", { day }))
      : t(today ? "rooms_today_range" : "rooms_on_range", { day, range: rangeText() });
  }

  // ---------- Calendar (always visible, between the map and the cards) ----------

  function minStart(key) {
    return key === todayKey() ? Math.max(0, currentSlot()) : 0;
  }

  function defaultStart(key) {
    return key === todayKey() ? Math.min(SLOTS - 1, minStart(key)) : 24;
  }

  function fitTime(next) {
    if (next.start === null) return next;
    const min = minStart(next.date);
    if (min >= SLOTS) return { ...next, start: null };
    const start = Math.min(Math.max(next.start, min), SLOTS - 1);
    const fits = DURATIONS.filter((h) => start + h * 2 <= SLOTS);
    return { ...next, start, hours: fits.includes(next.hours) ? next.hours : fits.at(-1) };
  }

  function drawCalendar() {
    const m = state.month;
    const today = new Date();
    today.setHours(0, 0, 0, 0);
    const last = new Date(today);
    last.setDate(last.getDate() + HORIZON_DAYS);
    $(".m-title").textContent = m.toLocaleDateString(locale, { month: "long", year: "numeric" });
    $(".m-prev").disabled = m <= new Date(today.getFullYear(), today.getMonth(), 1);
    $(".m-next").disabled = new Date(m.getFullYear(), m.getMonth() + 1, 1) > last;
    const lead = (new Date(m.getFullYear(), m.getMonth(), 1).getDay() + 6) % 7;
    const days = new Date(m.getFullYear(), m.getMonth() + 1, 0).getDate();
    let html = t("weekdays").split(",").map((x) => `<span class="dow">${x}</span>`).join("") + "<span></span>".repeat(lead);
    for (let i = 1; i <= days; i++) {
      const dt = new Date(m.getFullYear(), m.getMonth(), i);
      const key = dateKey(dt);
      const ok = dt >= today && dt <= last;
      html += `<button type="button" class="day ${key === todayKey() ? "today" : ""} ${key === state.date ? "sel" : ""}" data-day="${key}" ${ok ? "" : "disabled"}>${i}</button>`;
    }
    $(".m-grid").innerHTML = html;

    const any = state.start === null;
    const dayOver = minStart(state.date) >= SLOTS;
    const shown = any ? defaultStart(state.date) : state.start;
    $(".anytime").classList.toggle("on", any);
    $(".cal-time").classList.toggle("is-any", any);
    $(".t-out").textContent = dayOver ? t("t_closed") : slotTime(Math.min(shown, SLOTS - 1));
    $(".t-dn").disabled = dayOver || (!any && state.start <= minStart(state.date));
    $(".t-up").disabled = dayOver || (!any && state.start >= SLOTS - 1);
    $(".durs").innerHTML = DURATIONS.map((h) => `<button type="button" class="${!any && h === state.hours ? "on" : ""}" data-h="${h}"
      ${dayOver || shown + h * 2 > SLOTS ? "disabled" : ""}>${h === 0.5 ? "30m" : `${h}h`}</button>`).join("");
  }

  async function choose(next, direction) {
    const fitted = fitTime({ date: state.date, start: state.start, hours: state.hours, ...next });
    const dateChanged = fitted.date !== state.date;
    Object.assign(state, fitted, { page: 0 });
    drawCalendar();
    if (dateChanged) render();
    if (dateChanged || state.loadedFor !== state.date) {
      try {
        await loadSlots();
      } catch (err) {
        onError(err);
      }
    }
    render(direction);
  }

  $(".cal").addEventListener("click", (e) => {
    const t = e.target.closest("button");
    if (!t || t.disabled) return;
    const from = state.start ?? defaultStart(state.date);
    if (t.dataset.day) {
      if (t.dataset.day !== state.date) choose({ date: t.dataset.day }, t.dataset.day > state.date ? "left" : "right");
    } else if (t.classList.contains("m-prev") || t.classList.contains("m-next")) {
      state.month.setMonth(state.month.getMonth() + (t.classList.contains("m-next") ? 1 : -1));
      drawCalendar();
    } else if (t.classList.contains("anytime")) {
      choose({ start: null });
    } else if (t.classList.contains("t-dn")) {
      choose({ start: state.start === null ? from : from - 1 });
    } else if (t.classList.contains("t-up")) {
      choose({ start: state.start === null ? from : from + 1 });
    } else if (t.dataset.h) {
      choose({ start: from, hours: Number(t.dataset.h) });
    }
  });
  $(".prev").addEventListener("click", () => { state.page--; render("right"); });
  $(".next").addEventListener("click", () => { state.page++; render("left"); });
  $(".picks").addEventListener("click", (e) => {
    const card = e.target.closest(".pick");
    if (!card) return;
    if (touch && !card.classList.contains("open")) {
      for (const c of root.querySelectorAll(".pick.open")) c.classList.remove("open");
      card.classList.add("open");
      return;
    }
    onOpen(card.dataset.room, state.start === null
      ? { date: state.date }
      : { date: state.date, time: slotTime(state.start), hours: state.hours });
  });
  addEventListener("resize", () => render());
  state.month = new Date();
  state.month.setDate(1);
  drawCalendar();

  return {
    /** New live room list from /api/rooms (every few seconds): redraw cards without animation. */
    async setRooms(rooms) {
      const first = !state.rooms.length;
      state.rooms = rooms;
      if (first || state.loadedFor !== state.date) {
        try {
          await loadSlots();
        } catch (err) {
          onError(err);
        }
      }
      render();
    },
    /** Reload slots (after a booking or cancel) and redraw. */
    async refresh() {
      try {
        await loadSlots();
      } catch (err) {
        onError(err);
      }
      render();
    },
  };
}
