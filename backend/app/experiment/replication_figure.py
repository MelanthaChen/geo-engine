import struct
import zlib
from pathlib import Path


def write_pawc_bar_chart(rows: list[dict], path: Path):
    """Write a dependency-free publication PNG of mean PAWC by strategy."""
    width, height = 1400, 800
    pixels = bytearray([255] * width * height * 3)

    def rect(x0, y0, x1, y1, color):
        for y in range(max(0, y0), min(height, y1)):
            for x in range(max(0, x0), min(width, x1)):
                offset = (y * width + x) * 3
                pixels[offset:offset + 3] = bytes(color)

    left, top, bottom = 110, 70, 680
    rect(left, top, left + 2, bottom, (30, 30, 30))
    rect(left, bottom, width - 40, bottom + 2, (30, 30, 30))
    maximum = max([row.get("pawc_mean") or 0 for row in rows] or [1]) or 1
    slot = (width - left - 80) // max(len(rows), 1)
    for index, row in enumerate(rows):
        value = row.get("pawc_mean") or 0
        bar_height = int((bottom - top - 30) * value / maximum)
        x0 = left + index * slot + slot // 5
        x1 = left + (index + 1) * slot - slot // 5
        rect(x0, bottom - bar_height, x1, bottom, (46, 111, 214))

    def chunk(kind, data):
        return struct.pack(">I", len(data)) + kind + data + struct.pack(">I", zlib.crc32(kind + data) & 0xffffffff)

    raw = b"".join(b"\x00" + bytes(pixels[y * width * 3:(y + 1) * width * 3]) for y in range(height))
    png = b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0))
    png += chunk(b"IDAT", zlib.compress(raw, 9)) + chunk(b"IEND", b"")
    path.write_bytes(png)
