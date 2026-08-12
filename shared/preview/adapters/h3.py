from __future__ import annotations

import time
from typing import Any

from PIL import Image

from .ltx2 import preview_sample_count, uniform_frame_indices


def decode_h3_latent(decoder: Any, latent: Any, *, spec: Any = None, max_edge: int = 512, preview_fps: int = 16, source_fps: float | None = None, duration_seconds: float | None = None, parallel: bool = True) -> tuple[list[Image.Image], float, int]:
    import torch
    import torch.nn.functional as F

    if not torch.is_tensor(latent) or latent.ndim != 4:
        raise ValueError("H3 Tiny VAE preview expects a C,T,H,W tensor")
    if getattr(spec, "adapter_id", None) != "h3" or getattr(spec, "decoder_layout", "NTCHW") != "NTCHW":
        raise ValueError("unsupported H3 Tiny VAE decoder contract")
    if latent.shape[0] != 24 or min(latent.shape[1:]) <= 0:
        raise ValueError(f"unsupported H3 latent shape: {tuple(latent.shape)}")
    if not torch.isfinite(latent).all():
        raise ValueError("H3 latent contains non-finite values")
    device = next(decoder.parameters()).device
    dtype = next(decoder.parameters()).dtype
    ntchw = latent.detach().unsqueeze(0).permute(0, 2, 1, 3, 4).contiguous().to(device=device, dtype=dtype)
    started = time.perf_counter()
    with torch.inference_mode():
        # TAEHV.decode_video removes its t_upscale - 1 (three) warm-up frames.
        decoded = decoder.decode_video(ntchw, parallel=parallel, show_progress_bar=False)
    if decoded.ndim != 5 or decoded.shape[0] != 1 or decoded.shape[2] != 3 or decoded.shape[1] < 1:
        raise ValueError(f"unexpected taeh3 output shape: {tuple(decoded.shape)}")
    if not torch.isfinite(decoded).all():
        raise ValueError("taeh3 output contains non-finite values")
    temporal_scale = 2 ** sum(bool(value) for value in getattr(spec, "decoder_time_upscale", (False, True, True)))
    expected_frames = temporal_scale * (latent.shape[1] - 1) + 1
    if decoded.shape[1] != expected_frames:
        raise ValueError(f"unexpected taeh3 frame count: got {decoded.shape[1]}, expected {expected_frames}")
    frame_indices = uniform_frame_indices(decoded.shape[1], preview_sample_count(decoded.shape[1], preview_fps, source_fps, duration_seconds))
    selected = decoded[:, frame_indices]
    height, width = selected.shape[-2:]
    scale = min(1.0, max_edge / max(height, width))
    target_size = (max(1, round(height * scale)), max(1, round(width * scale)))
    selected = F.interpolate(selected.reshape(-1, 3, height, width), size=target_size, mode="bilinear", align_corners=False)
    selected = selected.clamp(0, 1).mul(255).round().to(torch.uint8).cpu()
    frames = [Image.fromarray(frame.permute(1, 2, 0).numpy()) for frame in selected]
    return frames, (time.perf_counter() - started) * 1000, decoded.shape[1]
