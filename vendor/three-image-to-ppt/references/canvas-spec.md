# Canvas contract

Every page job resolves one canvas contract before image generation.

1. Parse the page script first. A declared pixel canvas such as `1920×1080` or `1920x1080` is authoritative.
2. If no pixels are declared, a declared ratio such as `16:9`, `16：9`, `4:3`, or `16:10` is authoritative. Render at the configured long edge while preserving that ratio.
3. If the page script declares neither, use the global default: **1920×1080 (16:9)**.

The resolved width, height, and source (`script_pixels`, `script_ratio`, or `global_default`) must be saved in the page job manifest and appended to every FULL, BACKGROUND, and TEXT generation prompt. All image inputs must have identical dimensions. A nonmatching image is a failed input, never stretched by the PPT renderer.
