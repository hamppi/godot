import { createRequire } from 'node:module';
import fs from 'node:fs/promises';
import path from 'node:path';
import crypto from 'node:crypto';
import { execFileSync } from 'node:child_process';
import os from 'node:os';
const root = path.resolve(process.env.GODOT_GAMES_ROOT || path.join(os.homedir(), 'HTML5Games/GodotGames'));
const require = createRequire(path.join(root, '../GameHub/package.json'));
const { chromium } = require('playwright');
const out = path.resolve(process.env.QA_OUTPUT || path.join(root, 'qa-artifacts'));
await fs.mkdir(out, { recursive: true });
const hub = process.env.HUB || 'http://localhost:7777';
const catalog = await (await fetch(`${hub}/api/games`)).json();
const games = catalog.games.filter(g => g.root.startsWith('Godot')).map(g => ({ ...g, group: path.basename(path.dirname(g.folder)) }));
if (games.length !== Number(process.env.EXPECTED_GAMES || 6)) throw new Error(`Unexpected Godot catalog size: ${games.length}`);
const profile = await fs.mkdtemp(path.join(os.tmpdir(), 'godot-browser-'));
execFileSync('open', ['-na', 'Google Chrome', '--args', '--remote-debugging-port=0', `--user-data-dir=${profile}`, '--no-first-run', '--no-default-browser-check']);
let port;
for (let attempt = 0; attempt < 80; attempt++) {
  try { port = (await fs.readFile(path.join(profile, 'DevToolsActivePort'), 'utf8')).split('\n')[0]; break; }
  catch { await new Promise(r => setTimeout(r, 250)); }
}
if (!port) throw new Error('Regular Chrome did not expose its debugging port');
const remoteBrowser = await chromium.connectOverCDP(`http://127.0.0.1:${port}`);
const browser = remoteBrowser.contexts()[0];
const report = [];
try {
  if (!process.env.NO_HUB_SHOT) {
  const hubPage = await browser.newPage({ viewport: { width: 1440, height: 1000 } });
  await hubPage.goto(hub);
  await hubPage.getByRole('heading', { name: /Godot/ }).first().waitFor();
  await hubPage.getByRole('heading', { name: /Godot/ }).first().scrollIntoViewIfNeeded();
  await hubPage.screenshot({ path: path.join(out, 'hub-godot.png') });
  await hubPage.close();
  }
  for (const game of games.filter(g => !process.env.ONLY || g.group.endsWith(process.env.ONLY))) {
    const page = await browser.newPage({ viewport: { width: 1280, height: 720 } });
    await page.setViewportSize({ width: 1280, height: 720 });
    const errors = [], messages = [], failed = [];
    page.on('pageerror', e => errors.push(e.message));
    page.on('console', m => {
      if (m.type() === 'error' || /ERROR:|SCRIPT ERROR/.test(m.text())) errors.push(m.text());
      messages.push(m.text());
    });
    page.on('response', r => { if (r.status() >= 400) failed.push(`${r.status()} ${r.url()}`); });
    await page.addInitScript(() => {
      window.__qaGL = { draws: 0 };
      window.__qaFrameTimes = [];
      let lastFrame = 0;
      const raf = window.requestAnimationFrame;
      window.requestAnimationFrame = callback => raf.call(window, timestamp => {
        if (timestamp > lastFrame) {
          if (lastFrame) window.__qaFrameTimes.push(timestamp - lastFrame);
          lastFrame = timestamp;
        }
        callback(timestamp);
      });
      const original = HTMLCanvasElement.prototype.getContext;
      HTMLCanvasElement.prototype.getContext = function (...args) {
        const gl = original.apply(this, args);
        if (gl && String(args[0]).startsWith('webgl') && !gl.__qaWrapped) {
          gl.__qaWrapped = true;
          const ext = gl.getExtension('WEBGL_debug_renderer_info');
          window.__qaGL.renderer = ext ? gl.getParameter(ext.UNMASKED_RENDERER_WEBGL) : gl.getParameter(gl.RENDERER);
          for (const method of ['drawArrays', 'drawElements', 'drawArraysInstanced', 'drawElementsInstanced']) {
            const fn = gl[method];
            if (fn) gl[method] = function (...params) { window.__qaGL.draws++; return fn.apply(this, params); };
          }
        }
        return gl;
      };
    });
    await page.goto(`${hub}/play/${encodeURIComponent(game.id)}/build/`);
    await page.bringToFront();
    if (process.platform === 'darwin') execFileSync('osascript', ['-e', 'tell application "Google Chrome" to activate']);
    await page.waitForFunction(() => window.__qaGL?.draws > 100, { timeout: 60000 });
    await page.waitForTimeout(2000);
    await page.evaluate(() => { window.__qaFrameTimes = []; });
    const before = await page.screenshot({ path: path.join(out, `${game.group}-before.png`) });
    await page.locator('canvas').click({ position: { x: 640, y: 360 } });
    if (game.group.endsWith('Match-3')) {
      await page.mouse.move(402, 122);
      await page.mouse.down(); await page.mouse.move(470, 122, { steps: 8 }); await page.mouse.up();
      await page.waitForTimeout(700);
      await page.mouse.move(538, 190);
      await page.mouse.down(); await page.mouse.move(538, 258, { steps: 8 }); await page.mouse.up();
    } else if (game.group.endsWith('City-Builder')) {
      await page.mouse.click(640, 400);
      await page.keyboard.press('KeyE');
      await page.mouse.click(750, 420);
      await page.keyboard.press('F1');
      await page.waitForTimeout(1500);
      await page.keyboard.press('Delete');
      await page.keyboard.press('F2');
      await page.waitForTimeout(1000);
      await page.reload();
      await page.bringToFront();
      await page.waitForFunction(() => window.__qaGL?.draws > 100, { timeout: 60000 });
      await page.waitForTimeout(1500);
      await page.keyboard.press('F2');
      await page.waitForTimeout(800);
      await page.screenshot({ path: path.join(out, `${game.group}-restored.png`) });
      await page.keyboard.press('F3');
    } else if (!game.group.endsWith('Basic-Scene')) {
      await page.keyboard.down('KeyW');
      if (game.group.endsWith('3D-Platformer')) await page.keyboard.press('Space');
      if (game.group.endsWith('FPS')) { await page.mouse.move(700, 320, { steps: 8 }); await page.mouse.click(700, 320); await page.keyboard.press('KeyE'); }
      await page.waitForTimeout(1400);
      await page.keyboard.up('KeyW');
    }
    await page.waitForTimeout(1500);
    const after = await page.screenshot({ path: path.join(out, `${game.group}-after.png`) });
    const changed = crypto.createHash('sha256').update(before).digest('hex') !== crypto.createHash('sha256').update(after).digest('hex');
    const gpu = await page.evaluate(() => {
      const times = window.__qaFrameTimes.filter(t => t > 0 && t < 1000).sort((a, b) => a - b);
      return { ...window.__qaGL, focused: document.hasFocus(), visibility: document.visibilityState,
        pointerLocked: !!document.pointerLockElement, rafSamples: times.length,
        rafMedianMs: times.length ? times[Math.floor(times.length / 2)] : null,
        rafP95Ms: times.length ? times[Math.min(times.length - 1, Math.floor(times.length * .95))] : null };
    });
    const transfers = await page.evaluate(() => performance.getEntriesByType('resource')
      .filter(r => /\.(wasm|pck|js)(\?|$)/.test(r.name))
      .map(r => ({ name: new URL(r.name).pathname.split('/').at(-1), encoded: r.encodedBodySize, decoded: r.decodedBodySize })));
    const limitations = game.group.endsWith('FPS') ? errors.filter(e => e === 'The root document of this element is not valid for pointer lock.') : [];
    const blockingErrors = errors.filter(e => !limitations.includes(e));
    report.push({ name: game.name, id: game.id, gpu, changed, errors, blockingErrors, limitations, failed, transfers, saveLoad: messages.filter(m => /Saving map|Loading map/.test(m)) });
    await fs.writeFile(path.join(out, 'report.json'), JSON.stringify(report, null, 2));
    console.log(JSON.stringify(report.at(-1)));
    await page.close();
  }
} finally {
  const session = await remoteBrowser.newBrowserCDPSession();
  await session.send('Browser.close');
  await remoteBrowser.close();
}
if (report.some(g => g.blockingErrors.length || g.failed.length || !g.gpu.draws)) process.exitCode = 1;
