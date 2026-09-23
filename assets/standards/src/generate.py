#!/usr/bin/env python3
"""
Regenerate the "Стандарты сервиса" table PNGs from their HTML sources.

Usage:
    python3 generate.py
    (or: python3 assets/standards/src/generate.py, run from anywhere)

Requires the `playwright` Python package to be importable, with a Chromium
build available. This project's environment provides a pre-installed
Chromium via the PLAYWRIGHT_BROWSERS_PATH env var; no `playwright install`
step is needed or should be run.

Each HTML source in this directory is rendered at a fixed 1080px-wide
viewport and captured as a full-page PNG screenshot (device_scale_factor=1),
so the resulting images are exactly ~1080px wide and crisp on a phone
screen. Output PNGs are written to the parent `assets/standards/` folder,
overwriting any existing files with the same names.
"""

import os
import sys
from pathlib import Path

SRC_DIR = Path(__file__).resolve().parent
OUT_DIR = SRC_DIR.parent

VIEWPORT_WIDTH = 1080
VIEWPORT_HEIGHT = 900  # initial height; full_page screenshot grows to fit content
DEVICE_SCALE_FACTOR = 1

# Ordered list of (html filename, output png filename)
PAGES = [
    ("vneshniy_vid.html", "vneshniy_vid.png"),
    ("put_gostya_10_shagov.html", "put_gostya_10_shagov.png"),
    ("stop_frazy_vstrecha.html", "stop_frazy_vstrecha.png"),
    ("ne_govorim_pri_zakaze.html", "ne_govorim_pri_zakaze.png"),
    ("tipy_vozrazheniy.html", "tipy_vozrazheniy.png"),
    ("6_tekhnik_prodazh.html", "6_tekhnik_prodazh.png"),
    ("voprosy_obratnaya_svyaz.html", "voprosy_obratnaya_svyaz.png"),
    ("tri_urovnya_zhalob.html", "tri_urovnya_zhalob.png"),
    ("heart.html", "heart.png"),
]


def _find_chromium_executable():
    """Locate a Chromium executable under PLAYWRIGHT_BROWSERS_PATH.

    Some environments ship a Chromium build whose version doesn't match the
    installed `playwright` package's expected revision, which makes the
    default `browser_type.launch()` look for the wrong executable path. We
    fall back to explicitly locating the real chromium binary so this script
    keeps working without needing `playwright install`.
    """
    browsers_path = os.environ.get("PLAYWRIGHT_BROWSERS_PATH")
    candidates = []
    if browsers_path:
        candidates.append(Path(browsers_path) / "chromium")
    candidates.append(Path("/opt/pw-browsers/chromium"))

    for candidate in candidates:
        if candidate.exists():
            return str(candidate)
    return None


def main():
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print(
            "ERROR: the 'playwright' package is not importable.\n"
            "Install it into whatever Python/venv will run this script, e.g.:\n"
            "    pip install --break-system-packages playwright\n"
            "(Do NOT run 'playwright install' — the browser binary is already "
            "provided by PLAYWRIGHT_BROWSERS_PATH in this environment.)",
            file=sys.stderr,
        )
        sys.exit(1)

    OUT_DIR.mkdir(parents=True, exist_ok=True)

    executable_path = _find_chromium_executable()

    with sync_playwright() as p:
        launch_kwargs = {}
        if executable_path:
            launch_kwargs["executable_path"] = executable_path

        try:
            browser = p.chromium.launch(**launch_kwargs)
        except Exception:
            # Fall back to default resolution if the explicit path failed.
            browser = p.chromium.launch()

        page = browser.new_page(
            viewport={"width": VIEWPORT_WIDTH, "height": VIEWPORT_HEIGHT},
            device_scale_factor=DEVICE_SCALE_FACTOR,
        )

        for html_name, png_name in PAGES:
            html_path = SRC_DIR / html_name
            if not html_path.exists():
                print(f"WARNING: missing source {html_path}, skipping.", file=sys.stderr)
                continue

            out_path = OUT_DIR / png_name
            page.goto(html_path.as_uri())
            page.wait_for_load_state("networkidle")
            page.screenshot(path=str(out_path), full_page=True, type="png")
            print(f"generated {out_path}")

        browser.close()

    print(f"\nDone. {len(PAGES)} PNGs written to {OUT_DIR}")


if __name__ == "__main__":
    main()
