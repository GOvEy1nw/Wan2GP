# WanGP Animated Tiny VAE Live Preview — Agent Implementation Plan

**Baseline repository:** `GOvEy1nw/Wan2GP`  
**Baseline branch:** `AiVS`  
**Implementation branch:** `feat/tae-live-preview`  
**Initial decoder:** `taeltx2_3.safetensors`  
**Initial supported model class:** validated LTX‑2.3 / LTX‑2 22B profiles only  
**MVP transport:** fragmented H.264 MP4 via NVENC, with animated WebP fallback  
**Compatibility rule:** preserve the existing latent-RGB preview and all existing API consumers

> **Implementation amendment (2026-08-07):** Preview preferences are global
> under **Configuration > Previews**. The fixed frame budget and separate
> playback policy described below are superseded by **TAE Preview FPS**
> (16/8/4/2): decoded frames are sampled uniformly across the clip at that
> rate, up to 1,024 samples. Multi-frame previews prefer independently
> implemented, in-memory fragmented H.264/NVENC and fall back to animated
> WebP; the bounded latest-wins worker remains unchanged.

---

## 1. Verdict

This is feasible, and WanGP already has most of the generation-side plumbing needed.

WanGP’s sampler callbacks already forward intermediate latent tensors through `build_callback()`. The queue consumer already recognizes preview events, `generate_preview()` already exposes an optional model-handler override point, the WebUI already has a preview HTML component, and the Python API already emits structured preview events. The missing work is not “finding a way to access the latent”; it is building a safe preview subsystem around that latent.

The implementation should **not** be a direct copy of the ComfyUI KJNodes node. It should reproduce the behaviour cleanly within WanGP’s own architecture:

1. capture a complete denoising-step video latent;
2. decode it using a compatible Tiny AutoEncoder;
3. reduce the decoded result to a bounded set of useful frames;
4. encode those frames as an animated WebP away from the sampler thread;
5. replace older pending previews rather than allowing a backlog;
6. publish a generation-scoped structured media update;
7. render it in both WanGP and the in-process API;
8. retain the current latent-RGB preview as the fallback.

The first implementation should support **LTX‑2.3 via `taeltx2_3.safetensors`**. Other model families should be added only through explicit registry entries, latent adapters, and validation tests.

---

## 2. Research basis

Primary references:

- WanGP AiVS branch: https://github.com/GOvEy1nw/Wan2GP/tree/AiVS
- WanGP preview callback and UI orchestration: https://github.com/GOvEy1nw/Wan2GP/blob/AiVS/wgp.py
- WanGP in-process API: https://github.com/GOvEy1nw/Wan2GP/blob/AiVS/shared/api.py
- WanGP WebUI-backed API bridge: https://github.com/GOvEy1nw/Wan2GP/blob/AiVS/shared/api_webui.py
- WanGP CLI-backed API bridge: https://github.com/GOvEy1nw/Wan2GP/blob/AiVS/shared/api_cli.py
- Existing queue utility: https://github.com/GOvEy1nw/Wan2GP/blob/AiVS/shared/utils/thread_utils.py
- Current completed-video browser-preview patch: https://github.com/GOvEy1nw/Wan2GP/blob/AiVS/shared/gradio/video_preview.py
- KJNodes preview override, used as a behavioural reference only: https://github.com/kijai/ComfyUI-KJNodes/blob/main/nodes/preview_override_node.py
- TAEHV source, weights, model compatibility, and conventions: https://github.com/madebyollin/taehv
- Exact initial weight: https://github.com/madebyollin/taehv/blob/main/safetensors/taeltx2_3.safetensors
- TAEHV MIT license: https://github.com/madebyollin/taehv/blob/main/LICENSE
- KJNodes GPLv3 license: https://github.com/kijai/ComfyUI-KJNodes/blob/main/LICENSE

### Important conclusions from the source inspection

WanGP’s current video preview is a four-frame latent-to-RGB contact sheet. It samples up to four latent timesteps, applies model-family RGB projection factors, joins the resulting stills horizontally, and returns a 200-pixel-high PIL image. This is fast, but it does not provide an intelligible motion preview.

The current Preview accordion is already a `gr.HTML` component. However, `refresh_preview()` converts every preview to a single JPEG. Therefore, simply returning an animated PIL image will not work: the current serialization path would discard the animation.

`AsyncStream` and `SessionStream` are presently unbounded. A preview encoder that is slower than the sampler could therefore accumulate stale work unless the new subsystem adds dedicated bounded/coalescing behaviour.

The KJNodes implementation demonstrates the useful end state:

- decode multiple temporal frames, not one frame;
- encode animated WebP or fragmented MP4;
- perform media encoding in a bounded background worker;
- drop preview work when the worker is already busy instead of blocking sampling.

The TAEHV repository documents these model mappings:

| Model family | Tiny autoencoder weight |
|---|---|
| LTX‑2.3 | `taeltx2_3` |
| LTX‑2 | `taeltx_2` |
| Wan 2.1 | `taew2_1` |
| Wan 2.2 14B | `taew2_1` |
| Wan 2.2 5B | `taew2_2` |
| Hunyuan Video 1 | `taehv` |
| Hunyuan Video 1.5 | `taehv1_5` |
| CogVideoX | `taecvx` |
| Open-Sora 1.3 | `taeos1_3` |

