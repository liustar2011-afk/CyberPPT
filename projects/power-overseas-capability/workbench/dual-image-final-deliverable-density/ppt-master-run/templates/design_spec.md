---
brand_id: 中电联公共元素_轻量版
kind: brand
brand_mode: chrome-only
color_policy: visual-style-owned
summary: China Electricity Council lightweight chrome-only preset; locks public page elements while leaving content colors to visual style.
primary_color: ""
---

# 中电联公共元素_轻量版 Brand Specification

> Chrome-only brand preset. It locks the China Electricity Council public page elements and safety regions. It does not provide a content color scheme, typography system, icon style, voice rules, page structure, or SVG page roster.

## I. Brand Overview

| Property | Value |
|---|---|
| Brand Name | 中国电力企业联合会 |
| Brand Mode | `chrome-only` |
| Color Policy | `visual-style-owned` |
| Use Cases | 需要保留中电联公共品牌层和正式封面底板，同时希望正文视觉风格、配色、字体和版式由主流程根据材料内容确定的正式汇报、研究报告和专题说明 |
| Tone | Institutional, formal, public-sector compatible |

## II. Public Chrome Elements

| Element | Source File | Geometry / Rule | Lock Scope |
|---|---|---|---|
| Top red divider | `./master_elements.svg` | y=82, h=7, fill `#8B0000` | Public chrome only |
| Top-right CEC logo | `./logo.png` via `./master_elements.svg` | x=1060, y=16, w=189, h=63 | Public chrome only |
| Footer blue bar | `./master_elements.svg` | y=696, h=24, fill `#003366` | Public chrome only |
| Footer organization name | `./master_elements.svg` | x=40, y=711.5, font 9, fill `#FFFFFF`, text `中国电力企业联合会` | Public chrome only |
| Dynamic page number | `./master_elements.svg` | x=1240, y=712, font 10, fill `#FFFFFF`, exported as page-number field when supported | Public chrome only |

The red divider, blue footer, white footer text, and logo colors are fixed only for the public chrome layer. They are not a content palette and must not be copied into `spec_lock.md colors` as `primary`, `accent`, `bg`, `surface`, `text`, or chart colors.

## III. Cover Base

| Item | Value |
|---|---|
| Background File | `./cover_bg.jpg` |
| Policy | `chrome-only-cover-base` |
| Usage | 可作为中电联正式材料封面的全幅底图，用于承载标题、副标题、单位、日期和版本信息。 |
| Title Region | x=260, y=150, w=760, h=186，上半白区，建议放主标题和副标题。 |
| Metadata Region | x=360, y=430, w=560, h=220，下方蓝区，建议放汇报单位、日期、版本号等辅助信息。 |
| Non-Derivation Rule | 不得从 `cover_bg.jpg` 推导正文页色板、字体、图标风格、图表色或正文 visual style。红线和深蓝底带仅属于封面底板。 |

Cover generation may use this background as an institutional base plate. It should add only project-specific text and restrained alignment aids when needed; do not add another logo, large decorative graphic, or unrelated visual motif over the existing watermark.

## IV. Cover And Ending Templates

| File | Purpose | Usage |
|---|---|---|
| `./01_cover.svg` | Brand cover page template | Replace `{{TITLE}}`, `{{SUBTITLE}}`, `{{AUTHOR}}`, and `{{DATE}}` with project-specific text. Keep the cover background, text regions, and local contrast rules. |
| `./04_ending.svg` | Brand ending page template | Generic formal closing page with `感谢聆听` and `THANK YOU`. Use as the closing page unless the user explicitly requests a content-specific conclusion page. |

These two page templates are borrowed from `templates/brands/中电联公司_现代能源科技/` as public cover/ending assets. They are part of the chrome-only brand boundary only for opening and closing pages; they must not lock body-page structure, body color palette, icon style, or chart styling.

## V. Safety Regions

| Region | Geometry | Rule |
|---|---|---|
| Top-right logo region | x=1048, y=10, w=220, h=76 | Normal text and content graphics must not enter this region. |
| Footer region | x=0, y=696, w=1280, h=24 | Normal text and content graphics must not enter the footer bar. |
| Body content region | x=58, y=122, w=1164, h=554 | Recommended body area when no layout path supplies a stricter structure. |
| Cover title region | x=260, y=150, w=760, h=186 | Recommended title and subtitle area on `cover_bg.jpg`. |
| Cover metadata region | x=360, y=430, w=560, h=220 | Recommended date, organization, version, or report-type area on `cover_bg.jpg`. |

## VI. Assets

| File | Purpose | Usage |
|---|---|---|
| `./logo.png` | CEC logo lockup | Inject through the master chrome or place only in explicitly branded moments. |
| `./master_elements.svg` | Public page chrome | Red divider, top-right logo, footer bar, organization name, page number. |
| `./cover_bg.jpg` | Public cover base | Optional full-bleed cover background for formal CEC-facing decks; not a content style source. |
| `./01_cover.svg` | Public cover template | Optional cover-page SVG skeleton with placeholders. |
| `./04_ending.svg` | Public ending template | Optional closing-page SVG skeleton. |
| `./master_elements.reference.txt` | Text reference copy | Agent/tooling reference only. |
| `./brand_rules.json` | Machine-readable chrome rules | Safety regions, master element geometry, and chrome-only policy. |

## VII. Non-Locked Design Areas

| Area | Runtime Owner |
|---|---|
| Content color scheme | Strategist Eight Confirmations item e, derived from user requirement, source content, and locked visual style |
| Typography | Strategist Eight Confirmations item g |
| Icon style | Strategist Eight Confirmations item f |
| Visual style | Strategist Eight Confirmations item d |
| Page structure and SVG roster | Free design or explicitly supplied layout / deck |
| Chart and infographic colors | Project `spec_lock.md colors`, not this chrome-only brand |

## VIII. Runtime Rule

When this brand is copied into `<project_path>/templates/`, Strategist must treat it as a chrome-only public-element preset:

- Lock `master_elements.svg`, `logo.png`, `cover_bg.jpg`, `01_cover.svg`, `04_ending.svg`, `brand_rules.json`, protected regions, cover/ending template regions, cover base regions, and public chrome placement.
- Do not treat this brand as a color, typography, icon, or voice truth source.
- Generate the content palette and typography through the normal visual-style-driven confirmations.
- When using `cover_bg.jpg`, place project text inside the declared cover regions and do not infer body-page colors from the cover image.
- Keep public chrome visually separate from body content; do not redraw the logo, organization name, footer, or page number inside ordinary page SVGs when the master layer is available.
