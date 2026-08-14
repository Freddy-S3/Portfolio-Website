"""Compile styles/styles.scss to styles/styles.css.

Uses dart-sass, which is what produced the committed styles.css. This matters more
than it sounds: libsass and dart-sass emit the same rules with different cosmetics
(".4s" vs "0.4s", 'Poppins' vs "Poppins", blank-line placement), so building with the
wrong one rewrites all ~500 lines of styles.css and buries the actual change in noise.
The two were out of step - the CSS was dart-sass output while this script called
libsass - so every run produced a diff nobody had asked for.

Resolution order:
    1. `sass` on PATH          (a real dart-sass install, fastest)
    2. `npx sass@<pinned>`     (no install needed; pinned so output stays stable)

Usage:
    py tools/build_styles.py
    py tools/build_styles.py --check   # fail if styles.css is out of date
"""

import argparse
import os
import shutil
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "styles", "styles.scss")
CSS = os.path.join(ROOT, "styles", "styles.css")
MAP = os.path.join(ROOT, "styles", "styles.css.map")

# Pinned: an unpinned "npx sass" would silently change formatting on any upstream
# release and reintroduce exactly the whole-file diff this script exists to avoid.
SASS_VERSION = "1.80.6"


def sass_command():
    local = shutil.which("sass")
    if local:
        return [local]
    npx = shutil.which("npx") or shutil.which("npx.cmd")
    if npx:
        return [npx, "-y", "sass@" + SASS_VERSION]
    return None


def compile_to(target):
    cmd = sass_command()
    if cmd is None:
        print("dart-sass not found. Install it with one of:")
        print("  npm install -g sass")
        print("  (or make sure npx is on PATH)")
        return None
    result = subprocess.run(
        cmd + ["--style=expanded", "--source-map", SRC, target],
        capture_output=True, text=True,
    )
    if result.returncode != 0:
        sys.stderr.write(result.stderr)
        return None
    return target


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true",
                        help="exit non-zero if styles.css is out of date")
    args = parser.parse_args()

    if args.check:
        tmp = CSS + ".check"
        try:
            if compile_to(tmp) is None:
                return 1
            # The trailing sourceMappingURL names the output file, so it always differs
            # for the temp target. Comparing it would make --check permanently red.
            def rules(path):
                with open(path, encoding="utf-8") as handle:
                    return [ln for ln in handle if "sourceMappingURL" not in ln]
            ok = rules(tmp) == rules(CSS)
            print("styles.css is up to date" if ok else
                  "styles.css is out of date; run: py tools/build_styles.py")
            return 0 if ok else 1
        finally:
            for leftover in (tmp, tmp + ".map"):
                if os.path.exists(leftover):
                    os.remove(leftover)

    if compile_to(CSS) is None:
        return 1
    print("compiled styles/styles.css")
    return 0


if __name__ == "__main__":
    sys.exit(main())
