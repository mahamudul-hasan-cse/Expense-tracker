"""Shrink captured PNGs (256-colour palette) so they stay well under the repo's
500 KB large-file limit. UI screenshots lose no visible detail.

    uv run --no-project --with pillow python screenshots/optimize.py ../docs/screenshots
"""

import sys
from pathlib import Path

from PIL import Image

folder = Path(sys.argv[1])
for png in sorted(folder.glob("*.png")):
    before = png.stat().st_size
    with Image.open(png) as im:
        im.convert("RGB").quantize(colors=256, method=Image.Quantize.MEDIANCUT).save(png, optimize=True)
    print(f"{png.name:<42} {before // 1024:>5} KB -> {png.stat().st_size // 1024:>4} KB")
