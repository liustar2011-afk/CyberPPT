# Blueprint Image Learning

Source: `/Volumes/DOC/CyberPPT/projects/电力可信数据空间科技成果转化/workbench/blueprints`

## Scope

- Samples: 12 blueprint images, 1672 x 941 px, normalized to 1280 x 720.
- Manifest schema: `cyberppt.stage2_blueprint_manifest.v1`.
- Style: `象牙白 + 深蓝强调`.
- Policy: blueprint text is placeholder; final editable PPT must use `content-lock` text.

## Learned Layout Rules

- Canvas: 16:9, normalized 1280 x 720.
- Safe body zone: `x=25.64, y=84.00, w=1226.80, h=520.24`.
- Lower SO WHAT band: `x=25.64, y=618.24, w=1228.33, h=49.35`.
- Header / page-number chrome occupies the upper-left area; do not place body objects there.
- Median dark-blue visual density: `0.1654`; pages much above this should be treated as dense architecture / operations pages.
- Final PPT should use the blueprint for layout, visual density, color hierarchy and component placement only.

## Roles Observed

封面、背景、必要性、可行性、目标、架构、技术、场景、运营、实施、投入产出、风险保障。

## Application Notes

- Do not OCR-copy tiny blueprint text into final PPT.
- Use content locks for actual titles, subtitles, bullets, labels and SO WHAT text.
- When generating editable objects, place body components inside the safe body zone unless the slide role is `封面`.
- When a lower dark band is detected, reserve it for SO WHAT / conclusion text and align the text to the band centerline.
- Keep the page-number/header chrome separate from content objects.
