# ppt-image-enhancer — installable Agent Skill repository

This is a **real Skill repository**, not a text-only prompt. The repository root contains `SKILL.md`, executable enhancement code, backend adapters, setup tools, presets and tests.

## What is inside the ZIP vs downloaded later

The ZIP contains the Skill and all code written for this integration. It deliberately does **not** duplicate upstream AI model binaries/weights. Those are third-party runtime assets and are fetched from official upstream projects by `tools/bootstrap.py`.

That is why the source repository itself can remain small. After bootstrap, `runtime/` / `third_party/` becomes much larger and contains the actual AI backend assets.

See `MANIFEST.md` for an explicit inventory.

## Easiest use

### First time

Windows PowerShell:

```powershell
./install.ps1
```

macOS/Linux:

```bash
./install.sh
```

The default bootstrap installs base Python packages and tries the official portable Real-ESRGAN NCNN backend.

### Enhance one image

```bash
python enhance.py "page-08.png"
```

Output:

```text
page-08_enhanced.png
page-08_enhanced.png.report.json
```

### Enhance a folder

```bash
python batch.py "pages"
```

Outputs go to `pages/enhanced/` by default.

## What happens automatically

The program estimates whether the page is line/text-heavy or scene-rich, chooses a conservative or AI backend, runs super-resolution when appropriate, protects high-frequency source structure, protects near-white backgrounds, applies restrained cleanup, and writes a report.

If the automatic AI backend fails, `auto` mode falls back to the built-in enhancer instead of abandoning the image.

AI output also falls back automatically when it moves or invents text,
diagram edges, arrows or borders. The JSON report records both the accepted
built-in result and the rejected model's structural-fidelity metrics.

## Backend choices

You normally do not need these switches, but they are available:

```bash
python enhance.py page.png --backend builtin
python enhance.py page.png --backend realesrgan_ncnn
python enhance.py page.png --backend realesrgan
python enhance.py page.png --backend swinir
```

The portable NCNN path is the preferred low-friction desktop backend. Python Real-ESRGAN and SwinIR are optional advanced paths.

## Repository structure

```text
ppt-image-enhancer-skill-v1.0.0/
├── SKILL.md                 # Agent Skill contract
├── README.md                # human usage
├── MANIFEST.md              # honest bundled/downloaded inventory
├── enhance.py               # one image, automatic mode/backend
├── batch.py                 # folder processing
├── install.ps1 / install.sh
├── requirements.txt
├── config/                  # presets and AI adapters
├── src/ppt_image_enhancer/
│   ├── auto.py              # auto mode/backend selection
│   ├── pipeline.py          # enhancement + text_guard
│   ├── sr_backend.py        # Real-ESRGAN/SwinIR/NCNN adapters
│   ├── inspect.py           # quality diagnostics
│   └── config.py
├── tools/
│   ├── bootstrap.py         # obtains official runtime backends
│   └── doctor.py            # checks readiness
├── runtime/                 # generated after bootstrap
├── third_party/             # optional official source clones
├── models/                  # model asset documentation
└── tests/
```

## Important boundary

This Skill improves image quality. It does not redesign the slide and does not OCR-rewrite text. For malformed source text, use a semantic image editor or reconstruct the text as editable PPT elements instead of asking an SR model to guess characters.
