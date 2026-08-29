# Third-Party Notices

## slides_maker narrative divergence

- Upstream project: `addsumtech/slides_maker`
- Upstream commit: `0b38732543f62920f094a18c1621992068a18f57`
- Copyright: Copyright (c) 2026 Leo-Lyu
- License: MIT
- Upstream file: `skills/slide-maker/scripts/arc_divergence.py`
- Adapted file: `script_engine/narrative_arc.py`

The adaptation retains the CJK contiguous-run bigram tokenizer, the
shape/order/ask/stance comparison, and the relative evidence-effort check. It
removes the standalone JSON/CLI checkpoint contract and reads candidates from
CyberPPT's authoritative `deck-plan.json` structure.

## slides_maker composed trace

- Upstream project: `addsumtech/slides_maker`
- Upstream commit: `0b38732543f62920f094a18c1621992068a18f57`
- Copyright: Copyright (c) 2026 Leo-Lyu
- License: MIT
- Upstream file: `skills/slide-maker/scripts/trace_composed.py`
- Adapted file: `script_engine/analysis_audits/composed_trace.py`

The adaptation retains `cjk_ngrams()`, `latin_tokens()`, `numbers()` and the
quoted/composed distinction. It reads Final Script JSON and the existing
Foundation semantic surface, narrows hard Latin findings to high-specificity
identifiers, and exposes Critic priorities through existing CLI diagnostics.
It does not inspect PPTX files or create a new content artifact.

### License text

MIT License

Copyright (c) 2026 Leo-Lyu

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
