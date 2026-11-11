'use strict';
// Senaryoları sırayla (her biri ayrı süreçte) koşar, sonunda özet tablo basar.
//   node run.js                 → scenarios/ altındaki hepsi
//   node run.js smoke-5p ...    → yalnızca adı verilenler
const { spawnSync } = require('child_process');
const fs = require('fs'), path = require('path');

const dir = path.join(__dirname, 'scenarios');
const all = fs.readdirSync(dir).filter(f => f.endsWith('.js')).map(f => f.slice(0, -3)).sort((a, b) => (a.includes('solo') ? 0 : 1) - (b.includes('solo') ? 0 : 1) || a.localeCompare(b));
const want = process.argv.slice(2).map(a => path.basename(a, '.js'));
const unknown = want.filter(w => !all.includes(w));
if (unknown.length) { console.error(`Bilinmeyen senaryo: ${unknown.join(', ')}\nMevcut: ${all.join(', ')}`); process.exit(2); }

const rows = [];
for (const name of want.length ? want : all) {
  const t0 = Date.now();
  const r = spawnSync(process.execPath, [path.join(dir, name + '.js')], { stdio: 'inherit', timeout: 15 * 60 * 1000 * (+process.env.TB_SLOW || 1), killSignal: 'SIGKILL' });
  rows.push({ name, ok: r.status === 0, note: r.status === 0 ? '' : r.error ? String(r.error.code || r.error.message) : r.signal ? 'sinyal ' + r.signal : 'çıkış kodu ' + r.status, secs: (Date.now() - t0) / 1000 });
}

const w = Math.max(8, ...rows.map(r => r.name.length));
console.log('\n' + '='.repeat(w + 30));
console.log(`${'SENARYO'.padEnd(w)}  SONUÇ   SÜRE`);
for (const r of rows) console.log(`${r.name.padEnd(w)}  ${r.ok ? 'PASS ' : 'FAIL '}  ${r.secs.toFixed(1).padStart(6)} sn  ${r.note}`);
const bad = rows.filter(r => !r.ok).length;
console.log('='.repeat(w + 30));
console.log(bad ? `${bad}/${rows.length} senaryo BAŞARISIZ` : `${rows.length}/${rows.length} senaryo geçti`);
process.exit(bad ? 1 : 0);
