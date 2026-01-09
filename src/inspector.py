from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Tuple

import numpy as np
import spectral.io.envi as envi
import warnings
warnings.filterwarnings("ignore", category=UserWarning, module=r"spectral\.io\.envi")

data_dir = Path("data")
data_dir.mkdir(parents=True, exist_ok=True)

def _to_int(x: Any) -> int | None:
    if x is None:
        return None
    if isinstance(x, int):
        return x
    if isinstance(x, str):
        s = x.strip()
        if s.isdigit() or (s.startswith("-") and s[1:].isdigit()):
            return int(s)
    return None


def _to_float_list(x: Any) -> list[float] | None:
    if x is None or not isinstance(x, (list, tuple)):
        return None
    out: list[float] = []
    for v in x:
        out.append(float(v))
    return out


def _stats(x: np.ndarray) -> Dict[str, float]:
    x = np.asarray(x, dtype=np.float64)
    return {
        "min": float(np.min(x)),
        "max": float(np.max(x)),
        "mean": float(np.mean(x)),
        "median": float(np.median(x)),
        "std": float(np.std(x, ddof=0)),
    }


def print_meta_summary(meta: Dict[str, Any]) -> None:
    """ENVI metadata を見やすく整形してコンソール出力する。"""
    desc = meta.get("description")
    ftype = meta.get("file type")
    sensor = meta.get("sensor type")
    acq = meta.get("acquisition date")
    interleave = meta.get("interleave")

    samples = _to_int(meta.get("samples"))
    lines = _to_int(meta.get("lines"))
    bands = _to_int(meta.get("bands"))
    default_bands = meta.get("default bands")

    dtype = meta.get("data type")
    byte_order = meta.get("byte order")
    header_offset = meta.get("header offset")

    wl = _to_float_list(meta.get("wavelength"))
    fwhm = _to_float_list(meta.get("fwhm"))

    print("=" * 72)
    print("ENVI Metadata Summary")
    print("=" * 72)

    print("\n[Identity]")
    if desc is not None:
        print(f"description        : {desc}")
    if ftype is not None:
        print(f"file type         : {ftype}")
    if sensor is not None:
        print(f"sensor type       : {sensor}")
    if acq is not None:
        print(f"acquisition date  : {acq}")

    print("\n[Layout / Shape]")
    if interleave is not None:
        print(f"interleave        : {interleave}")
    if samples is not None:
        print(f"samples           : {samples}")
    if lines is not None:
        print(f"lines             : {lines}")
    if bands is not None:
        print(f"bands             : {bands}")
    if default_bands is not None:
        print(f"default bands     : {default_bands}")

    print("\n[IO / Encoding]")
    if header_offset is not None:
        print(f"header offset     : {header_offset}")
    if dtype is not None:
        print(f"data type         : {dtype}")
    if byte_order is not None:
        print(f"byte order        : {byte_order}")

    print("\n[Spectral Axis]")
    if wl is None:
        print("wavelength        : (missing)")
    else:
        wl_arr = np.asarray(wl, dtype=np.float64)
        print(f"wavelength len    : {wl_arr.size}")
        s = _stats(wl_arr)
        print(f"wavelength stats [nm]  : min={s['min']:.2f}, max={s['max']:.2f}")
        if wl_arr.size >= 2:
            d = np.diff(wl_arr)
            ds = _stats(d)
            print(f"Δwavelength stats [nm] : min={ds['min']:.4f}, max={ds['max']:.4f}, "
                  f"mean={ds['mean']:.4f}, median={ds['median']:.4f}, std={ds['std']:.4f}")

    print("\n[FWHM]")
    if fwhm is None:
        print("fwhm              : (missing)")
    else:
        fwhm_arr = np.asarray(fwhm, dtype=np.float64)
        print(f"fwhm len          : {fwhm_arr.size}")
        s = _stats(fwhm_arr)
        print(f"fwhm stats [nm]        : min={s['min']:.2f}, max={s['max']:.2f}, "
              f"mean={s['mean']:.4f}, median={s['median']:.4f}, std={s['std']:.4f}")

    print("\n[Other keys]")
    # 長い配列は除外して、残りをキー順に列挙（値が長ければ省略）
    exclude = {"wavelength", "fwhm"}
    for k in sorted(meta.keys()):
        if k in exclude:
            continue
        v = meta[k]
        sv = str(v)
        if len(sv) > 120:
            sv = sv[:117] + "..."
        print(f"{k:<16} : {sv}")
    
    print("\n")


