from __future__ import annotations

from pathlib import Path

import numpy as np
import matplotlib.pyplot as plt
from matplotlib.ticker import MultipleLocator, LogLocator, LogFormatterMathtext, NullFormatter

img_dir = Path("img")
img_dir.mkdir(parents=True, exist_ok=True)

def plot(
    snr: np.ndarray,
    denom_mean: np.ndarray, 
    wl: list,
    w0: float,
    snr_threshold: float = 10
    ) -> None:

    # -------------------------
    # Plot
    # -------------------------
    fig, axes = plt.subplots(
        nrows=1,
        ncols=2,
        figsize=(12, 4),
        dpi=150,
        constrained_layout=True,
    )

    # nm 用 locator
    major_locator = MultipleLocator(200)
    minor_locator = MultipleLocator(100)

    # fill 設定
    fill_color = "red"
    fill_alpha = 0.15

    # =========================
    # (a) Mean (W - D)
    # =========================
    ax = axes[0]
    ax.plot(
        wl,
        denom_mean,
        linewidth=1.5,
        label="Mean (W - D)",
    )
    ax.set_xlim(wl.min(), wl.max())
    ax.set_ylim(0, 60000)
    ax.set_xlabel("Wavelength [nm]")
    ax.set_ylabel("Mean (W - D)")
    ax.set_title("(a) Mean effective white signal")

    ax.xaxis.set_major_locator(major_locator)
    ax.xaxis.set_minor_locator(minor_locator)

    ax.grid(True, which="major", alpha=0.4)
    ax.grid(True, which="minor", alpha=0.2)
    ax.tick_params(direction="in", top=True, right=True)

    # SNR=10
    ax.axvline(
        w0,
        color="k",
        linestyle=":",
        linewidth=1.2,
        label=f"SNR = {snr_threshold} ({w0:.0f} nm)",
        )
    
    ax.axvspan(
        w0,
        wl.max(),
        color=fill_color,
        alpha=fill_alpha,
        zorder=0,
        label="Low-SNR region",
    )

    ax.legend(frameon=False, loc="lower left")

    # =========================
    # (b) Band-wise SNR
    # =========================
    ax = axes[1]
    ax.plot(
        wl,
        snr,
        linewidth=1.5,
        label="Band-wise SNR",
    )
    ax.set_xlim(wl.min(), wl.max())
    ax.set_yscale("log")
    ax.set_xlabel("Wavelength [nm]")
    ax.set_ylabel("SNR")
    ax.set_title("(b) Band-wise SNR of (W − D)")

    ax.xaxis.set_major_locator(major_locator)
    ax.xaxis.set_minor_locator(minor_locator)

    # --- log 軸設定 ---
    ax.yaxis.set_major_locator(LogLocator(base=10.0))
    ax.yaxis.set_major_formatter(LogFormatterMathtext(base=10.0))
    ax.yaxis.set_minor_locator(LogLocator(base=10.0, subs=np.arange(2, 10)))
    ax.yaxis.set_minor_formatter(NullFormatter())

    # decade 境界調整
    snr_pos = snr[np.isfinite(snr) & (snr > 0)]
    kmin = int(np.floor(np.log10(snr_pos.min())))
    kmax = int(np.ceil(np.log10(snr_pos.max())))
    if kmax - kmin < 1:
        kmin -= 1
    ax.set_ylim(10**kmin, 10**kmax)

    ax.tick_params(which="major", direction="in", top=True, right=True, length=6)
    ax.tick_params(which="minor", direction="in", top=True, right=True, length=3)

    # SNR=10 横線
    ax.axhline(
        10,
        color="k",
        linestyle="--",
        linewidth=1.2
    )

    # SNR=10
    ax.axvline(
        w0,
        color="k",
        linestyle=":",
        linewidth=1.2,
        label=f"SNR = {snr_threshold} ({w0:.0f} nm)",
        )
    
    ax.axvspan(
        w0,
        wl.max(),
        color=fill_color,
        alpha=fill_alpha,
        zorder=0,
        label="Low-SNR region"
    )

    ax.grid(True, which="major", alpha=0.4)
    ax.grid(True, which="minor", alpha=0.2)

    ax.legend(frameon=False, loc="lower left")
    plt.savefig(img_dir / "reference_snr.png")
    plt.show()
    
    print(f"\n plot saved to {img_dir / 'reference_snr.png'}")
