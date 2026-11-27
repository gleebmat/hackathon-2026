// 3D model of AAU buildings (Three.js). API per docs/PLAN.md:
//   const b = createBuilding(containerEl, campusJson)   // campus.json ({buildings:[...]}) or a single building
//   b.setStatus(id, {status, noise_class, live}); b.focusRoom(id); b.showAll(); b.setFloor(n|null); b.onRoomClick(cb)
//   extras: b.setBuilding(id|null), b.buildings(), b.setOfficesVisible(bool), b.onRoomHover(cb), b.rooms()
//   Roofs are always see-through.
import * as THREE from "three";
import { OrbitControls } from "three/addons/controls/OrbitControls.js";
import { FontLoader } from "three/addons/loaders/FontLoader.js";
import { TextGeometry } from "three/addons/geometries/TextGeometry.js";

const FONT_URL = "https://cdn.jsdelivr.net/npm/three@0.160.0/examples/fonts/helvetiker_bold.typeface.json";

const TYPE_COLOR = { seminar: 0x2a8fb0, office: 0xd9dde3, wc: 0xa9c9e8, hall: 0xe3c99a, atrium: 0x9fd8b5, foyer: 0xf2f2f2 };
const STATUS_COLOR = { free: 0xffffff, partial: 0xf5b642, full: 0xe0483e, ghost: 0xc9b8f2, closed: 0x9aa0a6 };
const HOVER_COLOR = new THREE.Color(0x4f8dff);   // the room under the mouse blends towards this blue
const HIDDEN_BY_DEFAULT = new Set(["office", "wc", "foyer"]);  // "offices" toggle
const SLAB = 0.35;

/**
 * @param el     container element (the canvas fills it)
 * @param input  campus.json ({buildings: [...]}) or a single building
 * @param opts   {controls: true}: draws a small building / floor selector inside the container. Pass
 *               {controls: false} if the page has its own buttons (they should call setBuilding / setFloor).
 */
