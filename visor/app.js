// Visor 3D del Carpincho. Carga el ensamble GLB y el catálogo parts.json que genera cad/build.py.
import * as THREE from "three";
import { OrbitControls } from "three/addons/controls/OrbitControls.js";
import { GLTFLoader } from "three/addons/loaders/GLTFLoader.js";

const BASE = new URL("../cad/out/", import.meta.url);
const REPO_RAW = ""; // vacío = rutas relativas (sirve en GitHub Pages y en local)

const el = (id) => document.getElementById(id);
const view = el("view");
const renderer = new THREE.WebGLRenderer({ antialias: true, preserveDrawingBuffer: true });
renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
view.appendChild(renderer.domElement);

const scene = new THREE.Scene();
const camera = new THREE.PerspectiveCamera(35, 1, 1, 20000);
camera.up.set(0, 0, 1); // Z arriba, igual que el robot (REP-103)
const controls = new OrbitControls(camera, renderer.domElement);
controls.enableDamping = true;

scene.add(new THREE.HemisphereLight(0xffffff, 0x445066, 1.6));
const sun = new THREE.DirectionalLight(0xffffff, 2.2);
sun.position.set(600, 400, 900);
scene.add(sun);
const fill = new THREE.DirectionalLight(0xffffff, 0.8);
fill.position.set(-500, -600, 300);
scene.add(fill);

const grid = new THREE.GridHelper(1600, 32, 0x8890a0, 0xb8bec8);
grid.rotation.x = Math.PI / 2;
grid.material.transparent = true;
grid.material.opacity = 0.35;
scene.add(grid);

function cssVar(name) {
  return getComputedStyle(document.documentElement).getPropertyValue(name).trim();
}
function applyBg() {
  scene.background = new THREE.Color(cssVar("--canvas") || "#e9ecf1");
}
applyBg();
el("theme").addEventListener("click", () => {
  const root = document.documentElement;
  const dark = root.dataset.theme
    ? root.dataset.theme === "dark"
    : matchMedia("(prefers-color-scheme: dark)").matches;
  root.dataset.theme = dark ? "light" : "dark";
  applyBg();
});
matchMedia("(prefers-color-scheme: dark)").addEventListener("change", applyBg);

function resize() {
  const w = view.clientWidth, h = view.clientHeight;
  renderer.setSize(w, h, false);
  camera.aspect = w / Math.max(h, 1);
  camera.updateProjectionMatrix();
}
new ResizeObserver(resize).observe(view);

// ------------------------------------------------------------------ datos
let catalog = null;
const nodes = new Map();      // nombre de nodo -> {obj, code, base: Vector3, dir: Vector3}
const byCode = new Map();     // código -> entrada del catálogo
let modelCenter = new THREE.Vector3();
let modelSize = 1;
let selected = null;
const hiddenGroups = new Set();

const EXPLODE_GROUP = {   // cuánto se separa cada subsistema (multiplica la dirección radial)
  chasis: 0.6, traccion: 1.0, flipper: 1.3, brazo: 1.1, electronica: 1.6, sensores: 1.4, referencia: 1.2,
};

function codeOfNode(name) {
  // "CH-01_L" -> "CH-01", "REF-buck_5v" -> "REF-buck_5v", "CH-08_L_2" -> "CH-08"
  if (byCode.has(name)) return name;
  const parts = name.split("_");
  for (let i = parts.length - 1; i > 0; i--) {
    const c = parts.slice(0, i).join("_");
    if (byCode.has(c)) return c;
  }
  return name;
}

async function load() {
  catalog = await (await fetch(new URL("parts.json", BASE))).json();
  catalog.parts.forEach((p) => byCode.set(p.code, p));
  renderStats();
  renderGroups();
  renderList("");

  const gltf = await new GLTFLoader().loadAsync(new URL("carpincho.glb", BASE).href);
  const root = gltf.scene;
  // el GLB de CadQuery puede venir en metros: normalizamos a mm
  // glTF es "Y arriba": lo volvemos a Z arriba (convención del robot)
  root.rotation.x = Math.PI / 2;
  const bb0 = new THREE.Box3().setFromObject(root);
  const size0 = bb0.getSize(new THREE.Vector3()).length();
  if (size0 < 50) root.scale.setScalar(1000);
  scene.add(root);
  root.updateMatrixWorld(true);

  const bb = new THREE.Box3().setFromObject(root);
  bb.getCenter(modelCenter);
  modelSize = bb.getSize(new THREE.Vector3()).length();

  root.traverse((o) => {
    if (!o.name || o === root || !o.parent) return;
    const code = codeOfNode(o.name);
    if (!byCode.has(code) || nodes.has(o.name)) return;
    // solo el nodo de instancia más alto (los hijos se mueven con él)
    for (let a = o.parent; a; a = a.parent) if (a.userData.__inst) return;
    o.userData.__inst = true;
    // usar el nodo de más arriba que tenga el nombre de la instancia
    const box = new THREE.Box3().setFromObject(o);
    if (box.isEmpty()) return;
    const c = box.getCenter(new THREE.Vector3());
    const dir = c.clone().sub(modelCenter);
    dir.z = Math.max(dir.z, 0) * 1.2 + 40;
    nodes.set(o.name, { obj: o, code, worldBase: o.getWorldPosition(new THREE.Vector3()), dir });
    o.traverse((m) => {
      if (m.isMesh) {
        m.userData.instance = o.name;
        m.material = m.material.clone();
        m.material.metalness = 0.1;
        m.material.roughness = 0.65;
      }
    });
  });
  el("loading").remove();
  setView("iso");
}

