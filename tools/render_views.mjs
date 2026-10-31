// Genera capturas PNG del visor 3D para la documentación (docs/img/).
// Uso:  node tools/render_views.mjs            (requiere playwright + chromium)
// Levanta un servidor estático en el repo, abre visor/index.html y saca 4 vistas + despiece.
import { createServer } from "node:http";
import { readFile, mkdir } from "node:fs/promises";
import { extname, join, resolve } from "node:path";
import { createRequire } from "node:module";

const require = createRequire(import.meta.url);
const { chromium } = require("playwright");
const ROOT = resolve(new URL("..", import.meta.url).pathname);
const OUT = join(ROOT, "docs/img");
const TYPES = { ".html": "text/html", ".js": "text/javascript", ".json": "application/json",
  ".glb": "model/gltf-binary", ".png": "image/png", ".css": "text/css" };

const server = createServer(async (req, res) => {
  try {
    const p = join(ROOT, decodeURIComponent(new URL(req.url, "http://x").pathname));
    const data = await readFile(p);
    res.writeHead(200, { "content-type": TYPES[extname(p)] || "application/octet-stream" });
    res.end(data);
  } catch {
    res.writeHead(404);
    res.end();
  }
}).listen(0);
const port = server.address().port;
await mkdir(OUT, { recursive: true });

const browser = await chromium.launch({ args: ["--use-gl=swiftshader", "--enable-unsafe-swiftshader"] });
const page = await browser.newPage({ viewport: { width: 1400, height: 900 } });
page.on("console", (m) => m.type() === "error" && console.error("[page]", m.text()));
await page.goto(`http://localhost:${port}/visor/index.html`);
await page.waitForSelector("#loading", { state: "detached", timeout: 120000 });

const shots = [["iso", 0], ["front", 0], ["side", 0], ["top", 0], ["iso", 70]];
for (const [v, ex] of shots) {
  await page.evaluate(([v, ex]) => {
    window.__setView(v);
    const r = document.getElementById("explode");
    r.value = ex;
    r.dispatchEvent(new Event("input"));
  }, [v, ex]);
  await page.waitForTimeout(800);
  const name = ex ? `vista_${v}_despiece.png` : `vista_${v}.png`;
  await page.locator("main").screenshot({ path: join(OUT, name) });
  console.log("ok", name);
}
await browser.close();
server.close();