export function createBuilding(el, input, opts = {}) {
  const buildings = input.buildings ?? [{ id: input.building, ...input,
    blocks: [{ x: 0, z: 0, w: input.outer.w, d: input.outer.d, courtyard: input.courtyard }] }];

  // --- renderer, scene, camera ---
  const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });
  renderer.setPixelRatio(Math.min(devicePixelRatio, 2));
  renderer.shadowMap.enabled = true;
  el.appendChild(renderer.domElement);
  const scene = new THREE.Scene();
  const camera = new THREE.PerspectiveCamera(40, 1, 0.5, 2000);
  const controls = new OrbitControls(camera, renderer.domElement);
  controls.enableDamping = true;
  controls.maxPolarAngle = Math.PI * 0.49;
  controls.minDistance = 6;
  controls.maxDistance = 600;

  scene.add(new THREE.HemisphereLight(0xffffff, 0x8899aa, 1.6));
  const sun = new THREE.DirectionalLight(0xffffff, 1.5);
  sun.position.set(-60, 120, 40);
  sun.castShadow = true;
  Object.assign(sun.shadow.camera, { left: -320, right: 320, top: 320, bottom: -320, far: 900 });
  sun.shadow.mapSize.set(4096, 4096);
  scene.add(sun);

  // --- materials ---
  const slabMat = new THREE.MeshStandardMaterial({ color: 0xc9ccd1, roughness: 0.9 });
  const roofMat = new THREE.MeshStandardMaterial({ color: 0xd4dee9, roughness: 0.4, transparent: true, opacity: 0.14, depthWrite: false });  // always see-through
  const glass = new THREE.MeshStandardMaterial({ color: 0xdfe8f0, transparent: true, opacity: 0.16, depthWrite: false });

  // --- helpers ---
  const rect = (path, x, z, w, d) => {   // shape coords are (x, -z): the extrusion is rotated onto the ground
    path.moveTo(x - w / 2, -(z - d / 2)); path.lineTo(x + w / 2, -(z - d / 2));
    path.lineTo(x + w / 2, -(z + d / 2)); path.lineTo(x - w / 2, -(z + d / 2)); path.closePath();
  };
  // footprint corners of a block: explicit polygon [[x,z],...] or the rectangle x,z,w,d
  const corners = (b) => b.poly ?? [[b.x - b.w / 2, b.z - b.d / 2], [b.x + b.w / 2, b.z - b.d / 2],
                                     [b.x + b.w / 2, b.z + b.d / 2], [b.x - b.w / 2, b.z + b.d / 2]];
  const polyShape = (pts, ox = 0, oz = 0) => {
    const s = new THREE.Shape();
    pts.forEach(([x, z], i) => (i ? s.lineTo(x - ox, -(z - oz)) : s.moveTo(x - ox, -(z - oz))));
    s.closePath();
    return s;
  };
  const inside = ([px, pz], pts) => {   // point in polygon (ray casting)
    let hit = false;
    for (let i = 0, j = pts.length - 1; i < pts.length; j = i++) {
      const [xi, zi] = pts[i], [xj, zj] = pts[j];
      if ((zi > pz) !== (zj > pz) && px < ((xj - xi) * (pz - zi)) / (zj - zi) + xi) hit = !hit;
    }
    return hit;
  };
  const roomCorners = (r) => r.poly ?? [[r.x - r.w / 2, r.z - r.d / 2], [r.x + r.w / 2, r.z - r.d / 2],
                                        [r.x + r.w / 2, r.z + r.d / 2], [r.x - r.w / 2, r.z + r.d / 2]];
  // `openings`: outlines of tall rooms below that pass through this slab (only those inside this block are cut)
  const slab = (b, y, hole, mat, thick = SLAB, openings = []) => {
    const s = polyShape(corners(b));
    const cuts = openings.filter((o) => inside([o.reduce((a, p) => a + p[0], 0) / o.length,
                                                  o.reduce((a, p) => a + p[1], 0) / o.length], corners(b)));
    for (const hp of [...(b.holes ?? []), ...cuts]) {   // footprint holes (a hall around another building) + tall rooms
      const h = new THREE.Path();
      hp.forEach(([x, z], i) => (i ? h.lineTo(x, -z) : h.moveTo(x, -z)));
      h.closePath();
      s.holes.push(h);
    }
    if (hole && b.courtyard) { const h = new THREE.Path(); rect(h, b.courtyard.x + b.x, b.courtyard.z + b.z, b.courtyard.w, b.courtyard.d); s.holes.push(h); }
    const g = new THREE.ExtrudeGeometry(s, { depth: thick, bevelEnabled: false });
    g.rotateX(-Math.PI / 2);
    const m = new THREE.Mesh(g, mat);
    m.position.y = y;
    m.receiveShadow = true;
    return m;
  };
  const edges = (mesh, color = 0x445566, opacity = 0.6) => {
    mesh.add(new THREE.LineSegments(new THREE.EdgesGeometry(mesh.geometry, 20),
      new THREE.LineBasicMaterial({ color, transparent: true, opacity })));
  };
  const box = (x, z, w, d, y0, h, mat, parent, edgeOpacity = 0.35) => {
    const m = new THREE.Mesh(new THREE.BoxGeometry(w, h, d), mat);
    m.position.set(x, y0 + h / 2, z);
    edges(m, 0x8796a8, edgeOpacity);
    parent.add(m);
    return m;
  };

  // --- room labels: the room number as 3D letters standing out of the room's top face ---
  const TEXT_DEPTH = 0.25;      // how far the letters stick out (m)
  const textWhite = new THREE.MeshStandardMaterial({ color: 0xf8fafc, roughness: 0.45 });
  const textDark = new THREE.MeshStandardMaterial({ color: 0x1f2a38, roughness: 0.5 });
  // white letters by default; dark letters on white / very light rooms
  const textColor = (r) => {
    if (!r.text) return;
    const c = r.mesh.material.color, lum = 0.299 * c.r + 0.587 * c.g + 0.114 * c.b;
    r.text.material = lum > 0.82 ? textDark : textWhite;
  };
  const label3d = (font, r, h) => {
    const g = new TextGeometry(r.label ?? r.id, { font, size: 1, height: TEXT_DEPTH, curveSegments: 3, bevelEnabled: false });
    g.computeBoundingBox();
    const bb = g.boundingBox, tw = bb.max.x - bb.min.x, th = bb.max.y - bb.min.y;
    g.translate(-(bb.min.x + tw / 2), -(bb.min.y + th / 2), 0);   // centre in the plane, base at z = 0
    // text runs along `angle` (rooms on a curve) or along the longer side; size it to that side and the other one
    const along = r.angle !== undefined ? r.w : Math.max(r.w, r.d), across = r.angle !== undefined ? r.d : Math.min(r.w, r.d);
    const s = Math.min((along * 0.9) / tw, (across * 0.7) / th, 3.2 / th);  // fill ~90% of the room; letters ≤ 3.2 m
    const m = new THREE.Mesh(g, textWhite);
    m.scale.set(s, s, 1);                                          // depth stays TEXT_DEPTH
    m.rotation.x = -Math.PI / 2;                                   // lie flat, extruded upwards
    if (r.angle !== undefined) m.rotation.z = -r.angle;            // rooms along a curve: follow the room's axis
    else if (r.d > r.w) m.rotation.z = Math.PI / 2;                // run along the longer side
    m.position.y = h / 2;
    m.castShadow = false;   // no label shadows: through see-through rooms they read as a second copy
    return m;
  };

  // --- buildings ---
  const floorGroups = new Map();   // "V:1" -> Group (slab + rooms of that floor)
  const shells = [];               // per building: walls + roof
  const rooms = new Map();         // id -> {mesh, data, baseColor, badge, loud, building}
  const bounds = new THREE.Box3();
  const bBounds = new Map();       // building id -> Box3
  for (const bd of buildings) {
    const H = bd.floor_height, top = bd.floors.length * H;
    const bb = new THREE.Box3();
    bBounds.set(bd.id, bb);
    const shell = new THREE.Group();
    shells.push({ shell, building: bd });
    scene.add(shell);
    for (const f of bd.floors) {
      const g = new THREE.Group();
      for (const b of bd.blocks) {
        if ((b.open && f > 0) || (b.floors && !b.floors.includes(f))) continue;
        const openings = bd.rooms.filter((r) => r.floor < f && f < r.floor + (r.storeys ?? 1)).map(roomCorners);
        g.add(slab(b, f * H, f > 1, slabMat, SLAB, openings));   // courtyards open above floor 1 (atrium floor)
      }
      floorGroups.set(`${bd.id}:${f}`, g);
      scene.add(g);
    }
    for (const b of bd.blocks) {
      const bTop = (b.floors ?? bd.floors).length * H;     // low annexes can have fewer storeys
      const roof = slab(b, bTop, true, roofMat, 0.5);
      edges(roof, 0x2b3440, 0.7);
      shell.add(roof);
      const pts = corners(b);
      pts.forEach(([x0, z0], i) => {                       // one glass wall per footprint edge
        const [x1, z1] = pts[(i + 1) % pts.length], len = Math.hypot(x1 - x0, z1 - z0);
        if (len < 0.05) return;
        const w = box((x0 + x1) / 2, (z0 + z1) / 2, len, 0.3, 0, bTop, glass, shell);
        w.rotation.y = -Math.atan2(z1 - z0, x1 - x0);
      });
      const c = b.courtyard;
      if (c) {
        const cx = b.x + c.x, cz = b.z + c.z;
        box(cx, cz - c.d / 2, c.w, 0.3, H, top - H, glass, shell); box(cx, cz + c.d / 2, c.w, 0.3, H, top - H, glass, shell);
        box(cx - c.w / 2, cz, 0.3, c.d, H, top - H, glass, shell); box(cx + c.w / 2, cz, 0.3, c.d, H, top - H, glass, shell);
      }
      for (const [x, z] of pts) { bb.expandByPoint(new THREE.Vector3(x, 0, z)); bb.expandByPoint(new THREE.Vector3(x, bTop, z)); }
    }
    bounds.union(bb);
    for (const c of bd.connectors ?? []) {
      box(c.x, c.z, c.w, c.d, 0, c.floors.length * H, glass, shell, 0.5);
    }
    for (const r of bd.rooms) {
      const isAtrium = r.type === "atrium", h = isAtrium ? 0.25 : (r.storeys ?? 1) * H - 0.8;   // tall halls span floors
      const mat = new THREE.MeshStandardMaterial({ color: TYPE_COLOR[r.type] ?? 0xcccccc, roughness: 0.7,
        transparent: true, opacity: isAtrium ? 0.75 : 0.92 });
      let geo;
      if (r.poly) {   // non-rectangular room (curved wing, fan-shaped hall): extrude its outline, centred on x,z
        geo = new THREE.ExtrudeGeometry(polyShape(r.poly, r.x, r.z), { depth: h, bevelEnabled: false });
        geo.rotateX(-Math.PI / 2);
        geo.translate(0, -h / 2, 0);
      } else {
        geo = new THREE.BoxGeometry(Math.max(r.w - 0.25, 0.5), h, Math.max(r.d - 0.25, 0.5));
      }
      const mesh = new THREE.Mesh(geo, mat);
      mesh.position.set(r.x, r.floor * H + SLAB + h / 2, r.z);
      mesh.castShadow = true;
      mesh.userData.roomId = r.id;
      edges(mesh, 0x334455, 0.5);
      floorGroups.get(`${bd.id}:${r.floor}`).add(mesh);
      rooms.set(r.id, { mesh, data: r, baseColor: mat.color.getHex(), baseOpacity: mat.opacity, badge: null, loud: false, h, building: bd.id, text: null,
        baseY: mesh.position.y, hoverK: 0, statusColor: mat.color.clone() });
    }
  }

  // 3D labels are added once the font has loaded (the model is usable before that)
  new FontLoader().loadAsync(FONT_URL)
    .then((font) => { for (const r of rooms.values()) { r.text = label3d(font, r.data, r.h); r.mesh.add(r.text); textColor(r); } })
    .catch((e) => console.warn("Room labels unavailable:", e));

  // --- camera views: fit a box (whole campus or one building), optionally looking at one floor ---
  let anim = null;
  const flyTo = (pos, target, ms = 900) => {
    anim = { t0: performance.now(), ms, p0: camera.position.clone(), q0: controls.target.clone(), p1: pos, q1: target };
  };
  const view = (box, floorY = null) => {
    const c = box.getCenter(new THREE.Vector3()), s = box.getSize(new THREE.Vector3());
    const span = Math.max(s.x, s.z * 1.6, 30);
    if (floorY === null) return { pos: c.clone().add(new THREE.Vector3(span * 0.25, span * 0.55, span * 0.75)), target: c };
    const t = c.clone().setY(floorY);
    return { pos: t.clone().add(new THREE.Vector3(span * 0.15, span * 0.55, span * 0.5)), target: t };
  };
  const goTo = (v) => flyTo(v.pos.clone(), v.target.clone());
  const home = view(bounds);
  camera.position.copy(home.pos);
  controls.target.copy(home.target);

  // --- picking ---
  const ray = new THREE.Raycaster(), mouse = new THREE.Vector2();
  let clickCb = null, hoverCb = null, down = null;
  const pick = (ev) => {
    const r = renderer.domElement.getBoundingClientRect();
    mouse.set(((ev.clientX - r.left) / r.width) * 2 - 1, -((ev.clientY - r.top) / r.height) * 2 + 1);
    ray.setFromCamera(mouse, camera);
    const visible = [...rooms.values()].map((x) => x.mesh).filter((m) => m.visible && m.parent.visible);
    const hit = ray.intersectObjects(visible, false)[0];
    return hit ? hit.object.userData.roomId : null;
  };
  renderer.domElement.addEventListener("pointerdown", (e) => (down = [e.clientX, e.clientY]));
  renderer.domElement.addEventListener("pointerup", (e) => {
    if (down && Math.hypot(e.clientX - down[0], e.clientY - down[1]) < 5) { const id = pick(e); if (id && clickCb) clickCb(id); }
  });
  // Hover: only bookable rooms react (blue glow + small lift, animated in the render loop) and show a pointer.
  let hovered = null;
  const setHover = (id, e) => {
    const r = id && rooms.get(id);
    const next = r && r.data.bookable ? id : null;
    renderer.domElement.style.cursor = next ? "pointer" : "";
    if (next !== hovered) { hovered = next; if (hoverCb) hoverCb(next, e); }
    else if (next && hoverCb) hoverCb(next, e);   // keep the tooltip following the pointer
  };
  renderer.domElement.addEventListener("pointermove", (e) => setHover(down ? null : pick(e), e));
  renderer.domElement.addEventListener("pointerleave", (e) => setHover(null, e));
  renderer.domElement.addEventListener("pointerup", () => { down = null; });

  // --- resize + loop ---
  const resize = () => {
    renderer.setSize(el.clientWidth, el.clientHeight);
    camera.aspect = el.clientWidth / el.clientHeight;
    camera.updateProjectionMatrix();
  };
  new ResizeObserver(resize).observe(el);
  resize();
  renderer.setAnimationLoop((now) => {
    if (anim) {
      const k = Math.min(1, (now - anim.t0) / anim.ms), e = k < 0.5 ? 2 * k * k : 1 - (-2 * k + 2) ** 2 / 2;
      camera.position.lerpVectors(anim.p0, anim.p1, e);
      controls.target.lerpVectors(anim.q0, anim.q1, e);
      if (k === 1) anim = null;
    }
    const pulse = 0.35 + 0.35 * Math.sin(now / 180);
    const glow = 0.85;                                        // the selected room glows steadily (no blinking)
    for (const r of rooms.values()) {
      r.hoverK += ((r.data.id === hovered ? 1 : 0) - r.hoverK) * 0.18;   // smooth fade in and out
      if (r.hoverK < 0.002) r.hoverK = 0;
      const h = r.hoverK;
      r.mesh.material.color.copy(r.statusColor).lerp(HOVER_COLOR, 0.65 * h);
      if (r.data.id === highlight) r.mesh.material.emissive.setRGB(0.55 * glow, 0.4 * glow, 0.1 * glow);
      else r.mesh.material.emissive.setRGB((r.loud ? pulse : 0) + 0.05 * h, 0.12 * h, 0.35 * h);
      r.mesh.position.y = r.baseY + 0.45 * h;
    }
    if (halo) {
      halo.scale.setScalar(1.06);
      halo.material.opacity = 0.32;
    }
    controls.update();
    renderer.render(scene, camera);
  });

  // --- visibility state ---
  let highlight = null, halo = null, floorFilter = null, buildingFilter = null, showOffices = false;
  // buildingFilter: null (everything) or a Set of building ids (one building, or a group such as "Lakeside")
  const inView = (id) => buildingFilter === null || buildingFilter.has(id);
  const filterBox = () => {
    if (!buildingFilter) return bounds;
    const b = new THREE.Box3();
    for (const id of buildingFilter) b.union(bBounds.get(id));
    return b;
  };
  const applyVisibility = () => {
    const hl = highlight && rooms.get(highlight);
    for (const [key, g] of floorGroups) {
      const [bid, f] = key.split(":");
      // a searched room is never covered: floors above it in its own building are hidden
      const coversTarget = hl && bid === hl.building && Number(f) > hl.data.floor;
      g.visible = inView(bid) && (floorFilter === null || Number(f) <= floorFilter) && !coversTarget;
    }
    for (const { shell, building } of shells) shell.visible = inView(building.id);   // the glass case stays when floors are hidden
    for (const r of rooms.values()) {
      const isTarget = r.data.id === highlight;
      r.mesh.visible = isTarget || showOffices || !HIDDEN_BY_DEFAULT.has(r.data.type);
      r.mesh.material.opacity = hl && !isTarget ? 0.28 : r.baseOpacity;   // dim the rest while one room is highlighted
    }
  };
  const clearHighlight = () => {
    highlight = null;
    if (halo) { halo.parent.remove(halo); halo.geometry.dispose(); halo = null; }
  };
  applyVisibility();

  const badge = (text, color) => {
    const c = document.createElement("canvas");
    c.width = 256; c.height = 96;
    const x = c.getContext("2d");
    x.fillStyle = color; x.beginPath(); x.roundRect(4, 4, 248, 88, 40); x.fill();
    x.fillStyle = "#fff"; x.font = "bold 44px system-ui, sans-serif"; x.textAlign = "center"; x.textBaseline = "middle";
    x.fillText(text, 128, 50);
    const s = new THREE.Sprite(new THREE.SpriteMaterial({ map: new THREE.CanvasTexture(c), depthTest: false }));
    s.scale.set(4.2, 1.6, 1);
    return s;
  };

  const api = {
    rooms: () => [...rooms.values()].map((r) => r.data),
    setStatus(id, { status, noise_class, live } = {}) {
      const r = rooms.get(id);
      if (!r) return false;
      r.statusColor.setHex(status && r.data.bookable ? STATUS_COLOR[status] ?? r.baseColor : r.baseColor);
      r.mesh.material.color.copy(r.statusColor);
      textColor(r);
      r.loud = noise_class === "loud";
      if (live && !r.badge) {
        r.badge = badge("● LIVE", "#e0483e");
        r.badge.position.set(0, r.h / 2 + 1.4, 0);
        r.mesh.add(r.badge);
      } else if (!live && r.badge) { r.mesh.remove(r.badge); r.badge = null; }
      return true;
    },
    /** Highlight a room inside the model: it glows and pulses, the rest dims, the camera frames it with context. */
    focusRoom(id) {
      const norm = (v) => String(v ?? "").replace(/\s+/g, "").toLowerCase();   // "HS1" = "HS 1" = "hs 1"
      const key = [...rooms.keys()].find((k) => norm(k) === norm(id) || norm(rooms.get(k).data.label) === norm(id));
      if (!key) return false;
      clearHighlight();
      const r = rooms.get(key);
      if (buildingFilter && !buildingFilter.has(r.building)) buildingFilter = null;
      floorFilter = null;
      highlight = key;
      halo = new THREE.Mesh(r.mesh.geometry.clone(),
        new THREE.MeshBasicMaterial({ color: 0xffc94d, transparent: true, opacity: 0.3, depthWrite: false }));
      r.mesh.add(halo);
      applyVisibility();
      const c = r.mesh.position.clone(), s = Math.max(r.data.w, r.data.d, 14);
      flyTo(c.clone().add(new THREE.Vector3(s * 1.6, s * 2.2, s * 2.6)), c);
      return key;
    },
    buildings: () => buildings.map((bd) => ({ id: bd.id, name: bd.name, floors: bd.floors, group: bd.group ?? null })),
    /** Back to the current building (or the whole campus), all floors, nothing focused. */
    showAll() {
      clearHighlight(); floorFilter = null;
      applyVisibility();
      goTo(view(filterBox()));
    },
    /** Isolate one building (id like "V") or show all (null). Resets floor filter and focus. */
    setBuilding(id) {
      const ids = buildings.filter((bd) => bd.id === id || bd.group === id).map((bd) => bd.id);
      buildingFilter = id && ids.length ? new Set(ids) : null;
      clearHighlight(); floorFilter = null;
      applyVisibility();
      goTo(view(filterBox()));
      return buildingFilter ? id : null;
    },
    /** Show floors 0..n of the visible building(s), or all floors (null). */
    setFloor(n) {
      floorFilter = n === null || n === undefined ? null : Number(n);
      clearHighlight();
      applyVisibility();
      const box = filterBox();
      const bd = buildings.find((x) => inView(x.id)) ?? buildings[0];
      goTo(view(box, floorFilter === null ? null : floorFilter * bd.floor_height + 1));
    },
    setOfficesVisible(v) { showOffices = !!v; applyVisibility(); },
    onRoomClick(cb) { clickCb = cb; },
    onRoomHover(cb) { hoverCb = cb; },
  };
  if (opts.controls !== false) mountControls(el, api);
  return api;
}

