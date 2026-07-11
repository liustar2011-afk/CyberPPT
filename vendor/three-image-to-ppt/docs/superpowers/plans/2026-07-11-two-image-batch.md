# Two-image and batch implementation plan

**Goal:** Add a first-class two-image OCR-to-PPT path while retaining optional three-image OCR, with independent batch page jobs.

## Tasks

- [ ] Add CLI input-mode selection and validate the required image set.
- [ ] Allow JSON OCR to be generated from FULL in two-image mode; retain TEXT as the OCR source in three-image mode.
- [ ] Add a batch manifest format and page-isolated runner with deterministic ordering.
- [ ] Cover two-image success, missing-input rejection, and mixed batch outcomes with tests.
- [ ] Update the workflow contract and prompts.
