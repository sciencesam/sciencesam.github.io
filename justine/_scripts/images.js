// Convert downloaded originals to WebP: 1600px long edge (q78, auto-oriented, metadata stripped),
// plus a 480px thumb for featured images. Idempotent: skips outputs that already exist.
// Usage: node images.js <mirror_dir> <out_dir>
const sharp = require('sharp'); const fs = require('fs'); const path = require('path');
const [,, M, OUT] = process.argv;
const manifest = JSON.parse(fs.readFileSync(path.join(M, 'manifest.json')));
let before = 0, after = 0, done = 0, missing = [], failed = [];
async function one(m) {
  const ext = path.extname(m.base);
  const src = path.join(M, 'img-src', m.local.slice(4).replace(/\.(webp|gif)$/, '') + ext);
  if (!fs.existsSync(src)) { missing.push(m.base); return; }
  before += fs.statSync(src).size;
  const out = path.join(OUT, m.local);
  fs.mkdirSync(path.dirname(out), { recursive: true });
  try {
    if (!fs.existsSync(out))
      await sharp(src).rotate().resize({ width: 1600, height: 1600, fit: 'inside', withoutEnlargement: true }).webp({ quality: 78 }).toFile(out);
    after += fs.statSync(out).size;
    if (m.thumb) {
      const t = path.join(OUT, m.thumb);
      if (!fs.existsSync(t))
        await sharp(src).rotate().resize({ width: 480, height: 480, fit: 'inside', withoutEnlargement: true }).webp({ quality: 78 }).toFile(t);
      after += fs.statSync(t).size;
    }
    done++;
  } catch (e) { failed.push(m.base + ': ' + e.message); }
}
(async () => {
  const q = manifest.slice(); const N = 6;
  await Promise.all(Array.from({ length: N }, async () => { while (q.length) await one(q.shift()); }));
  const mb = b => (b / 1048576).toFixed(1) + ' MB';
  console.log(`converted ${done}/${manifest.length}; missing source ${missing.length}; failed ${failed.length}`);
  console.log(`size before (1600px JPEG originals as downloaded): ${mb(before)}  after (WebP + thumbs): ${mb(after)}`);
  if (missing.length) console.log('missing:', missing.slice(0, 20).join('\n  '));
  if (failed.length) console.log('failed:', failed.slice(0, 20).join('\n  '));
})();