Do not infer compatibility from a filename or channel count alone. Each mapping must be represented by a registry entry and validated against the actual latent contract used by WanGP.

---

## 3. Scope

### In scope for the first pull request

- A generic live-preview subsystem, rather than an LTX-specific block embedded in `wgp.py`.
- `taeltx2_3.safetensors` support for validated LTX‑2.3 / 22B generation paths.
- `Off`, `Fast RGB`, and `Tiny VAE — Animated` preview modes.
- Adaptive capture scheduling.
- Tiny VAE decoding with automatic GPU/CPU fallback.
- Animated WebP encoding.
- A bounded preview worker with stale-result suppression.
- Preview lifecycle integration with task start, pass/window changes, cancellation, completion, and model release.
- WebUI rendering.
- Backward-compatible Python API support.
- Existing model-download progress integration.
- Tests, benchmarks, documentation, and third-party notices.

### Explicitly out of scope for the first pull request

- Copying KJNodes source or importing ComfyUI.
- A global ComfyUI-style callback override.
- Using the full production VAE for every denoising preview.
- Audio previews.
- HLS, WebSocket streaming, or a new media server.
- MP4/NVENC as the primary transport.
- Automatically enabling every TAEHV weight for every nominally related model.
- Replacing `shared/gradio/video_preview.py`; that module concerns completed/uploaded videos.
- Changing sampling, seeds, scheduler behaviour, denoising numerics, or final decoding.
- Treating Tiny VAE output as final-quality output.
- AI Video Studio frontend changes inside this WanGP pull request. The WanGP API contract should make that follow-up straightforward.

---

## 4. Target user experience

### Preview controls

Expose a capability-aware Preview control:

- **Off**
- **Fast RGB** — existing latent projection
- **Tiny VAE — Animated** — only when the current model has a validated compatible decoder

Keep **Fast RGB** as the default for the initial release so existing users receive no extra model download, generation overhead, or VRAM use.

When Tiny VAE mode is selected and its weight is absent, show a clear install/download action. Use the existing structured download-progress system. Do not silently start a download without an equivalent existing WanGP UX precedent.

Recommended advanced options:

- **Preview update rate:** Adaptive, Every step, Every 2 steps, Every 4 steps
- **Preview device:** Auto, GPU, CPU
- **Preview size:** Auto, 384 px, 512 px, 640 px maximum edge
- **Preview frame budget:** 8, 12, 16, 24
- **Preview playback:** Approximate real duration, Fast loop
- **Preview quality:** Fast, Balanced, Detailed

Only expose settings supported by the selected decoder. Do not add universal model controls that silently do nothing.

### Preview display

The current Preview accordion should render:

- the animated WebP;
- `Tiny VAE · Step 4/8 · 16 preview frames`;
- the current pass/window label where relevant;
- a one-time fallback warning if Tiny VAE becomes unavailable.

The existing Cancel/Abort behaviour remains the control for stopping a bad generation. The preview implementation must not invent a second cancellation path.

---

## 5. Proposed architecture

```text
Sampler / denoise loop
        │
        │ callback(step, latent, pass/window metadata)
        ▼
PreviewCoordinator
  ├─ resolves effective preview options
  ├─ validates decoder capability
  ├─ applies adaptive capture schedule
  ├─ owns generation/context token
  └─ selects GPU-sync or CPU-worker path
        │
        ├─ GPU path:
        │    decode synchronously at sampler callback
        │    select/resize frames
        │    copy CPU uint8 frames
        │
        └─ CPU path:
             make a complete, immutable CPU latent snapshot
             submit latest-wins decode request
        │
        ▼
Bounded Preview Worker
  ├─ capacity 1 or 2
  ├─ never blocks sampler submission
  ├─ encodes animated WebP
  ├─ enforces byte/frame/size limits
  └─ discards stale generation/context tokens
        │
        ▼
PreviewMedia
        │
        ├─ send_cmd("preview_media", media)
        ├─ gen["preview_media"] = latest only
        ├─ gen["preview"] = first-frame PIL fallback
        ├─ WebUI gr.HTML renderer
        └─ PreviewUpdate.media in Python API
```

### Why GPU decode should be synchronous in v1

Do not run Tiny VAE CUDA work on a background Python thread while the denoiser continues using the GPU. That creates difficult-to-control VRAM pressure, stream ordering, and offloading interactions.

For v1:

- run GPU Tiny VAE inference inside the sampler callback;
- use the current CUDA stream;
- finish selecting/resizing frames and copying CPU `uint8` data before returning;
- perform only WebP encoding in the background.

This adds measured preview overhead, but it avoids concurrent GPU work and gives deterministic ownership of the intermediate latent.

CPU mode may decode asynchronously, but the callback must first create a completed, immutable CPU snapshot. Never let a worker read a GPU tensor that the sampler may subsequently reuse or mutate.

### Why `StreamingTAEHV` must not persist across denoising steps

Each denoising step represents a newly revised complete video latent. Temporal decoder state from step N must not be reused for step N+1. Doing so would mix different diffusion states and produce invalid previews.

A fresh sequential decode may be used within one captured denoising step to reduce memory, but all temporal decoder state must reset for every captured step.

---

## 6. New core contracts

Create `shared/preview/types.py`.