// ------------------------------------------------------------------ UI
function renderStats() {
  const s = catalog.summary;
  const items = [
    [`${Math.round(s.length_tracks)} mm`, "largo (orugas)"],
    [`${Math.round(s.length_flippers_ext)} mm`, "largo con flippers"],
    [`${Math.round(s.width_total)} mm`, "ancho total"],
    [`${catalog.mass_total_kg} kg`, "masa estimada"],
    [`${catalog.parts.filter((p) => !p.bought).length}`, "piezas a fabricar"],
    [`z = ${Math.round(catalog.cg_mm[2])} mm`, "centro de gravedad"],
  ];
  el("stats").innerHTML = items.map(([b, t]) => `<div class="stat"><b>${b}</b><span>${t}</span></div>`).join("");
}

function renderGroups() {
  el("groups").innerHTML = Object.entries(catalog.groups)
    .map(([k, v]) => `<label class="grp"><input type="checkbox" data-g="${k}" checked> ${v}</label>`)
    .join("");
  el("groups").querySelectorAll("input").forEach((cb) =>
    cb.addEventListener("change", () => {
      cb.checked ? hiddenGroups.delete(cb.dataset.g) : hiddenGroups.add(cb.dataset.g);
      applyVisibility();
    }),
  );
}

function renderList(q) {
  q = q.toLowerCase();
  const list = catalog.parts.filter(
    (p) => !q || p.code.toLowerCase().includes(q) || p.name.toLowerCase().includes(q),
  );
  el("parts").innerHTML = list
    .map(
      (p) => `<li data-code="${p.code}" class="${selected === p.code ? "on" : ""}">
      <code>${p.code}</code><span>${p.name}</span><span class="q">×${p.qty}</span></li>`,
    )
    .join("");
  el("parts").querySelectorAll("li").forEach((li) => li.addEventListener("click", () => select(li.dataset.code)));
}
el("q").addEventListener("input", (e) => renderList(e.target.value));

function applyVisibility() {
  for (const n of nodes.values()) {
    const p = byCode.get(n.code);
    n.obj.visible = !hiddenGroups.has(p.group);
  }
}

function select(code) {
  selected = selected === code ? null : code;
  for (const n of nodes.values()) {
    n.obj.traverse((m) => {
      if (!m.isMesh) return;
      m.material.emissive = new THREE.Color(n.code === selected ? 0x1f6feb : 0x000000);
      m.material.emissiveIntensity = n.code === selected ? 0.55 : 0;
    });
  }
  renderList(el("q").value);
  const card = el("card");
  if (!selected) return card.classList.remove("show");
  const p = byCode.get(selected);
  const links = Object.entries(p.files || {})
    .map(([k, v]) => `<a href="${REPO_RAW}../${v}" download>${k.toUpperCase()}</a>`)
    .join("");
  card.innerHTML = `<h3>${p.code} · ${p.name}</h3><dl>
    <dt>Subsistema</dt><dd>${p.group_name}</dd>
    <dt>Cantidad</dt><dd>${p.qty}</dd>
    <dt>Material</dt><dd>${p.material}</dd>
    <dt>Fabricación</dt><dd>${p.process}</dd>
    <dt>Medidas</dt><dd>${p.bbox_mm.join(" × ")} mm</dd>
    <dt>Masa</dt><dd>${p.mass_g_unit} g c/u</dd>
    ${p.notes ? `<dt>Notas</dt><dd>${p.notes}</dd>` : ""}
    ${links ? `<dt>Archivos</dt><dd>${links}</dd>` : ""}
  </dl>`;
  card.classList.add("show");
}

// clic en el modelo
const ray = new THREE.Raycaster();
const ptr = new THREE.Vector2();
let down = null;
renderer.domElement.addEventListener("pointerdown", (e) => (down = [e.clientX, e.clientY]));
renderer.domElement.addEventListener("pointerup", (e) => {
  if (!down || Math.hypot(e.clientX - down[0], e.clientY - down[1]) > 4) return;
  const r = renderer.domElement.getBoundingClientRect();
  ptr.set(((e.clientX - r.left) / r.width) * 2 - 1, -((e.clientY - r.top) / r.height) * 2 + 1);
  ray.setFromCamera(ptr, camera);
  const hit = ray.intersectObjects(scene.children, true).find((h) => h.object.visible && h.object.userData.instance);
  if (hit) select(nodes.get(hit.object.userData.instance).code);
});

el("explode").addEventListener("input", (e) => {
  const f = Number(e.target.value) / 100;
  for (const n of nodes.values()) {
    const g = EXPLODE_GROUP[byCode.get(n.code).group] ?? 1;
    const target = n.worldBase.clone().addScaledVector(n.dir, f * g * 1.2);
    n.obj.position.copy(n.obj.parent.worldToLocal(target));
  }
});

function setView(v) {
  const d = modelSize * 1.25;
  const c = modelCenter;
  const pos = {
    iso: [c.x + d * 0.75, c.y - d * 0.85, c.z + d * 0.6],
    front: [c.x + d * 1.2, c.y, c.z + d * 0.1],
    side: [c.x, c.y - d * 1.2, c.z + d * 0.1],
    top: [c.x, c.y - 0.001, c.z + d * 1.3],
  }[v];
  camera.position.set(...pos);
  controls.target.copy(c);
  controls.update();
  document.querySelectorAll("[data-view]").forEach((b) => b.classList.toggle("primary", b.dataset.view === v));
}
document.querySelectorAll("[data-view]").forEach((b) => b.addEventListener("click", () => setView(b.dataset.view)));

(function loop() {
  controls.update();
  renderer.render(scene, camera);
  requestAnimationFrame(loop);
})();

load().catch((err) => {
  el("loading").textContent = "No se pudo cargar el modelo: " + err.message +
    " — abrí el visor con un servidor (ver visor/README.md).";
  console.error(err);
});
window.__setView = setView; // usado por tools/render_views.py para capturas
