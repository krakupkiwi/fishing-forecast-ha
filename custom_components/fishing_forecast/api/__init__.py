"""Open-Meteo API clients + JSON->dataclass parsing.

This package may import ``aiohttp`` and ``.models`` only. It must not import
``homeassistant.components.*`` or anything from ``.scoring``. The parsing helpers
take a plain ``aiohttp.ClientSession`` so they are testable without Home Assistant
(see ``tests/fixtures/``).
"""

from __future__ import annotations