```python
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal


@dataclass(frozen=True)
class PreviewOptions:
    mode: Literal["off", "rgb", "tae"] = "rgb"
    device: Literal["auto", "cuda", "cpu"] = "auto"
    update_rate: Literal["adaptive", "every_step", "every_2", "every_4"] = "adaptive"
    max_edge: int = 512
    max_frames: int = 16
    webp_quality: int = 72
    target_updates: int = 7
    preserve_duration: bool = True


@dataclass(frozen=True)
class PreviewContext:
    generation_id: str
    context_id: str
    sequence: int
    model_type: str
    architecture: str
    decoder_id: str | None
    step: int
    total_steps: int
    pass_no: int | None = None
    window_no: int | None = None
    fps: float | None = None
    duration_seconds: float | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class PreviewMedia:
    generation_id: str
    context_id: str
    sequence: int
    media_kind: Literal["image", "animated_image", "video"]
    mime_type: str
    data: bytes
    width: int
    height: int
    frame_count: int
    fps: float | None
    duration_ms: int | None
    step: int
    total_steps: int
    decoder_id: str
    decode_ms: float
    encode_ms: float
    dropped_count: int = 0
    warning: str | None = None
```

The implementation may adjust names to fit repository conventions, but preserve these semantic requirements:

- a stable generation ID;
- a context ID that changes between incompatible passes/windows;
- a monotonically increasing sequence number;
- explicit model/decoder identity;
- explicit MIME type;
- binary media bytes;
- dimensions, frame count, timing, and denoising progress;
- no raw GPU tensor in the final media object.

### Backward-compatible API extension

Extend, rather than replace, `PreviewUpdate`:

```python
@dataclass(frozen=True)
class PreviewUpdate:
    image: Image.Image | None
    phase: str
    status: str
    progress: int
    current_step: int | None
    total_steps: int | None
    media: PreviewMedia | None = None
```

Rules:

- Existing consumers may continue reading `.image`.
- For animated previews, `.image` is the first frame only.
- New consumers use `.media`.
- Do not make bytes mandatory for old image-only previews.
- Add a serialization helper for any future JSON bridge; do not make the in-process API base64-encode bytes unnecessarily.

---

## 7. Decoder registry

Create `shared/preview/registry.py`.

The registry must separate:

1. decoder architecture;
2. weight asset;
3. supported WanGP model architectures;
4. latent adapter;
5. default decode policy.

Example logical record:

```python
TAELTX23 = PreviewDecoderSpec(
    decoder_id="taeltx2_3",
    backend="taehv",
    filename="taeltx2_3.safetensors",
    source_repo="madebyollin/taehv",
    source_revision="<PINNED_COMMIT>",
    sha256="<PIN_BEFORE_MERGE>",
    size_bytes=23_531_296,
    license_id="MIT",
    latent_channels=128,
    patch_size=4,
    encoder_time_downscale=(True, True, True),
    decoder_time_upscale=(True, True, True),
    output_range=(0.0, 1.0),
    decoder_layout="NTCHW",
    compatible_architectures=frozenset({
        # Begin with the exact validated LTX-2.3 architecture IDs only.
    }),
)
```

Do not enable the registry record until:

- the exact repository revision is pinned;
- the SHA-256 is recorded;
- strict state-dict loading passes;
- a fixed-latent golden decode passes;
- the actual WanGP callback latent contract is documented.

### Model capability exposure

The model metadata exposed by WanGP should include a capability such as:

```json
{
  "capabilities": {
    "live_preview": {
      "modes": ["off", "rgb", "tae"],
      "decoders": ["taeltx2_3"]
    }
  }
}
```

The UI and API clients must derive available preview choices from this capability. Do not identify support by matching the visible model name.

For the first PR, enable the LTX‑2.3 / 22B standard Dev and Distilled profiles only. Add Edit Anything, MSR, JoyAI Echo, prompt-relay, and other derived profiles only after each path passes a smoke test confirming that its callback exposes the same unpatched video latent.

---

## 8. TAEHV code and weight handling

### Licensing

TAEHV is MIT-licensed and may be vendored with its copyright and permission notice preserved.

KJNodes is GPLv3. Use it only to understand behaviour. Do not copy its implementation, comments, class structure, or frontend protocol into WanGP. Write the WanGP implementation against the independently documented TAEHV API and WanGP’s own callback interfaces.

Add:

- `LICENSES/taehv-MIT.txt`
- an attribution entry in `THIRD_PARTY_NOTICES.md`, or the repository’s equivalent
- a source-revision comment beside the vendored code

### Suggested placement

```text
shared/preview/vendor/taehv.py
LICENSES/taehv-MIT.txt
```

Alternatively, use an external package only if it provides a stable release compatible with WanGP’s Python versions. Vendoring the small MIT module is preferable for reproducibility.

### Safetensors loader

The upstream `TAEHV` constructor uses `torch.load()` when given a checkpoint path. The initial WanGP weight is a `.safetensors` file, so do not pass the path directly to the constructor.

Create the architecture with `checkpoint_path=None`, load the state dict using `safetensors.torch.load_file()`, patch temporal grow layers through the upstream helper, and then strict-load it:

```python
from safetensors.torch import load_file

model = TAEHV(
    checkpoint_path=None,
    patch_size=4,
    latent_channels=128,
    encoder_time_downscale=(True, True, True),
    decoder_time_upscale=(True, True, True),
    decoder_space_upscale=(True, True, True),
)

state_dict = load_file(str(weight_path), device="cpu")
state_dict = model.patch_tgrow_layers(state_dict)
model.load_state_dict(state_dict, strict=True)
model.eval()
model.requires_grad_(False)
```

