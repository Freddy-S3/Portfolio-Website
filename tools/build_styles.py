"""Compile styles/styles.scss to styles/styles.css.

Requires libsass:  py -m pip install libsass

Usage:
    py tools/build_styles.py
"""

import io
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "styles", "styles.scss")
CSS = os.path.join(ROOT, "styles", "styles.css")
MAP = os.path.join(ROOT, "styles", "styles.css.map")


def main():
    try:
        import sass
    except ImportError:
        print("libsass is not installed. Run: py -m pip install libsass")
        return 1

    css, source_map = sass.compile(
        filename=SRC,
        output_style="expanded",
        source_map_filename=MAP,
        omit_source_map_url=False,
    )
    io.open(CSS, "w", encoding="utf-8", newline="").write(css)
    io.open(MAP, "w", encoding="utf-8", newline="").write(source_map)
    print("compiled styles/styles.css")
    return 0


if __name__ == "__main__":
    sys.exit(main())
