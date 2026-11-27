// Temporary mock data, shaped exactly like the contracts in docs/PLAN.md.
// api.js uses it only while the backend or building_v.json is not available.
// Delete this file once both are live.

const SLOTS = [
  { n: "01", x: -20, z: -14, w: 18, d: 10 },
  { n: "02", x: 0, z: -14, w: 18, d: 10 },
  { n: "03", x: 20, z: -14, w: 18, d: 10 },
  { n: "04", x: 22.5, z: 0, w: 13, d: 14 },
  { n: "05", x: 20, z: 14, w: 18, d: 10 },
  { n: "06", x: 0, z: 14, w: 18, d: 10 },
  { n: "07", x: -20, z: 14, w: 18, d: 10 },
  { n: "08", x: -22.5, z: 0, w: 13, d: 14 },
];
const NAMES = ["Seminar room", "Study room", "Lecture room", "Group room",
  "Computer lab", "Project room", "Meeting room", "Learning space"];
const CAPACITIES = [24, 8, 40, 10, 20, 12, 12, 30];

const rooms = [];
for (let floor = 0; floor <= 2; floor++) {
  SLOTS.forEach((s, i) => {
    const id = floor === 1 && s.n === "07" ? "V.1.07a" : `V.${floor}.${s.n}`;
    rooms.push({ id, floor, x: s.x, z: s.z, w: s.w, d: s.d,
      capacity: CAPACITIES[i], name: NAMES[i] });
  });
}

export const building = {
  building: "V", outer: { w: 60, d: 40 }, courtyard: { w: 30, d: 16 }, floor_height: 4, rooms,
};

function at(hour) {
  const t = new Date();
  t.setHours(hour, 0, 0, 0);
  return t.toISOString();
}

// Bookings for today: [room_id, startHour, hours, mode, seats, purpose]
let nextId = 1;
const bookings = [
  ["V.1.07a", 8, 2, "partial", 4, "quiet_study"],
  ["V.1.07a", 17, 4, "partial", 4, "quiet_study"],
  ["V.0.02", 16, 3, "partial", 3, "group_study"],
  ["V.0.03", 9, 2, "full", 40, "event"],
  ["V.0.05", 15, 5, "partial", 6, "gaming"],
  ["V.1.01", 14, 6, "full", 24, "meeting"],
  ["V.1.04", 18, 2, "partial", 4, "board_games"],
  ["V.2.03", 13, 8, "full", 40, "event"],
  ["V.2.06", 17, 3, "partial", 5, "quiet_study"],
  ["V.2.08", 16, 4, "partial", 10, "group_study"],
].map(([room_id, h, hours, mode, seats, purpose]) => ({
  id: nextId++, room_id, start: at(h), end: at(h + hours), mode, seats, purpose, custom_purpose: null,
}));

const PURPOSE_NOISE = { quiet_study: 36, group_study: 50, meeting: 48, custom: 48,
  gaming: 68, board_games: 63, event: 72 };
const noise = {};

function noiseClass(db) {
  return db < 40 ? "quiet" : db <= 60 ? "moderate" : "loud";
}

function current(roomId) {
  const now = Date.now();
  return bookings.filter((b) => b.room_id === roomId
    && Date.parse(b.start) <= now && now < Date.parse(b.end));
}

function roomState(room) {
  const active = current(room.id);
  const status = active.some((b) => b.mode === "full") ? "full" : active.length ? "partial" : "free";
  const target = active.length ? Math.max(...active.map((b) => PURPOSE_NOISE[b.purpose])) : 33;
  // Random walk around the target, so the UI visibly updates like live data.
  const prev = noise[room.id] ?? target;
  noise[room.id] = Math.round((prev + (target - prev) * 0.3 + (Math.random() - 0.5) * 4) * 10) / 10;
  const seats = active.reduce((sum, b) => sum + b.seats, 0);
  const people = status === "full" ? Math.round(room.capacity * 0.6) : seats;
  return {
    id: room.id, floor: room.floor, capacity: room.capacity, name: room.name, status,
    noise_db: noise[room.id], noise_class: noiseClass(noise[room.id]), people,
    live: room.id === "V.1.07a",
    bookings_now: active.map(({ mode, purpose, seats: s, end }) => ({ mode, purpose, seats: s, end })),
  };
}

export function getRooms() {
  return rooms.map(roomState);
}

export function getRoom(id) {
  const room = rooms.find((r) => r.id === id);
  if (!room) return null;
  return { ...roomState(room), bookings_today: bookings.filter((b) => b.room_id === id) };
}
