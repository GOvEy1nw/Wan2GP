---
id: WGP-5
title: Resolve latest upstream merge conflicts
status: Human Review
assignee:
  - '@codex'
created_date: '2026-08-16 09:48'
updated_date: '2026-08-16 09:54'
labels: []
dependencies: []
ordinal: 5000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Complete the in-progress upstream-to-dev merge by resolving the two LTX conflicts without dropping either upstream changes or the dev fork fixes.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 Git reports no unmerged paths or conflict markers
- [x] #2 LTX preview callbacks retain the dev fork denoised/x0 preview behavior while incorporating upstream changes
- [x] #3 LTX 2.5 pixel upscaler retains the Dev checkpoint plus Distilled and pixel-upscaler LoRAs while incorporating upstream changes
- [x] #4 Focused syntax and relevant regression checks pass
<!-- AC:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [x] #1 Acceptance criteria are satisfied
- [x] #2 Relevant automated tests pass
- [x] #3 Lint, type-check, and build checks pass where applicable
- [x] #4 Documentation is updated where required
- [x] #5 Implementation summary and verification evidence are recorded
- [x] #6 No unrelated changes are included
<!-- DOD:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. Resolve helpers.py by retaining the denoised/x0 preview callback and upstream CFG++ unconditional prediction handling. 2. Resolve runtime.py by retaining the LTX 2.5 Dev-plus-Distilled-LoRA mapping and upstream audio sample-rate support. 3. Stage only the two resolved paths and run conflict-marker, syntax, and focused regression checks.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Resolved helpers.py by retaining the denoised/x0 callback before upstream CFG++ advancement. Resolved runtime.py by retaining both LTX 2.5 LoRAs and upstream AUDIO_SAMPLE_RATE. Verification: no unmerged paths or conflict markers; py_compile passed for both files; tests.test_ltx2_upsampler_runtime passed 2 tests; targeted denoised-preview regression passed in the torch-capable AiVS backend venv; resolved-path git diff --check passed. The full suite was not run because the change is limited to two conflict blocks.

Git operation detail: this is a single cherry-pick of upstream commit 25245d62. No sequencer todo remains. The conflicts are staged, but cherry-pick --continue was not run because the user did not request creating the commit.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Resolved both latest upstream merge conflicts without dropping dev behavior: LTX callbacks still publish denoised/x0 previews, LTX 2.5 upscaling still loads Dev plus Distilled and pixel-upscaler LoRAs, and upstream CFG++/audio support is retained. Focused syntax, regression, marker, and whitespace checks pass.
<!-- SECTION:FINAL_SUMMARY:END -->
