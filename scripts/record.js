#!/usr/bin/env node
// Record the rigged character frame by frame, on a virtual clock.
//
// The page's clock (performance.now, requestAnimationFrame) is replaced before the app loads, so
// every frame is simulated exactly 1/fps apart however long the capture of it takes -- smooth
// even under a slow software renderer. Each frame is the rig canvas itself at the PSD's size,
// transparent where nothing is drawn; compose.sh puts a background behind it.
//
//   node record.js --url 'http://127.0.0.1:8765/?obs=1&model=chisato.psd' --out frames \
//     --seconds 12 --fps 60 --pointer
const fs = require('fs');
const path = require('path');
const puppeteer = require('puppeteer-core');

function arg(name, def) {
  const i = process.argv.indexOf('--' + name);
  if (i < 0) return def;
  const v = process.argv[i + 1];
  return v === undefined || v.startsWith('--') ? true : v;
}
const URL = arg('url');
const OUT = arg('out', 'frames');
const SECONDS = Number(arg('seconds', 12));
const FPS = Number(arg('fps', 60));
const WARMUP = Number(arg('warmup', 2));          // seconds simulated before the first frame
const POINTER = !!arg('pointer', false);
const CHROME = arg('chrome', process.env.CHROME);
const SEED = Number(arg('seed', 7));

// A pointer that drifts around the face the way a hand on a mouse does in the demo: slow loops,
// a pause, a glance to each side. x, y in -1..1 across the canvas; t in seconds.
function pointerAt(t) {
  const x = 0.55 * Math.sin(t * 0.9) + 0.18 * Math.sin(t * 2.3 + 1.1);
  const y = -0.25 + 0.28 * Math.sin(t * 0.7 + 0.6) + 0.08 * Math.sin(t * 1.9);
  return { x, y };
}

(async () => {
  fs.mkdirSync(OUT, { recursive: true });
  const browser = await puppeteer.launch({
    executablePath: CHROME,
    headless: true,
    args: ['--no-sandbox', '--enable-webgl', '--ignore-gpu-blocklist', '--use-angle=swiftshader',
      '--enable-unsafe-swiftshader', '--window-size=1400,1400'],
  });
  const page = await browser.newPage();
  await page.setViewport({ width: 1400, height: 1400, deviceScaleFactor: 1 });
  page.on('console', m => { if (m.type() === 'error') console.error('[page]', m.text()); });
  page.on('pageerror', e => console.error('[pageerror]', e.message));

  await page.evaluateOnNewDocument((seed) => {
    // Deterministic Math.random so a take can be redone exactly (mulberry32).
    let s = seed >>> 0;
    Math.random = () => { s = (s + 0x6D2B79F5) >>> 0; let t = s; t = Math.imul(t ^ (t >>> 15), t | 1);
      t ^= t + Math.imul(t ^ (t >>> 7), t | 61); return ((t ^ (t >>> 14)) >>> 0) / 4294967296; };
    let vnow = 0;
    let queue = [];
    performance.now = () => vnow;
    window.requestAnimationFrame = cb => { queue.push(cb); return queue.length; };
    window.cancelAnimationFrame = () => {};
    window.__vstep = (ms) => { vnow += ms; const q = queue; queue = []; q.forEach(cb => cb(vnow)); };
  }, SEED);

  await page.goto(URL, { waitUntil: 'load' });
  // Let the PSD parse and rig (worker + timers run on the real clock) while frames tick over.
  const t0 = Date.now();
  for (;;) {
    const n = await page.evaluate(() => { window.__vstep(16); return window.Anime25D ? window.Anime25D.state().layers : 0; });
    if (n > 0) break;
    if (Date.now() - t0 > 180000) throw new Error('model did not load');
    await new Promise(r => setTimeout(r, 50));
  }
  const info = await page.evaluate(() => {
    const cv = document.getElementById('cv');
    return { w: cv.width, h: cv.height, state: window.Anime25D.state() };
  });
  console.log('loaded', info.w + 'x' + info.h, 'layers', info.state.layers);

  if (POINTER) {
    await page.evaluate(() => {
      const el = document.getElementById('tgMouse');
      if (el && !el.classList.contains('on')) el.click();
    });
  }
  const movePointer = async (t) => {
    if (!POINTER) return;
    const p = pointerAt(t);
    await page.evaluate((px, py) => {
      const cv = document.getElementById('cv');
      const r = cv.getBoundingClientRect();
      cv.dispatchEvent(new MouseEvent('mousemove', { clientX: r.left + (px + 1) / 2 * r.width,
        clientY: r.top + (py + 1) / 2 * r.height, bubbles: true }));
    }, p.x, p.y);
  };

  const dt = 1000 / FPS;
  for (let i = 0; i < WARMUP * FPS; i++) { await movePointer(i / FPS); await page.evaluate(ms => window.__vstep(ms), dt); }

  const total = Math.round(SECONDS * FPS);
  for (let i = 0; i < total; i++) {
    await movePointer(WARMUP + i / FPS);
    // Step and read the canvas in one task: the drawing buffer is not preserved past it.
    const data = await page.evaluate(ms => { window.__vstep(ms); return document.getElementById('cv').toDataURL('image/png'); }, dt);
    fs.writeFileSync(path.join(OUT, `f_${String(i).padStart(5, '0')}.png`), Buffer.from(data.split(',')[1], 'base64'));
    if (i % FPS === 0) console.log('frame', i, '/', total);
  }
  await browser.close();
  console.log('done', total, 'frames');
})().catch(e => { console.error(e); process.exit(1); });