Do not weaken strict loading to hide a mismatch. A mismatch must disable that decoder and produce a clear install/compatibility error.

### Weight location and download

Use WanGP’s existing file locator and download-progress plumbing.

Suggested logical location:

```text
<WanGP model root>/preview_decoders/taehv/taeltx2_3.safetensors
```

Before coding the path, inspect `shared.utils.files_locator` and the Model Manager conventions. The final path must work with custom model roots and portable installs.

The download record must pin:

- immutable source revision;
- exact filename;
- size;
- SHA-256;
- MIT license attribution;
- compatible decoder ID.

No test should download the weight implicitly.

---

## 9. LTX‑2.3 latent adapter

Create `shared/preview/adapters/ltx2.py`.

### Input contract

The currently inspected LTX pipeline callback provides an unpatchified video latent in `C,T,H,W` order. The adapter must still validate at runtime:

- tensor type;
- exactly four dimensions;
- channel count equals 128;
- finite values;
- non-zero temporal and spatial dimensions;
- expected architecture/decoder mapping.

Transform:

```python
# WanGP callback: C,T,H,W
# TAEHV input: N,T,C,H,W
ntchw = latent.detach().unsqueeze(0).permute(0, 2, 1, 3, 4).contiguous()
```

Do not apply the production VAE’s mean/std transform outside the Tiny AutoEncoder. TAEHV consumes the diffusion-model latent representation directly. Confirm this with the golden test before enabling the capability.

### Decode

Use:

```python
with torch.inference_mode():
    decoded = tae.decode_video(
        ntchw.to(device=device, dtype=dtype),
        parallel=parallel_decode,
        show_progress_bar=False,
    )
```

TAEHV outputs `N,T,C,H,W` in approximately `[0,1]`.

For the full LTX temporal configuration, output frame count should follow:

```text
8 × (latent_timesteps − 1) + 1
```

Assert the actual output shape. Do not merely assume the formula.

### Frame reduction

After decoding:

1. uniformly choose no more than `max_frames`, including the first and last decoded frames;
2. resize as a batch to `max_edge`, preserving aspect ratio;
3. convert to `uint8`;
4. transfer only the selected/resized frames to CPU;
5. release decode activations before returning to the sampler.

Do not transfer all full-resolution decoded frames to CPU and then discard most of them.

### Parallel versus sequential decode

TAEHV documents that parallel temporal decoding is faster but uses more memory.

Implement `Auto` policy:

- GPU and adequate free VRAM: try parallel;
- long/high-resolution decode or low headroom: use sequential;
- CUDA OOM: delete preview activations, retry once in sequential mode or on CPU;
- second failure: disable Tiny VAE for the rest of the current generation and fall back to Fast RGB.

Never fail the main generation because preview decoding failed.

Do not call `torch.cuda.empty_cache()` on every preview. Use it only after cleaning up a preview-specific OOM or during explicit preview-model unload.

---

## 10. Capture scheduler

Create `shared/preview/scheduler.py`.

The scheduler should prevent excessive overhead while still showing early problems.

### Adaptive default

Target approximately seven useful captures per denoising pass. Use percentage-based capture thresholds rather than only `step % interval`, because early previews are disproportionately valuable.

Suggested normalized thresholds:

```python
(0.08, 0.16, 0.28, 0.43, 0.60, 0.80, 1.00)
```

Rules:

- skip the raw initial-noise callback;
- capture no more than once for each threshold;
- force the final step;
- reset thresholds when `context_id` changes;
- obey explicit Every step / Every 2 / Every 4 modes;
- avoid a capture when an encode request is already pending and the policy is latest-wins;
- preserve `force_refresh` only when it represents a meaningful pass/window transition.

For an eight-step distilled run, the implementation should normally produce around five to seven updates. For a 40-step run, it should remain around seven unless the user overrides the rate.

Record actual capture steps in benchmark output.

---

## 11. Threading, buffering, and stale-result protection

Create `shared/preview/worker.py`.

### Worker responsibilities

The background worker handles CPU-side work only in the normal GPU path:

- animated WebP encoding;
- byte-size enforcement;
- media metadata creation;
- publishing the result.

It must not own a CUDA model in v1.

### Queue behaviour

Use a dedicated bounded queue. Do not change the global `FIFOQueue` semantics in the first PR.

Recommended capacity: **1 pending job plus 1 active job**.

Submission must be non-blocking:

```python
accepted = worker.try_submit(job)
```

If full:

- increment dropped count;
- either discard the new request or atomically replace the pending request with the newer sequence;
- never block the sampler waiting for space.

Prefer **latest-pending-wins**:

- let the active encode finish;
- replace an older not-yet-started pending item with the newest item;
- publish the active result only if its token is still current.

### Generation token

Every result must be checked against:

- generation ID;
- context ID;
- sequence;
- cancellation state.

A preview from:

- a previous task;
- a previous repeat;
- an earlier sliding window;
- an earlier LTX pass;
- a cancelled generation

must be discarded before it reaches `gen["preview_media"]`.

### Cancellation

On cancel:

- mark the generation token invalid immediately;
- clear pending preview work;
- do not wait for the active WebP encode to finish;
- allow the daemon worker to complete privately;
- suppress its publish callback;
- release CPU frame buffers as soon as possible.

