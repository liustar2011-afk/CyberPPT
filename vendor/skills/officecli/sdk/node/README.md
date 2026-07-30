# @officecli/sdk

A thin **async** Node.js client over [officecli](https://github.com/iOfficeAI/OfficeCLI)'s
resident pipe. It does one thing: forward a command to the running resident and
hand back the response. There is no second vocabulary to learn — a command is the
same object you'd put in an officecli `batch` list.

```bash
npm install @officecli/sdk
```

Installing the SDK pulls `@officecli/officecli`, which bundles an auto-updating
native binary — so the CLI comes with it and you don't manage it separately. If
the binary is ever missing, the SDK provisions it on first use (downloads the
bundled signed binary, or falls back to the official installer).

## Usage

```js
const oc = require('@officecli/sdk');

const doc = await oc.create('report.xlsx', ['--force']);
try {
  await doc.send({ command: 'set', path: '/Sheet1/A1', props: { text: 'Hello' } });
  const a1 = await doc.send({ command: 'get', path: '/Sheet1/A1' }); // → envelope object
  console.log(a1);

  // Many writes in one round-trip:
  await doc.batch([
    { command: 'set', path: '/Sheet1/B1', props: { text: '42' } },
    { command: 'set', path: '/Sheet1/C1', props: { text: 'world' } },
  ]);
} finally {
  await doc.close(); // flushes to disk
}
```

On Node ≥ 24 you can use `await using` and skip the explicit close:

```js
await using doc = await oc.open('existing.xlsx');
await doc.send({ command: 'get', path: '/body/p[1]' });
```

## Two surfaces

- **bootstrap** (infrequent): `create()` / `open()` spawn one CLI process.
- **hot path**: `send()` / `batch()` are pure pipe round-trips, no per-command
  process spawn.

## API

- `await create(path, args?, options?)` → `Document` — make a new file. Extra CLI
  flags pass through verbatim (`['--force']`, `['--type', 'docx']`).
- `await open(path, options?)` → `Document` — open an existing file.
- `Document.send(item, asJson = true, timeoutMs?)` — forward one command.
  `asJson = false` requests plain-text output (view/raw/dump).
- `Document.batch(items, { force = true, stopOnError = false, timeoutMs? })`.
- `Document.alive(timeoutMs?)` — is a resident serving this file?
- `Document.close()` — stop the resident (flushes to disk).
- `install()` — run the official installer (unix only).

`options`: `{ binary?, timeoutMs?, autoInstall? }`. Pass `binary` to point at a
specific officecli; `autoInstall: false` to disable provisioning a missing CLI.

## Errors vs business outcomes

Transport/process failures throw `OfficeCliError`. Business outcomes are **not**
exceptions — they live in the returned envelope's `success` field, exactly like
the CLI's exit code. Check `result.success` yourself.

## Lifecycle

```js
// Owner — close on exit:
const d = await oc.open(f);
try { /* ... */ } finally { await d.close(); }

// Borrow — leave a resident another program owns running:
const d = await oc.open(f);
await d.send(/* ... */); // no close()
```

A dead resident is transparently restarted and the command retried once. An
alive-but-busy pipe raises `OfficeCliError` (retry, or `close()` and reopen) —
the SDK never bypasses a live resident, which would race its save.

Licensed under Apache-2.0.
