'use strict';
// CI smoke test (not shipped — excluded from package.json "files"). On a runner
// without officecli on PATH, create() triggers auto-install (install.sh on unix,
// install.ps1 on Windows), proving the cross-platform provisioning + the pipe
// round-trip end to end. Exits non-zero on any failure.
const os = require('os');
const path = require('path');
const fs = require('fs');
const oc = require('./index.js');

(async () => {
  const f = path.join(os.tmpdir(), `officecli-smoke-${process.pid}.xlsx`);
  const d = await oc.create(f, ['--force']);
  await d.send({ command: 'set', path: '/Sheet1/A1', props: { text: 'smoke-ok' } });
  const g = await d.send({ command: 'get', path: '/Sheet1/A1' });
  await d.close();
  try { fs.unlinkSync(f); } catch (_) { /* ignore */ }
  if (!JSON.stringify(g).includes('smoke-ok')) {
    console.error('node SDK smoke FAIL: A1 mismatch', JSON.stringify(g));
    process.exit(1);
  }
  console.log('node SDK smoke PASS');
})().catch((e) => {
  console.error('node SDK smoke THREW:', (e && e.message) || e);
  process.exit(1);
});