Application shutdown may perform a bounded worker join. User cancellation must not.

### API event coalescing

`SessionStream` is currently unbounded. Add preview-specific coalescing so a slow API consumer cannot accumulate every animated preview.

Preserve all completion/error events. For `kind == "preview"`, keep only the newest not-yet-consumed preview event.

Do not silently remove output, error, or completion events.

---

## 12. Animated WebP encoder

Create `shared/preview/encoding.py`.

Use Pillow for the MVP:

```python
first.save(
    buffer,
    format="WEBP",
    save_all=True,
    append_images=remaining,
    duration=durations_ms,
    loop=0,
    quality=quality,
    method=4,
)
```

Requirements:

- RGB frames;
- bounded dimensions;
- bounded frame count;
- `loop=0`;
- valid per-frame duration;
- output byte limit;
- first-frame static fallback if animated encoding fails.

Recommended defaults:

- max edge: 512;
- max frames: 16;
- quality: 72;
- output limit: 4 MiB;
- minimum frame duration: 50 ms;
- maximum frame duration: 500 ms.

If the byte cap is exceeded, progressively reduce in this order:

1. WebP quality;
2. frame count;
3. max edge.

Never allow unbounded retries.

### Playback timing

When `preserve_duration=True`, approximate the generated clip duration using the selected frame indices and model FPS. Otherwise use a fixed preview playback rate, initially 8 FPS.

Record both generated-video FPS and preview playback timing in metadata.

---

## 13. WanGP orchestration integration

### `wgp.py`

Keep orchestration thin.

Required changes:

1. Initialize the shared preview registry/service once.
2. Resolve effective preview options for the current task.
3. Start a generation-scoped preview session before denoising.
4. Pass the service/session into `build_callback()`.
5. In the callback:
   - continue emitting progress exactly as now;
   - if mode is `tae` and scheduler permits, call the Tiny VAE capture path;
   - if mode is `rgb`, retain the current payload path;
   - if mode is `off`, emit no preview work.
6. Publish animated results with `send_cmd("preview_media", media)`.
7. Handle the new command in the queue consumer.
8. Clear both `gen["preview"]` and `gen["preview_media"]` on output, task change, cancel, and reset.
9. End/invalidate the preview session in `finally`, including error and abort paths.
10. Release/offload the preview decoder during explicit model release or application shutdown.

Do not place TAEHV model construction, WebP encoding, registry data, or weight-download logic directly in `wgp.py`.

### Existing `generate_preview()`

Preserve it as the Fast RGB implementation and compatibility fallback.

Optional refactor:

```python
generate_preview(...) -> generate_rgb_preview(...)
```

Keep a compatibility alias if external code imports the old name.

Do not make `generate_preview()` perform GPU Tiny VAE decoding on the UI/API consumer thread.

### State keys

Add only latest-value state:

```python
gen["preview"]          # legacy first-frame PIL / RGB preview
gen["preview_media"]    # latest PreviewMedia
gen["preview_warning"]  # optional one-time message
```

Do not store a history of previews in `gen`.

---

## 14. WebUI implementation

### Rendering helper

Create a helper such as:

```python
preview_media_to_html(media: PreviewMedia) -> str
```

For animated WebP:

```html
<img
  src="data:image/webp;base64,..."
  alt="Live Tiny VAE generation preview"
  style="max-width:100%;max-height:512px;object-fit:contain"
/>
```

The existing WanGP UI already allows data-image URIs. Escape all displayed metadata.

### `refresh_preview()`

New priority:

1. `gen["preview_media"]`;
2. existing `gen["preview"]`;
3. empty HTML.

Do not send animated media through `pil_to_base64_uri(..., format="jpeg")`.

### Modal

Update the preview modal to use the same media renderer. An `<img>` can display animated WebP directly. Avoid creating a second independently encoded copy.

### Controls

Add Preview Mode near the preview UI or the most relevant generation controls. Populate its choices from model capabilities.

Recommended initial labels:

- `Off`
- `Fast RGB`
- `Tiny VAE (Animated)`

If the weight is missing:

- retain the choice with an install marker, or
- replace it with `Install Tiny VAE Preview…`.

Do not present a compatible choice and then silently do nothing.

---

## 15. Python API changes

### `shared/api.py`

- Add `PreviewMedia`.
- Extend `PreviewUpdate` with optional `media`.
- Update `_build_preview_update()` to accept:
  - existing raw latent payloads for Fast RGB;
  - an already-rendered `PreviewMedia` object.
- Add preview-event coalescing to `SessionStream`.
- Clear preview state on job preparation/reset.
- Preserve cancellation semantics.

### `shared/api_cli.py`

Handle:

```python
command == "preview_media"
```

Publish `PreviewUpdate(media=..., image=first_frame, ...)` without decoding the latent again.

Keep current `"preview"` handling for Fast RGB.

### `shared/api_webui.py`

Poll `gen["preview_media"]` first.

Replace the current deduplication key based on Python object identity with:

```python
(
    active_client_id,
    media.generation_id,
    media.context_id,
    media.sequence,
)
```

Fall back to the current PIL identity key for legacy previews.

### `docs/API.md`

Update the example:

```python
elif event.kind == "preview":
    update = event.data
    if update.media is not None:
        Path("preview.webp").write_bytes(update.media.data)
    elif update.image is not None:
        update.image.save("preview.png")
```

Document:

