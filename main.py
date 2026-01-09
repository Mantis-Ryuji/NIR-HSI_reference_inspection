from __future__ import annotations

import argparse
from src import load_references, inspect_snr, plot


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Inspect SNR of denominator (white-dark) and plot diagnostics."
    )
    p.add_argument("--white_name", type=str, required=True, help="Basename of white reference (without .hdr/.raw)")
    p.add_argument("--dark_name", type=str, required=True, help="Basename of dark reference (without .hdr/.raw)")
    p.add_argument("--snr_threshold", type=float, default=10.0, help="SNR threshold for low-SNR bands")
    p.add_argument("--eps", type=float, default=1e-12, help="Epsilon to avoid division by zero in SNR")
    return p.parse_args()


def main(
    white_name: str,
    dark_name: str,
    snr_threshold: float = 10.0,
    eps: float = 1e-12,
) -> None:
    white, dark, meta = load_references(white_name, dark_name)
    denom_mean, snr, wl, w0 = inspect_snr(white, dark, meta, snr_threshold, eps)
    plot(snr, denom_mean, wl, w0, snr_threshold)


if __name__ == "__main__":
    args = parse_args()
    main(
        white_name=args.white_name,
        dark_name=args.dark_name,
        snr_threshold=args.snr_threshold,
        eps=args.eps,
    )