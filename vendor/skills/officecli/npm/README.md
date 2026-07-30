# officecli

CLI for reading and writing Office documents (`.docx`, `.xlsx`, `.pptx`) via a
document DOM API.

```bash
npm install -g @officecli/officecli
# or run without installing:
npx @officecli/officecli --help
```

On install, the native binary for your platform (macOS / Linux / Windows,
x64 / arm64) is downloaded from the official release mirror
(`d.officecli.ai`, with GitHub Releases as a fallback) and verified against
its published `SHA256SUMS`. macOS builds are Developer ID signed and notarized.

## Usage

```bash
officecli create report.docx
officecli add report.docx /body --type paragraph --prop text="Hello"
officecli get report.docx '/body/p[1]'
officecli --help
```

## Notes

- Supported platforms: macOS (arm64/x64), Linux glibc & musl/Alpine
  (arm64/x64), Windows (arm64/x64).
- Set `OFFICECLI_SKIP_BINARY_DOWNLOAD=1` to skip the download during
  `npm install` (the binary is then fetched on first run).
- Source, issues and full docs:
  <https://github.com/iOfficeAI/OfficeCLI>

Licensed under Apache-2.0.