- media MIME type;
- bytes;
- dimensions;
- frame count;
- sequence/context IDs;
- backward compatibility;
- event coalescing;
- cancellation behaviour.

---

## 16. Configuration contract

Use a reserved non-model envelope for programmatic clients:

```json
{
  "_preview": {
    "mode": "tae",
    "device": "auto",
    "update_rate": "adaptive",
    "max_edge": 512,
    "max_frames": 16,
    "webp_quality": 72,
    "target_updates": 7,
    "preserve_duration": true
  }
}
```

Requirements:

- strip `_preview` before model-setting validation;
- store it in task/plugin metadata;
- do not include it in model inference kwargs;
- do not treat it as generation-semantic metadata;
- allow server defaults when absent;
- validate and clamp all fields;
- reject unknown modes rather than silently accepting typos.

The WebUI may store its defaults in `wgp_config.json`, but task-level API options must override them.

---

## 17. Detailed implementation phases

## Phase 0 — Audit and lock down contracts

**Goal:** establish evidence before changing behaviour.

Tasks:

1. Create `feat/tae-live-preview` from the latest `AiVS`.
2. Run and record:
   ```bash
   rg -n "prepare_preview_payload|preview_latents|generate_preview|build_callback\(|callback\(" wgp.py shared models
   ```
3. Record every model/pipeline implementation that can alter a preview payload.
4. Add temporary trace logging behind `WANGP_PREVIEW_TRACE=1`.
5. For LTX‑2.3 Dev and Distilled, record at each callback:
   - model type;
   - architecture;
   - phase/pass/window;
   - shape;
   - dtype;
   - device;
   - min/max/mean;
   - whether the tensor is packed, normalized, or unpatchified.
6. Repeat for:
   - normal text-to-video;
   - image-to-video;
   - two-stage generation;
   - one sliding-window case;
   - one prompt-relay/edit case if intended for MVP.
7. Generate baseline timings, peak VRAM, and output hash with:
   - preview off;
   - current RGB preview.
8. Pin the TAEHV source revision and compute the weight SHA-256.
9. Write a short `docs/preview/latent-contracts.md`.

**Stop conditions:**

- LTX callback latent is not a stable `C,T,H,W` diffusion latent.
- Different supported LTX profiles expose incompatible tensors.
- The exact weight cannot strict-load.
- A fixed-latent reference decode does not match the independent TAEHV invocation.

**Commit:**

```text
test(preview): lock down latent preview and API contracts
```

---

## Phase 1 — Preview types, registry, and capabilities

**Goal:** add architecture without changing runtime behaviour.

Tasks:

1. Add `shared/preview/types.py`.
2. Add `shared/preview/registry.py`.
3. Add decoder availability and capability queries.
4. Extend model metadata with live-preview capabilities.
5. Add `_preview` option parsing/validation.
6. Keep all existing behaviour defaulting to Fast RGB.
7. Add unit tests for:
   - option validation;
   - model capability filtering;
   - unsupported model behaviour;
   - registry aliases;
   - missing weight status.

**Acceptance:**

- Existing models and API schemas remain valid.
- No TAE code loads during startup.
- Unsupported models never advertise Tiny VAE mode.

**Commit:**

```text
feat(preview): add live-preview contracts and decoder registry
```

---

## Phase 2 — Vendor TAEHV and implement strict loading

**Goal:** load the initial decoder reproducibly.

Tasks:

1. Vendor the MIT TAEHV implementation or use a pinned package.
2. Add the MIT license/notice.
3. Implement safetensors loading with `checkpoint_path=None`.
4. Implement strict key/shape validation.
5. Add lazy CPU cache.
6. Add controlled device/dtype transfer.
7. Add explicit unload.
8. Add downloader/availability integration through existing WanGP utilities.
9. Add unit tests using a locally generated safetensors fixture.
10. Add an opt-in real-weight integration test.

**Acceptance:**

- Importing WanGP does not load TAE weights.
- Loading is lazy and thread-safe.
- A corrupted or incompatible file produces a clear decoder error.
- The main generation path remains usable.

**Commit:**

```text
feat(preview): add MIT TAEHV loader and weight management
```

---

## Phase 3 — LTX‑2.3 decoder adapter

**Goal:** turn one WanGP LTX latent into CPU preview frames.

Tasks:

1. Add `shared/preview/adapters/ltx2.py`.
2. Validate CTHW shape and 128 channels.
3. Convert to NTCHW.
4. Decode under `torch.inference_mode()`.
5. Implement Auto parallel/sequential policy.
6. Select frames uniformly.
7. Resize and convert selected frames to CPU `uint8`.
8. Return decode metrics.
9. Add golden and shape/range/frame-count tests.
10. Verify input latent is not mutated.

**Stop conditions:**

- Extra mean/std scaling is needed but not fully understood.
- Preview output is temporally misaligned.
- Fixed latent produces non-finite output.
- Enabling the adapter changes final generation output.

**Commit:**

```text
feat(preview): decode LTX 2.3 latents with taeltx2_3
```

---

## Phase 4 — Scheduler and bounded encoder

**Goal:** ensure preview work cannot outrun generation or cancellation.

Tasks:

1. Add adaptive capture scheduler.
2. Add generation/context tokens.
3. Add latest-pending-wins bounded worker.
4. Add animated WebP encoder.
5. Add byte/frame/dimension reduction policy.
6. Add stale-result suppression.
7. Add cancellation invalidation.
8. Add metrics.
9. Add concurrency tests with deliberately slow encoders.

