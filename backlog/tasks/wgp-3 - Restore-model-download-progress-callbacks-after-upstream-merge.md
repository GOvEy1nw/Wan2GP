---
id: WGP-3
title: Restore model-download progress callbacks after upstream merge
status: Done
assignee:
  - '@codex'
created_date: '2026-08-11 16:34'
updated_date: '2026-08-11 16:58'
labels: []
dependencies: []
references:
  - 'https://github.com/deepbeepmeep/Wan2GP/pull/2026'
priority: high
type: bug
ordinal: 3000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
An upstream merge into the AiVS branch restored the older WanGP download helper signatures. AI-Video-Studio model-pack downloads still pass progress_callback, so downloads now fail before transfer with TypeError. Restore the PR #2026 callback contract without broadening scope.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 wgp.download_models accepts the optional progress_callback used by AI-Video-Studio model-pack downloads
- [x] #2 The callback is forwarded through process_files_def and direct-file download paths covered by PR #2026
- [x] #3 Existing callers that omit the callback remain behaviorally compatible
- [x] #4 A focused regression check proves the callback signature and forwarding path
<!-- AC:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [x] #1 Acceptance criteria are satisfied
- [x] #2 Relevant automated tests pass
- [x] #3 Lint, type-check, and build checks pass where applicable
- [x] #4 Documentation is updated where required
- [x] #5 Implementation summary and verification evidence are recorded
- [x] #6 No unrelated changes are included
- [x] #7 Targeted validation passes
- [x] #8 The final diff contains only the merge-regression repair and its focused check
<!-- DOD:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. Compare current AiVS signatures and forwarding against PR 2026 and the merge commit. 2. Restore the smallest missing callback contract in wgp.py, reusing shared download support already present. 3. Add or restore one focused regression check, then run it plus syntax and diff checks. 4. Record evidence and move the task to Human Review.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Restored PR 2026 structured download callbacks in shared/utils/download.py and optional forwarding in wgp.py, preserving existing positional behavior. Restored a dependency-light 17-test regression including AST checks for the public signature and every forwarding call. Validation: 17 Wan2GP tests passed in both standalone and AiVS backend Python; 12 backend model-pack tests passed; compileall and git diff --check passed. The user confirmed a live AiVS model download now succeeds. Broader WanGP WebUI progress presentation was deliberately left out of this repair.

Human acceptance: user confirmed a live AiVS model download succeeds and requested publication to the AiVS branch.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Fixed the AiVS model-pack TypeError by restoring the optional progress_callback contract and structured downloader implementation, then synced the three repaired files into AiVS. Verified with 17 focused tests in both runtimes, 12 AiVS backend tests, syntax/diff checks, and a successful live user download.
<!-- SECTION:FINAL_SUMMARY:END -->
