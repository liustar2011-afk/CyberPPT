'use strict';
// Minimal end-to-end demo: create a workbook, set + read a cell, close.
//   node demo.js [path.xlsx]
const os = require('os');
const path = require('path');
const oc = require('./index.js');

async function main() {
  const file = process.argv[2] || path.join(os.tmpdir(), `officecli-demo-${process.pid}.xlsx`);

  // create() makes the file and binds to the resident it auto-starts.
  const doc = await oc.create(file, ['--force']);
  try {
    // One write.
    await doc.send({ command: 'set', path: '/Sheet1/A1', props: { text: 'Hello from Node' } });

    // Read it back — get --json returns the envelope as a JS object.
    const got = await doc.send({ command: 'get', path: '/Sheet1/A1' });
    console.log('A1 =', JSON.stringify(got));

    // Many writes in one round-trip.
    await doc.batch([
      { command: 'set', path: '/Sheet1/B1', props: { text: '42' } },
      { command: 'set', path: '/Sheet1/C1', props: { text: 'world' } },
    ]);

    console.log('B1 =', JSON.stringify(await doc.send({ command: 'get', path: '/Sheet1/B1' })));
  } finally {
    // close() flushes the resident's in-memory doc to disk.
    await doc.close();
  }
  console.log('wrote', file);
}

main().catch((e) => {
  console.error(e);
  process.exit(1);
});
