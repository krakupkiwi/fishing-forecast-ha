"""Local astronomy + solunar calculation.

``ephemeris`` is the only module allowed to import ``ephem``. Everything else
(and the coordinator) goes through the dataclass-returning helpers here so a future
swap to ``skyfield`` or a HA add-on touches one file (see docs/research.md §4.3).
"""

from __future__ import annotations
