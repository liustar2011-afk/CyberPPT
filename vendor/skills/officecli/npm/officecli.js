#!/usr/bin/env node
'use strict';

// Launcher shim. npm links this as the `officecli` command. It execs the native
// binary fetched by postinstall, forwarding argv, stdio and the exit code. If
// the binary is missing (postinstall was skipped or failed offline), it is
// downloaded lazily on this first run.
//
// This lives at the package root, NOT under bin/, on purpose: the repo's root
// .gitignore ignores `bin/`, which would silently drop a bin/ shim from the
// published tarball.

const fs = require('fs');
const { spawnSync } = require('child_process');
const installer = require('./lib/install-binary');

async function main() {
  let bin = installer.binaryPath();
  if (!fs.existsSync(bin)) {
    try {
      bin = await installer.ensureBinary();
    } catch (err) {
      process.stderr.write('[officecli] ' + err.message + '\n');
      process.exit(1);
    }
  }
  const res = spawnSync(bin, process.argv.slice(2), { stdio: 'inherit' });
  if (res.error) {
    process.stderr.write('[officecli] failed to launch binary: ' + res.error.message + '\n');
    process.exit(1);
  }
  // Signal-terminated child: surface a non-zero exit rather than a null status.
  if (res.signal) {
    process.exit(1);
  }
  process.exit(res.status === null ? 1 : res.status);
}

main();
