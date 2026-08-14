# Component manifest

This file distinguishes **bundled source** from **runtime downloads** so the repository never pretends to contain model weights it does not contain.

## Bundled in this Skill archive

| Component | Bundled | Purpose |
|---|---:|---|
| `SKILL.md` | yes | Agent Skill instructions and execution policy |
| `enhance.py`, `batch.py` | yes | simple entry points |
| `src/ppt_image_enhancer/*` | yes | image inspection, post-processing, text guard, backend adapters |
| `config/*` | yes | presentation presets and backend configuration |
| `tools/bootstrap.py` | yes | installs/downloads official optional backends |
| `tools/doctor.py` | yes | environment/backend diagnostics |
| tests | yes | base pipeline and adapter smoke tests |

## Downloaded/installed at runtime

| Component | Bundled | Installed location | Source |
|---|---:|---|---|
| Real-ESRGAN NCNN executable + portable model assets | no | `runtime/realesrgan-ncnn-vulkan/` | official Real-ESRGAN release asset |
| Real-ESRGAN Python source | no | `third_party/Real-ESRGAN/` | official `xinntao/Real-ESRGAN` repository |
| Real-ESRGAN Python pretrained weights | no | upstream-managed cache/repository paths | official Real-ESRGAN inference flow |
| SwinIR source | no | `third_party/SwinIR/` | official `JingyunLiang/SwinIR` repository |
| SwinIR pretrained weights | no | `third_party/SwinIR/model_zoo/swinir/` | official SwinIR inference flow |
| PyTorch/CUDA runtime | no | Python environment | hardware/platform-specific installation |

## Why they are not bundled

They are large third-party artifacts, may vary by OS/GPU, and have their own upstream licenses and release lifecycle. The Skill owns orchestration and protection logic; the upstream projects own their binaries/models.
