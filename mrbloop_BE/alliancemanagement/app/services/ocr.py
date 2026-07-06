"""OCR service: turn screenshot bytes into text lines, fully in-memory.

Uses RapidOCR (ONNX runtime, pure pip install — no system Tesseract needed).
The engine is CPU-bound, so it runs in a worker thread to keep the event loop
free. Screenshots are never written to disk.

Each line is a dict: {"text": "ShoNuff", "confidence": 0.97, "box": [[x, y], ...]}
box is the quadrilateral RapidOCR detected the text in (4 [x, y] points),
kept so callers can group lines into rows (see services/power_matching.py).
"""
import asyncio
import logging

logger = logging.getLogger(__name__)

_engine = None  # lazy singleton; model load takes a few seconds


def _get_engine():
    global _engine
    if _engine is None:
        from rapidocr_onnxruntime import RapidOCR

        logger.info("Initialising RapidOCR engine...")
        _engine = RapidOCR()
    return _engine


def _run_ocr(image_bytes: bytes) -> list[dict]:
    engine = _get_engine()
    result, _ = engine(image_bytes)
    if not result:
        return []
    return [
        {
            "text": str(text),
            "confidence": float(score),
            "box": [[float(x), float(y)] for x, y in box],
        }
        for box, text, score in result
    ]


async def extract_lines(image_bytes: bytes) -> list[dict]:
    """Extract text lines from an image (bytes), off the event loop."""
    return await asyncio.to_thread(_run_ocr, image_bytes)
