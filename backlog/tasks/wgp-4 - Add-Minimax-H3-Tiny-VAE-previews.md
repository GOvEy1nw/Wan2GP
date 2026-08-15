---
id: WGP-4
title: Add Minimax H3 Tiny VAE previews
status: Human Review
assignee:
  - '@codex'
created_date: '2026-08-12 09:00'
updated_date: '2026-08-15 17:06'
labels: []
dependencies: []
modified_files:
  - defaults/minimax_h3_fl2va.json
  - defaults/minimax_h3_fl2va_pruned.json
  - defaults/minimax_h3_ref2va.json
  - defaults/minimax_h3_ref2va_pruned.json
  - models/minimax_h3/pipeline.py
  - shared/preview/registry.py
  - shared/preview/loader.py
  - shared/preview/coordinator.py
  - shared/preview/adapters/h3.py
  - tests/test_preview_subsystem.py
  - docs/preview/README.md
  - THIRD_PARTY_NOTICES.md
  - LICENSES/taeh3-MIT.txt
priority: medium
type: enhancement
ordinal: 4000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Extend the existing Tiny VAE live-preview capability so Minimax H3 generations can use the taeh3 decoder while preserving the established fallback behavior for unsupported or unavailable decoders.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 Minimax H3 model definitions advertise Tiny VAE preview support through the existing capability mechanism.
- [x] #2 Tiny VAE preview decoding for Minimax H3 uses taeh3 with the correct latent input contract and produces preview media through the shared preview pipeline.
- [x] #3 Missing or unusable taeh3 assets fall back through the existing preview behavior without breaking generation.
- [x] #4 A focused runnable check protects Minimax H3 capability selection and adapter behavior.
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
1. Register a verified taeh3 decoder in the shared preview registry and advertise it from all MiniMax H3 model definitions; preserve the existing capability-based install and RGB fallback flow.
2. Add the smallest H3-specific latent adapter and dispatch from the shared coordinator, reusing decoder loading, scheduling, OOM/CPU fallback, encoding, and UI/API transport. Do not adopt PR #2124's parallel H3-specific UI/download pipeline.
3. Extend the focused preview subsystem test with H3 capability selection and adapter-contract coverage, then run the focused suite and syntax/diff checks. Only change the H3 generation callback if real decoder evidence shows its existing post-step latent is unusable.

4. Correct the taeh3 asset source to Kijai/MiniMax-H3-TAE, recompute immutable size/SHA-256 metadata, confirm the replacement state dict strict-loads and decodes through the existing H3 adapter, then rerun focused validation.

5. Fix the confirmed H3 callback regression at `models/minimax_h3/pipeline.py`: retain the denoised/x0 estimate in Euler and RES, send a preview-only x0 tensor through the existing callback, postprocess source/mask regions at sigma zero without mutating sampler state, and preserve Spectrum anchor suppression. Add one focused regression check for x0 versus post-step state, run the focused preview suite and compile/diff checks, obtain independent review, then commit and push `dev` so the existing origin PR updates.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Reference implementation reviewed: upstream PR #2124 confirms a 24-channel H3 TAE input layout and three-frame decoder warm-up, but implements a separate H3-only UI/download path without shared registry/coordinator integration or tests. WGP-4 will reuse the established modular preview subsystem instead. Exact taeh3 asset integrity/license/normalization remains pending upstream primary-source verification before implementation.

Implemented H3 through the existing capability-bound shared preview subsystem rather than PR #2124's parallel H3-specific UI/download path. Pinned community taeh3 revision d1eb17beb5e11856f93eb682e0998b6f232969d1 at 39,458,084 bytes with computed SHA-256 200b17f16fbdf2afbd4f5c70b8390d57225bd2671ec17dfe162ad0e866dff66c and retained its MIT notice.

Verification: focused preview suite passed in AI-Video-Studio backend venv (26 tests, 1 skipped); pinned real decoder strict-loaded as decoder-only TAEHV with 24 channels; real CPU zero-latent adapter smoke decoded 9 frames and selected 3 images; touched Python files compiled; all four JSON definitions parsed; git diff --check passed. Independent reviewer verdict: ship. Full H3 generation with production model weights was not run.