def load_references(white_name: str, dark_name: str) -> Tuple[np.ndarray, np.ndarray, dict]:
    white_hdr = data_dir / f"{white_name}.hdr"
    white_raw = data_dir / f"{white_name}.raw"
    dark_hdr = data_dir / f"{dark_name}.hdr"
    dark_raw = data_dir / f"{dark_name}.raw"

    white_envi = envi.open(str(white_hdr), str(white_raw))
    white = np.array(white_envi.load(), dtype=np.float32)

    dark_envi = envi.open(str(dark_hdr), str(dark_raw))
    dark = np.array(dark_envi.load(), dtype=np.float32)

    meta = dark_envi.metadata

    # ---- print summary here (optional) ----
    print_meta_summary(meta)

    return white, dark, meta


def inspect_snr(
    white: np.ndarray,
    dark: np.ndarray,
    meta: dict,
    snr_threshold: float = 10,
    eps: float = 1e-12,
) -> None:
    """
    white-dark の差分（=分母）について、バンドごとの SNR を計算し、
    SNR が閾値以下のバンド範囲を wavelength[nm] で示し、そこでの SNR 統計量も表示する。

    Notes
    -----
    - 入力 shape は (H, W, C) を想定（C=bands）。
    - SNR = mean / std を band-wise に計算する。
    """
    if white.shape != dark.shape:
        raise ValueError(f"white.shape {white.shape} != dark.shape {dark.shape}")
    if white.ndim != 3:
        raise ValueError(f"Expected white/dark to be 3D (H,W,C), got {white.ndim}D")

    # (H,W,C)
    denominator = white.astype(np.float32) - dark.astype(np.float32)

    # band-wise stats over pixels
    denom_mean = denominator.mean(axis=(0, 1))  # (C,)
    denom_std = denominator.std(axis=(0, 1))    # (C,)
    snr = denom_mean / (denom_std + eps)        # (C,)

    # wavelength axis
    if "wavelength" not in meta:
        raise KeyError('meta must contain key "wavelength"')
    wl = np.asarray(meta["wavelength"], dtype=np.float64)  # (C,)
    C = snr.shape[0]
    if wl.ndim != 1 or wl.size != C:
        raise ValueError(f"wavelength length mismatch: wl.size={wl.size}, bands={C}")

    # low-SNR mask
    low = snr <= snr_threshold
    idx = np.flatnonzero(low)

    def _stats(x: np.ndarray) -> dict[str, float]:
        x = np.asarray(x, dtype=np.float64)
        return {
            "min": float(np.min(x)),
            "max": float(np.max(x)),
            "mean": float(np.mean(x)),
            "median": float(np.median(x)),
            "std": float(np.std(x, ddof=0)),
        }

    print("=" * 72)
    print("SNR inspection (denominator = white - dark)")
    print("=" * 72)
    print(f"bands             : {C}")
    print(f"wavelength[nm]     : {wl.min():.2f} .. {wl.max():.2f}")
    print(f"snr_threshold      : {snr_threshold}")

    all_stats = _stats(snr)
    print(
        "snr (all) stats    : "
        f"min={all_stats['min']:.4f}, max={all_stats['max']:.4f}, "
        f"mean={all_stats['mean']:.4f}, median={all_stats['median']:.4f}, std={all_stats['std']:.4f}"
    )

    if idx.size == 0:
        print(f"\nlow-SNR bands      : none (snr <= {snr_threshold})")
        print("=" * 72)
        return

    lo, hi = int(idx.min()), int(idx.max())
    frac = idx.size / C

    wl_lo, wl_hi = float(wl[lo]), float(wl[hi])
    print(
        f"\nlow-SNR bands      : count={idx.size} ({frac:.2%}), "
        f"range=[{wl_lo:.2f}, {wl_hi:.2f}] nm (idx [{lo}, {hi}])"
    )

    low_stats = _stats(snr[idx])
    print(
        "snr (low) stats    : "
        f"min={low_stats['min']:.4f}, max={low_stats['max']:.4f}, "
        f"mean={low_stats['mean']:.4f}, median={low_stats['median']:.4f}, std={low_stats['std']:.4f}"
    )

    # contiguous runs (multiple bad segments)
    splits = np.where(np.diff(idx) != 1)[0] + 1
    runs = np.split(idx, splits)

    print("\nlow-SNR contiguous ranges [nm] (and idx):")
    for r in runs:
        i0, i1 = int(r[0]), int(r[-1])
        w0, w1 = float(wl[i0]), float(wl[i1])
        print(f"  - [{w0:.2f}, {w1:.2f}] nm  (idx [{i0}, {i1}], len={r.size})")
    
    return denom_mean, snr, wl, w0
    