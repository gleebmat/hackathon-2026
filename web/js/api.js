// The only place the UI talks to the backend. Every function returns data shaped like
// the API contract in docs/PLAN.md, from the real backend or from mock-data.js.
//
// Data source: add ?data=mock or ?data=api to the URL to force one. By default ("auto")
// the real API is used when GET /api/rooms answers, otherwise the mock.
import * as mock from "./mock-data.js";

const forced = new URLSearchParams(location.search).get("data");
let source = forced === "mock" || forced === "api" ? forced : null;

async function getJson(path) {
  const res = await fetch(path, { credentials: "same-origin" });
  if (!res.ok) throw new Error(`${path}: HTTP ${res.status}`);
  return res.json();
}

export async function detectSource() {
  if (!source) {
    try {
      await getJson("/api/rooms");
      source = "api";
    } catch {
      source = "mock";
    }
  }
  return source;
}

// building_v.json comes from gemini, independently of the backend, so it falls back on its own.
export async function getBuilding() {
  try {
    return { data: await getJson("data/building_v.json"), mock: false };
  } catch {
    return { data: mock.building, mock: true };
  }
}

export async function getRooms() {
  return source === "api" ? getJson("/api/rooms") : mock.getRooms();
}

export async function getRoom(id) {
  if (source === "api") return getJson(`/api/rooms/${encodeURIComponent(id)}`);
  const room = mock.getRoom(id);
  if (!room) throw new Error(`Unknown room ${id}`);
  return room;
}
