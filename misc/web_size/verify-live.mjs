// Verify real HTTP encoding and decoded bytes through the live Hub, without a browser.
import http from 'node:http';
import { brotliDecompressSync } from 'node:zlib';
import { createHash } from 'node:crypto';
import fs from 'node:fs';
import path from 'node:path';
import os from 'node:os';
const root = path.resolve(process.env.GODOT_GAMES_ROOT || (process.platform === 'win32' ? 'D:/HTML5Games/GodotGames' : path.join(os.homedir(), 'HTML5Games/GodotGames')));
const hub = new URL(process.env.HUB || 'http://localhost:7777');
const data = await (await fetch(new URL('/api/games', hub))).json();
const games = data.games.filter(g => g.root === 'Godot');
if (games.length !== 6) throw new Error(`Expected 6 live Godot builds, found ${games.length}`);
for (const game of games) {
  const project = path.join(root, path.basename(path.dirname(game.folder)));
  const manifest = JSON.parse(fs.readFileSync(path.join(project, 'web-templates/manifest.json')));
  const result = await new Promise((resolve, reject) => {
    const req = http.get({ hostname: '127.0.0.1', port: hub.port || 80,
      path: `/play/${game.id}/build/index.wasm`,
      headers: { Host: `${game.host}.localhost:${hub.port || 80}`, 'Accept-Encoding': 'br, gzip' } }, res => {
      const chunks = [];
      res.on('data', c => chunks.push(c));
      res.on('error', reject);
      res.on('end', () => resolve({ status: res.statusCode, headers: res.headers, body: Buffer.concat(chunks) }));
    });
    req.on('error', reject);
  });
  if (result.status !== 200 || result.headers['content-encoding'] !== 'br' || result.headers['content-type'] !== 'application/wasm')
    throw new Error(`${game.id}: bad HTTP metadata ${JSON.stringify(result.headers)}`);
  const decoded = brotliDecompressSync(result.body);
  if (decoded.length !== manifest.wasm_bytes || createHash('sha256').update(decoded).digest('hex') !== manifest.wasm_sha256)
    throw new Error(`${game.id}: WASM byte mismatch`);
  if (Number(result.headers['content-length']) !== result.body.length) throw new Error('Encoded length mismatch');
  console.log(JSON.stringify({ game: game.name, encoding: 'br', transferred: result.body.length, decoded: decoded.length, sha256: manifest.wasm_sha256 }));
}
