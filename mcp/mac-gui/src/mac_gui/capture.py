"""Capture one window by id and return a small JPEG.

screencapture -l takes exactly one window, so no other app can appear in the image.
-x keeps it silent, which matters on a machine used for audio work.
"""

from __future__ import annotations

import subprocess
import tempfile
from pathlib import Path

import Quartz
from Foundation import NSURL, NSMutableData

from .apps import Refused

MAX_EDGE = 1280
JPEG_QUALITY = 0.6


def _encode(source, max_edge: int, quality: float) -> tuple[bytes, int, int]:
    full = Quartz.CGImageSourceCreateImageAtIndex(source, 0, None)
    if full is None:
        raise Refused("screencapture wrote an image that could not be read.")
    longest = max(Quartz.CGImageGetWidth(full), Quartz.CGImageGetHeight(full))
    image = Quartz.CGImageSourceCreateThumbnailAtIndex(
        source,
        0,
        {
            Quartz.kCGImageSourceCreateThumbnailFromImageAlways: True,
            Quartz.kCGImageSourceCreateThumbnailWithTransform: True,
            Quartz.kCGImageSourceThumbnailMaxPixelSize: min(max_edge, longest),
        },
    )
    data = NSMutableData.data()
    target = Quartz.CGImageDestinationCreateWithData(data, "public.jpeg", 1, None)
    Quartz.CGImageDestinationAddImage(
        target, image, {Quartz.kCGImageDestinationLossyCompressionQuality: quality}
    )
    if not Quartz.CGImageDestinationFinalize(target):
        raise Refused("JPEG encoding failed.")
    return bytes(data), Quartz.CGImageGetWidth(image), Quartz.CGImageGetHeight(image)


def capture_window(window_id: int, max_edge: int = MAX_EDGE) -> tuple[bytes, int, int]:
    """Return (jpeg_bytes, width, height), with the longest edge at most max_edge."""
    with tempfile.TemporaryDirectory(prefix="mac-gui-") as folder:
        path = Path(folder) / "window.png"
        done = subprocess.run(
            ["/usr/sbin/screencapture", "-x", "-o", "-l", str(window_id), "-t", "png", str(path)],
            capture_output=True, text=True, timeout=15, check=False,
        )
        if done.returncode != 0 or not path.exists() or path.stat().st_size == 0:
            raise Refused(
                f"screencapture failed for window {window_id}: {done.stderr.strip() or 'no image'}. "
                "The window may be minimized, or Screen Recording may be missing."
            )
        url = NSURL.fileURLWithPath_(str(path))
        source = Quartz.CGImageSourceCreateWithURL(url, None)
        if source is None:
            raise Refused("screencapture wrote an image that could not be opened.")
        return _encode(source, max_edge, JPEG_QUALITY)
