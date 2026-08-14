# Model assets

This repository intentionally does **not** embed hundreds of megabytes of third-party pretrained weights.

Runtime assets are installed by `tools/bootstrap.py`:

- `runtime/realesrgan-ncnn-vulkan/`: official portable Real-ESRGAN NCNN package; the upstream archive contains the executable and model files used by the portable backend.
- `third_party/Real-ESRGAN/`: optional official Python source checkout. Its inference script retrieves supported missing weights when needed.
- `third_party/SwinIR/`: optional official source checkout. Its official test script retrieves supported pretrained weights when needed.

This separation keeps the Skill repository reviewable while still providing a real executable backend after bootstrap.