**Acceptance:**

- Preview submission never waits for queue space.
- Pending queue depth is bounded.
- An old preview cannot overwrite a newer task/window.
- Cancelling prevents late publication.
- Encoder failure falls back to the first frame or RGB.

**Commit:**

```text
feat(preview): add bounded animated preview scheduler and encoder
```

---

## Phase 5 — Sampler/orchestration integration

**Goal:** activate Tiny VAE mode without contaminating model pipelines.

Tasks:

1. Resolve effective preview options in `generate_media()`.
2. Start/end a PreviewCoordinator session in `try/finally`.
3. Extend `build_callback()` with the coordinator.
4. Keep RGB mode using the existing code path.
5. Add `"preview_media"` command.
6. Update `gen` state.
7. Clear preview state on output/cancel/error/task transition.
8. Add one-time fallback warnings.
9. Integrate preview model release with existing lifecycle.
10. Run final-output equivalence tests.

**Acceptance:**

- No sampler implementation has TAE-specific code.
- Preview off behaves identically to baseline.
- Fast RGB behaves identically to baseline.
- Tiny VAE failure does not fail generation.

**Commit:**

```text
feat(wgp): integrate generation-scoped Tiny VAE previews
```

---

## Phase 6 — WebUI controls and animated rendering

**Goal:** make the feature usable in WanGP.

Tasks:

1. Add capability-driven Preview Mode choices.
2. Add advanced preview settings.
3. Add install/missing-weight UX.
4. Update `refresh_preview()`.
5. Update modal rendering.
6. Display concise metadata/fallback state.
7. Ensure the HTML update does not preserve old base64 payloads.
8. Test Firefox, Chromium, and the packaged environment.

**Acceptance:**

- Animated WebP visibly moves.
- Fast RGB still renders.
- Switching model updates available choices.
- Missing decoder is understandable and recoverable.
- Cancel remains immediately available.

**Commit:**

```text
feat(webui): render animated Tiny VAE generation previews
```

---

## Phase 7 — API compatibility and coalescing

**Goal:** expose previews to AiVS and other clients safely.

Tasks:

1. Extend `PreviewUpdate`.
2. Add preview media handling to CLI mode.
3. Add preview media handling to WebUI queue mode.
4. Coalesce queued preview events.
5. Replace identity-based deduplication for structured media.
6. Update API docs/examples.
7. Add callback/event-stream tests.
8. Verify legacy `.image` consumers.

**Acceptance:**

- Existing API example remains functional.
- New API client receives animated WebP bytes.
- A slow event consumer sees the newest preview rather than an unbounded backlog.
- Cancelling emits no post-cancel preview.

**Commit:**

```text
feat(api): expose coalesced structured live preview media
```

---

## Phase 8 — Validation and performance tuning

**Goal:** prove utility without destabilising generation.

Run on the target RTX 4070 Ti Super:

1. LTX‑2.3 Distilled, 8 steps, 121 frames.
2. LTX‑2.3 Dev, longer step count.
3. 720p and one lower-resolution case.
4. Text-to-video and image-to-video.
5. Two-stage generation.
6. Sliding-window generation.
7. Queue of at least three tasks.
8. Cancel around the second/third preview.
9. Missing, corrupt, and wrong decoder weight.
10. Forced CUDA OOM/fallback.
11. CPU-only preview mode.
12. Repeated generations to detect memory growth.

Measure:

- generation wall time;
- preview decode time;
- encode time;
- event-to-visible latency;
- peak allocated/reserved VRAM;
- WebP byte size;
- dropped preview count;
- cancellation delay;
- final-output equivalence.

Initial gates:

- target average generation overhead: **≤10%**;
- do not merge if representative overhead remains **>20%** after tuning;
- preview worker pending depth: **≤1**;
- first useful preview: by the second eligible denoising callback;
- event-to-visible latency target: **≤1.5 seconds** in Balanced mode;
- no preview-caused generation OOM in Auto mode;
- cancellation must not wait for WebP encoding;
- no sustained CPU or VRAM growth across repeated jobs.

Select final Balanced decode settings from evidence. Do not decide full/partial spatial or temporal upscaling solely by intuition.

**Commit:**

```text
test(preview): add cancellation fallback and performance coverage
```

---

## Phase 9 — Documentation and release polish

Tasks:

1. Add user documentation.
2. Add developer architecture documentation.
3. Add support table.
4. Document Tiny VAE limitations and approximate quality.
5. Document the known softness of standard `taeltx2_3`.
6. Document optional future `taeltx2_3_wide` evaluation.
7. Add third-party notices.
8. Include benchmark results and tested hardware.
9. Add troubleshooting:
   - missing decoder;
   - corrupt decoder;
   - fallback to RGB;
   - CPU mode;
   - VRAM pressure.
10. Update changelog/release notes.

**Commit:**

```text
docs(preview): document Tiny VAE live previews and model support
```

---

## 18. Test matrix

### Unit tests

