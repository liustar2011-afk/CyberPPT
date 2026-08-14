# Stage 02 Image-to-PPTX Full Internalization

## Decision

CyberPPT will own the complete PPT-Master `image-to-pptx` Quick reconstruction
capability. It will not invoke `/Volumes/DOC/ppt-master` at runtime. CyberPPT
Stage 02 remains the authority for the prior full-image generation, typo audit,
script binding, and final delivery assembly; the imported reconstruction runtime
becomes the only transformation between the audited image and the Stage 02
assembly input.

The target acceptance criterion is visual equivalence at normal slide viewing
size, native editable text and reconstructable graphics/layers. A reviewer may
make a very small number of local SVG edits. Requiring pixel-perfect identity is
explicitly out of scope; a page that needs a layout redesign, wholesale text
replacement, or a large visual rebuild is rejected.

## Reference Baseline

The source of truth is PPT-Master’s `image-to-pptx.md` profile and its Quick
runtime. The following capabilities are imported as one cohesive feature:

1. Ordered canonical-page roster and source archive.
2. Per-page visible-region inventory, source sufficiency, identity/data safety,
   z-order and layer-stack decisions.
3. Reference-image preparation: clean bases, registered scene/foreground
   layers, exact source crops and isolated/shared plates.
4. Hand-authored SVG with native text, exact geometry, source-graphic fidelity,
   and no canonical full-page image concealed in the delivery.
5. SVG quality validation, visual review material, local SVG editor for small
   human corrections, revalidation and re-export.
6. Native PPTX conversion and package postflight.

## Architecture

```text
CyberPPT full image + passed typo audit + final-script binding
                         |
                         v
image_to_pptx_runtime (ported PPT-Master Quick reconstruction)
  roster -> inventory -> layer preparation -> hand-authored SVG
       -> quality check -> visual review/editor -> approved SVG roster
                         |
                         v
CyberPPT Stage 02 assembly and delivery readiness
```

### 1. Internal runtime package

Create `scripts/image_to_pptx_runtime/` as the CyberPPT-owned import of the
PPT-Master reconstruction runtime. Retain provenance headers on copied files
and use package-local imports only. It includes the image-to-pptx-specific
parts of PPT-Master’s project/roster utilities, source/layer preparation,
image treatment and slicing, SVG quality checker, SVG authoring viewer/editor,
native SVG-to-PPTX writer and its required DrawingML/PPTX package modules.

Unrelated PPT-Master product routes—research, templates, narration/video,
beautification and external image search providers—are not imported. They are
not part of the image-to-PPTX capability and must not become a hidden Stage 02
dependency.

### 2. Internal Skill and workflow

Expand `.agents/skills/cyberppt-image-to-editable-svg/` to be a faithful,
path-correct CyberPPT adaptation of the entire PPT-Master image-to-pptx Quick
workflow. All referenced Quick, image-base, image-generator, SVG quality,
visual-review and local-editor instructions must resolve inside this repository.
The Stage 02 command calls the runtime with the same reconstruction semantics,
not the former OCR/rectangle fallback.

### 3. Stage 02 adapter boundary

The existing audited `full` image remains mandatory. The adapter constructs the
runtime project in the active Stage 02 build directory, binds canonical source
pages to the approved final script and text-audit receipt, then requests a
complete SVG roster. It consumes only a passing SVG roster and its review
report. CyberPPT retains its own final output locations, readiness report and
CLI shape.

The old `scripts/image_to_editable_svg` coordinate reconstruction is removed
from production generation. Its contracts may remain only where they are
useful as compatibility validators, never as an automatic visual author.

### 4. Review and local correction loop

The runtime emits source/recomposition review images and an issue list grouped
by text, source graphics, layers and geometry. A passing initial review
exports directly. A limited local correction starts the imported SVG editor,
records edits in the runtime project, reruns SVG quality and then reassembles.
The adapter marks a page failed if a required asset remains unverified,
registration drifts, editable text is missing, or the reviewer reports a
whole-page rebuild requirement.

### 5. Fidelity and safety rules

- Visible ordinary text is native and bound to the final script; OCR is a
  locator only.
- Data/identity graphics are native-and-verified, exact-source, or blocking.
- A canonical full-page source can be comparison evidence only, never delivered
  as a hidden full-slide image.
- Generated layer candidates are inspected and registered against their source
  canvas before SVG authoring.
- All copied runtime code is exercised in CyberPPT without paths into
  `/Volumes/DOC/ppt-master`.

## Verification

1. Unit tests for roster, region inventory, layer registration, source-image
   exclusion, direct SVG text, SVG quality, image relocation and editor edit
   recording.
2. Integration test starts from an audited Stage 02 manifest and produces a
   valid internal runtime project, review report, SVG roster and CyberPPT PPTX.
3. Regression fixture uses the known palette-09 reconstruction and verifies
   that the CyberPPT runtime emits equivalent native text/layer structure
   without reading the PPT-Master checkout.
4. Two-image end-to-end fixture validates page count, editable text, source
   graphic preservation and a human-reviewable visual comparison set.
5. Run the focused suite plus `graft build`, `graft check`, OpenXML validation
   and OfficeCLI structural/text inspection on the exported PPTX.

## Migration and Delivery

The runtime and workflow are copied into CyberPPT first, then imports are
rewired to local modules. A repository scan blocks absolute PPT-Master paths
from production code, skills and tests. The former Stage 02 coordinate-based
author is deleted or converted into a test-only compatibility fixture after the
internal runtime is green. Existing unrelated dirty-tree changes are excluded
from every migration commit.
