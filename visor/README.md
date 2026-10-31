# Visor 3D

Visor web del ensamble (three.js, sin instalación). Carga `cad/out/carpincho.glb` y `cad/out/parts.json`.

- **Local**: desde la raíz del repo, `python -m http.server 8000` → <http://localhost:8000/visor/>
  (abrir `index.html` con doble clic no funciona: el navegador bloquea la carga de archivos locales).
- **GitHub Pages**: Settings → Pages → *Deploy from a branch* → `main` / `(root)`. Queda en
  `https://<usuario>.github.io/urubotsrescue/visor/`.

Funciones: despiece con un deslizador, mostrar u ocultar subsistemas, buscar piezas, clic en una pieza para ver
su ficha (material, proceso, masa, notas) y descargar el STL, STEP o DXF.