- PreviewOptions defaults and validation.
- Registry lookup by architecture.
- Unsupported model hidden.
- Safetensors strict-load success/failure.
- CTHW → NTCHW conversion.
- Channel mismatch rejection.
- Output range and dtype.
- LTX frame-count formula.
- Input latent not mutated.
- Uniform frame sampling includes first/last.
- WebP contains more than one frame.
- WebP durations and loop metadata.
- Byte-limit degradation terminates.
- Scheduler thresholds.
- Bounded worker never blocks.
- Latest-pending-wins semantics.
- Generation/context token invalidation.
- Cancel suppresses publication.
- One-time fallback warning.
- API legacy image fallback.
- API preview coalescing.

### Integration tests

- Real `taeltx2_3.safetensors` load from local fixture/cache.
- Fixed-latent comparison against independent TAEHV reference call.
- LTX‑2.3 callback capture.
- Animated WebP through WebUI state.
- Animated WebP through CLI API.
- Animated WebP through WebUI-backed API.
- Model download progress.
- CUDA OOM fallback.
- Multi-task queue isolation.
- Sliding-window/pass isolation.

### Regression tests

- Preview Off generation output.
- Fast RGB output.
- Existing image models.
- Existing audio models.
- Existing completed-video preview patch.
- Queue cancel/pause/resume.
- API progress and download details.
- Settings export/import.
- Model switching and unload.

---

## 19. Final acceptance criteria

The feature is complete only when all of these are true:

- Tiny VAE mode is shown only for validated models.
- `taeltx2_3.safetensors` loads lazily and only once per cache lifecycle.
- An LTX‑2.3 generation displays genuinely animated previews at multiple denoising steps.
- Balanced mode displays at least eight useful temporal samples where the clip length permits.
- The first useful preview appears by the second eligible callback.
- Preview work is bounded and cannot accumulate indefinitely.
- A stale task/window/pass preview cannot overwrite the current preview.
- Cancel invalidates pending previews immediately.
- Preview failure never fails the generation.
- Final output and random-number behaviour are unchanged.
- Fast RGB and Off modes remain backward compatible.
- WebUI and Python API both support structured media.
- Existing API clients reading `PreviewUpdate.image` still work.
- The real weight, source revision, hash, and MIT notice are documented.
- Performance gates are met on the target RTX 4070 Ti Super.
- The PR contains no copied GPL KJNodes implementation.

---

## 20. Suggested branch and commit sequence

```bash
git switch AiVS
git pull --ff-only
git switch -c feat/tae-live-preview
```

Suggested commits:

```text
test(preview): lock down latent preview and API contracts
feat(preview): add live-preview contracts and decoder registry
feat(preview): add MIT TAEHV loader and weight management
feat(preview): decode LTX 2.3 latents with taeltx2_3
feat(preview): add bounded animated preview scheduler and encoder
feat(wgp): integrate generation-scoped Tiny VAE previews
feat(webui): render animated Tiny VAE generation previews
feat(api): expose coalesced structured live preview media
test(preview): add cancellation fallback and performance coverage
docs(preview): document Tiny VAE live previews and model support
```

Keep decoder/model-family expansion out of the initial PR.

---

## 21. Suggested pull request

**Title**

```text
feat(preview): add animated Tiny VAE live video previews
```

**Summary**

```text
Adds generation-scoped animated Tiny VAE previews to WanGP, initially
supporting validated LTX-2.3 profiles through taeltx2_3.safetensors.

The implementation introduces a generic preview decoder registry, adaptive
capture scheduling, synchronous GPU-safe TAE decoding, bounded asynchronous
WebP encoding, stale-result suppression, cancellation cleanup, WebUI rendering,
and a backward-compatible structured Python API.

The existing latent-RGB preview remains the default and fallback.
```

**PR checklist**

- [ ] LTX latent contract documented
- [ ] Source revision and weight SHA-256 pinned
- [ ] MIT notice included
- [ ] No KJNodes code copied
- [ ] Preview Off equivalence verified
- [ ] Fast RGB regression verified
- [ ] Animated WebP verified
- [ ] Cancel/stale-result tests pass
- [ ] API backward compatibility passes
- [ ] Target-hardware benchmark attached
- [ ] No representative run exceeds the performance gate
- [ ] Model support table updated

---

## 22. Agent operating rules

The implementing agent must:

- inspect before editing;
- keep `wgp.py` as orchestration, not the subsystem implementation;
- add no universal model control without a capability binding;
- preserve the existing RGB fallback;
- never let preview failure abort generation;
- never perform background CUDA decoding in v1;
- never hand a mutable/in-flight GPU latent to another thread;
- never persist temporal TAE decoder state across denoising steps;
- never weaken strict state-dict loading;
- never silently apply `taeltx2_3` to old LTX‑2 / 19B models;
- never introduce an unbounded preview queue;
- never wait for preview encoding during cancellation;
- never mutate latent tensors, RNG state, sampler state, or final decode settings;
- add tests with every contract change;
- record benchmark evidence before changing defaults;
- create follow-up tasks for other TAEHV model families instead of expanding scope mid-PR.

### Mandatory stop-and-investigate conditions

Stop implementation and document the evidence if:

- the callback latent layout differs from the documented contract;
- a model path appends conditioning/keyframe latents;
- the Tiny VAE output has incorrect frame count or temporal order;
- the fixed-latent golden comparison fails;
- final output changes with preview enabled;
- GPU preview causes unstable offloading or recurrent OOM;
- cancellation waits on encoding;
- the preview queue grows beyond its bound;
- a compatibility change would break existing API clients.

Do not paper over any of these with shape slicing, non-strict loading, broad exception swallowing, or hidden fallback.