// Built-in building / floor selector, so any page that embeds the map can switch floors without its own UI.
function mountControls(el, api) {
  if (getComputedStyle(el).position === "static") el.style.position = "relative";
  const box = document.createElement("div");
  box.style.cssText = "position:absolute;left:12px;bottom:12px;display:flex;flex-direction:column;gap:6px;" +
    "font:12px/1 system-ui,sans-serif;z-index:5;pointer-events:none";
  el.appendChild(box);
  let building = null, floor = null;
  const row = () => {
    const r = document.createElement("div");
    r.style.cssText = "display:flex;gap:3px;flex-wrap:wrap;padding:3px;border-radius:10px;" +
      "background:rgba(15,20,30,.55);pointer-events:auto";
    box.appendChild(r);
    return r;
  };
  const bRow = row(), fRow = row();
  const button = (parent, text, on, title, click) => {
    const b = document.createElement("button");
    b.textContent = text;
    b.title = title ?? "";
    b.style.cssText = "border:0;border-radius:7px;padding:6px 9px;cursor:pointer;font:inherit;" +
      (on ? "background:#2a8fb0;color:#fff" : "background:rgba(255,255,255,.9);color:#1d2430");
    b.onclick = click;
    parent.appendChild(b);
  };
  const render = () => {
    bRow.replaceChildren(); fRow.replaceChildren();
    button(bRow, "All", building === null, "All buildings", () => { building = api.setBuilding(null); floor = null; render(); });
    for (const b of api.buildings()) {
      button(bRow, b.id, building === b.id, b.name, () => { building = api.setBuilding(b.id); floor = null; render(); });
    }
    const floors = [...new Set(api.buildings().filter((b) => !building || b.id === building).flatMap((b) => b.floors))]
      .sort((a, b) => b - a);
    button(fRow, "All floors", floor === null, "Show every floor", () => { floor = null; api.setFloor(null); render(); });
    for (const f of floors) {
      button(fRow, `Floor ${f}`, floor === f, `Floor ${f} (floors above are hidden)`, () => { floor = f; api.setFloor(f); render(); });
    }
  };
  // keep the selector in sync when the page calls the API directly
  for (const [name, after] of [["setBuilding", (id) => { building = id ?? null; floor = null; }],
                               ["setFloor", (_, n) => { floor = n === null || n === undefined ? null : Number(n); }],
                               ["showAll", () => { floor = null; }],
                               ["focusRoom", (key) => { if (!key) return; floor = null; if (building && key.split(".")[0] !== building) building = null; }]]) {
    const orig = api[name];
    api[name] = (...args) => { const res = orig(...args); after(res, args[0]); render(); return res; };
  }
  render();
}
