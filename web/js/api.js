// The only place the UI talks to the backend (contract: docs/PLAN.md, "API").
// The session is a cookie set by /api/login, so no token is stored here.
// Every failed call throws an ApiError with the backend's {error, suggestions} (error translated to German if chosen).
import { tError, tRoom } from "./i18n.js";

export class ApiError extends Error {
  constructor(status, body) {
    super(tError(body?.error || `Request failed (${status})`));
    this.status = status;
    this.suggestions = body?.suggestions || [];
  }
}

async function request(method, path, body) {
  let res;
  try {
    res = await fetch(path, {
      method,
      credentials: "same-origin",
      headers: body ? { "Content-Type": "application/json" } : undefined,
      body: body ? JSON.stringify(body) : undefined,
    });
  } catch {
    throw new ApiError(0, { error: "Can't reach the server. Is the backend running?" });
  }
  const data = await res.json().catch(() => null);
  if (!res.ok) throw new ApiError(res.status, data);
  return data;
}

const q = (params) => new URLSearchParams(params).toString();

export const me = () => request("GET", "/api/me");
export const login = (email, password) => request("POST", "/api/login", { email, password });
export const register = (email, password, name) => request("POST", "/api/register", { email, password, name });
export const logout = () => request("POST", "/api/logout");

// Room names in the chosen language (the backend sends the English room types).
const named = (r) => ({ ...r, name: tRoom(r.name) });
export const rooms = () => request("GET", "/api/rooms").then((list) => list.map(named));
export const room = (id) => request("GET", `/api/rooms/${encodeURIComponent(id)}`).then(named);
export const search = (text, limit = 8) => request("GET", `/api/search?${q({ q: text, limit })}`).then((list) => list.map(named));
export const availability = (id, date) =>
  request("GET", `/api/rooms/${encodeURIComponent(id)}/availability?${q({ date })}`);

export const calendar = (date) => request("GET", `/api/calendar?${q({ date })}`);
export const rate = (id, stars) => request("POST", `/api/rooms/${encodeURIComponent(id)}/rating`, { stars });

export const myBookings = () => request("GET", "/api/bookings/mine");
export const book = (booking) => request("POST", "/api/bookings", booking);
export const cancel = (id) => request("DELETE", `/api/bookings/${id}`);

// building_v.json belongs to gemini; until it exists the UI lays the rooms out itself.
export async function building() {
  try {
    const res = await fetch("data/building_v.json");
    return res.ok ? await res.json() : null;
  } catch {
    return null;
  }
}
