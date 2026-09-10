"""Pure fishing-score functions + rolling window / daily aggregation.

Every module here is framework-independent: stdlib + ``..models`` + ``..const``
only. No ``homeassistant``, no ``ephem``, no ``aiohttp``. Functions are pure where
practical and each has unit tests driven by the tables in ``docs/scoring.md``.
"""

from __future__ import annotations