Human review correction: the registered community PreviewOverride safetensor is the wrong H3 TAE asset. Replace it with https://huggingface.co/Kijai/MiniMax-H3-TAE/resolve/main/vae_approx/taeh3.safetensors and refresh integrity/runtime evidence before returning to review.

Correction completed: replaced the prior temporal PreviewOverride asset with Kijai/MiniMax-H3-TAE `taeh3.safetensors` pinned at revision `a213ac8bf2f148b4f32372279a7f207846978900` (9,791,388 bytes; SHA-256 `f0f60fa072089997f817402098c2fd90777cb2660dd79cf5df42fc1e3e08e527`). The supplied file is a flat 2D per-frame decoder, so the loader now reconstructs that exact state-dict architecture while LTX continues using TAEHV. Removed the obsolete MIT notice and added Apache-2.0 attribution referencing the repository's existing license text.

Correction verification: `C:\Users\rais\Documents\GitHub\AI-Video-Studio\backend\.venv\Scripts\python.exe -m unittest tests.test_preview_subsystem` ran 26 tests: OK, 1 skipped. The exact pinned asset strict-loaded as H3Decoder and decoded a CPU smoke latent to 3 frames. `py_compile` passed for registry, loader, H3 adapter, and focused test; `git diff --check` passed. Independent correction review verdict: ship. Full production H3 GPU generation remains unrun.

Diagnosis 2026-08-15: `models/minimax_h3/pipeline.py` computes H3 x0 as `video + sigma * video_velocity` in both Euler and RES paths, but the callback receives the post-step noisy `video`. At final sigma=0 the post-step state equals x0, exactly matching the reported last-step-only usefulness. KJNodes PreviewOverride decodes sampler-provided x0, and LTX now callbacks with postprocessed denoised_video. Minimal future fix is confined to H3 `denoise_pass`: callback with a preview-only detached x0, apply source/mask conditioning at sigma=0 on a clone, preserve Spectrum anchor suppression, and leave sampling state unchanged. No source edits were made during this diagnosis.

User explicitly authorized implementing diagnosis #0040, pushing the result to `dev`, and updating the existing origin PR.

Implemented review fix #0040: both H3 Euler and RES retain `video_denoised = video + sigma * velocity` for preview callbacks while the sampler continues updating `video` exactly as before. Video-to-video/masked source regions are reinjected at sigma zero only on a preview clone; Spectrum anchor capture remains suppressed. The initial new test assertion exposed a scalar-versus-one-element shape mismatch and was corrected without weakening the contract.

Verification 2026-08-15: targeted H3 x0 regression passed; `C:\Users\rais\Documents\GitHub\AI-Video-Studio\backend\.venv\Scripts\python.exe -m unittest tests.test_preview_subsystem` ran 27 tests, OK, 1 skipped; targeted `py_compile` passed; `git diff --check` passed with only existing CRLF conversion warnings. Independent reviewer verdict: ship. Live H3 GPU generation remains user validation.
<!-- SECTION:NOTES:END -->

## Comments

<!-- COMMENTS:BEGIN -->
author: @codex
created: 2026-08-15 16:50
---
Human review feedback: MiniMax H3 TAE previews are not visually useful until the final denoising step, while LTX is useful early. Read-only diagnosis confirms this is the same noisy-latent-versus-x0 regression previously fixed for LTX.
---
<!-- COMMENTS:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
## Summary
- Added MiniMax H3 Tiny VAE previews through the existing capability registry, shared coordinator, validated download, OOM/CPU fallback, and preview transport.
- Pinned the verified Kijai/MiniMax-H3-TAE flat 2D decoder with immutable size/SHA-256 metadata and Apache-2.0 attribution.
- Fixed H3 preview timing so Euler and RES callbacks decode the current denoised/x0 estimate instead of the post-step noisy sample, preserving sampling output, source/mask conditioning, and Spectrum suppression.
- Added focused H3 capability, adapter, and x0 callback regressions.

## Verification
- Focused preview subsystem: 27 tests passed, 1 skipped.
- Targeted Python compilation and `git diff --check`: passed.
- Exact pinned decoder strict-load/CPU smoke from the preceding correction: passed.
- Independent reviewer verdict: ship.

## Remaining validation
- A live production H3 GPU generation is still required to visually confirm early previews across representative Euler/RES and masked modes.
<!-- SECTION:FINAL_SUMMARY:END -->
