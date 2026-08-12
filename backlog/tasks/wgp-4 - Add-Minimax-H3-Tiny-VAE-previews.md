---
id: WGP-4
title: Add Minimax H3 Tiny VAE previews
status: Human Review
assignee:
  - '@codex'
created_date: '2026-08-12 09:00'
updated_date: '2026-08-12 09:21'
labels: []
dependencies: []
modified_files:
  - defaults/minimax_h3_fl2va.json
  - defaults/minimax_h3_fl2va_pruned.json
  - defaults/minimax_h3_ref2va.json
  - defaults/minimax_h3_ref2va_pruned.json
  - shared/preview/registry.py
  - shared/preview/loader.py
  - shared/preview/coordinator.py
  - shared/preview/adapters/h3.py
  - tests/test_preview_subsystem.py
  - docs/preview/README.md
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
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Reference implementation reviewed: upstream PR #2124 confirms a 24-channel H3 TAE input layout and three-frame decoder warm-up, but implements a separate H3-only UI/download path without shared registry/coordinator integration or tests. WGP-4 will reuse the established modular preview subsystem instead. Exact taeh3 asset integrity/license/normalization remains pending upstream primary-source verification before implementation.

Implemented H3 through the existing capability-bound shared preview subsystem rather than PR #2124's parallel H3-specific UI/download path. Pinned community taeh3 revision d1eb17beb5e11856f93eb682e0998b6f232969d1 at 39,458,084 bytes with computed SHA-256 200b17f16fbdf2afbd4f5c70b8390d57225bd2671ec17dfe162ad0e866dff66c and retained its MIT notice.

Verification: focused preview suite passed in AI-Video-Studio backend venv (26 tests, 1 skipped); pinned real decoder strict-loaded as decoder-only TAEHV with 24 channels; real CPU zero-latent adapter smoke decoded 9 frames and selected 3 images; touched Python files compiled; all four JSON definitions parsed; git diff --check passed. Independent reviewer verdict: ship. Full H3 generation with production model weights was not run.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Extended the existing Tiny VAE live-preview subsystem to MiniMax H3 without adding a second UI or decoder lifecycle. All four H3 model definitions now advertise `taeh3`; the shared registry pins and integrity-checks the immutable community decoder; the loader strict-loads its decoder-only state; an H3 adapter handles the raw 24-channel C,T,H,W callback latent and existing temporal warm-up contract; and the coordinator dispatches it through the existing scheduler, worker, encoder, OOM/CPU retry, UI/API transport, and RGB fallback. Added focused capability/adapter coverage, preview documentation, and the upstream MIT notice.

Verification: `python -m unittest tests.test_preview_subsystem` passed 26 tests with 1 skip; strict real-weight loading passed; a real CPU adapter smoke decoded the pinned taeh3 weight; touched Python compilation, JSON parsing, and `git diff --check` passed. Independent review verdict: ship. Full production-weight H3 generation remains a deployment-time validation.
<!-- SECTION:FINAL_SUMMARY:END -->
