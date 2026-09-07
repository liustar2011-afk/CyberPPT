# Checkpoint — Final Stage1 faithful regression verification

Date: 2026-09-07
Branch: `refactor/stage1-faithful-authoring`

Status: completed — regression-neutral relative to current `main`.

## Verified functional head

- Branch functional/tested head: `4f7f191143859e4c632f6b2dc1d2c49f087c6e59`
- Main baseline head: `d6b986cc7954ef190b2d92e6811fac59718ce9f9`
- Draft PR: #28

This checkpoint commit is documentation-only and records the verification of the functional head above.

## Pytest failure-set comparison

The repository `main` branch already has historical full-suite failures. Acceptance for this refactor is therefore exact failure-set regression neutrality, not an artificial all-green result obtained by changing unrelated tests.

### Python 3.10

Branch:

- 63 failed
- 1882 passed

Main baseline:

- 63 failed
- 1858 passed

Set comparison:

- branch-only failures: 0
- main-only failures: 0
- failure sets are exactly equal

### Python 3.12

Branch:

- 63 failed
- 1882 passed

Main baseline:

- 63 failed
- 1858 passed

Set comparison:

- branch-only failures: 0
- main-only failures: 0
- failure sets are exactly equal

The branch therefore introduces no pytest regression and adds 24 passing tests on both Python versions.

## Packaging smoke

Exact branch functional head:

- macOS wheel/package smoke: passed
- Windows wheel/package smoke: passed

These match the successful baseline behavior on `main`.

## OfficeCLI smoke comparison

Both the branch and current `main` fail the same OfficeCLI render step for the same external runtime reason.

Shared failure:

```text
System.IO.FileNotFoundException:
Could not load file or assembly 'System.Private.Xml, Version=10.0.0.0,
Culture=neutral, PublicKeyToken=cc7b13ffcd2ddd51'.
```

Both runs use repository OfficeCLI `1.0.145`; geometry validation passes, then HTML rendering fails because the Ubuntu runner cannot load the required .NET assembly. This failure exists on `main` and is not introduced by the Stage1 faithful refactor.

## Completion verdict

The Stage1 faithful-authoring refactor is complete for the agreed scope:

- default faithful authoring no longer forces judgment-first / one-page-one-conclusion semantics;
- `full_copy` is the faithful semantic manuscript and `onscreen` derives from it;
- analytical authoring remains explicit opt-in;
- high-confidence semantic-addition audits protect source fidelity;
- exact `page-source` packets are implemented and required before faithful page authoring when v2 source index exists;
- PLAN human review shows source anchors;
- `script` is consistently the default Stage1 profile and `strict/legacy` is explicit;
- strict Source Truth projection preserves explicit/inferred claim origin correctly;
- CLI modularization remains intact;
- examples, contracts, tests and master workflow documentation are aligned;
- exact failure-set comparison shows zero branch-only pytest failures.

PR #28 remains unmerged. Merge is intentionally left as a separate repository decision.
