"""Language detection (D76): GlotLID default, `und` below threshold.

GlotLID is the default detector; the model is loaded lazily on first real use
(installed at build time on the reference box). Below the length/confidence
threshold the result is `und`.
"""

from __future__ import annotations

_MIN_CHARS = 20  # provisional; D76 threshold TBD
_CONF_THRESHOLD = 0.5  # provisional; D76 threshold TBD


def detect_lang(text: str) -> str:
    stripped = text.strip()
    if len(stripped) < _MIN_CHARS:
        return "und"
    try:
        from glotlid import model

        lang, conf = model.predict(stripped)
        if conf >= _CONF_THRESHOLD:
            return str(lang)
    except Exception:  # noqa: BLE001 - detector is optional at M1; never crash
        return "und"
    return "und"