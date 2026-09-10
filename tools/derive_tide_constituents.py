"""Derive tidal constituents for a station by least-squares fit to a tide-gauge
record (numpy-free). Used to build the tables in ``tide_harmonic.py``.

    python tools/derive_tide_constituents.py --uhslc 175 --name fremantle \
        --lat -32.065 --lon 115.747

Downloads the UHSLC fast-delivery hourly CSV (year,month,day,hour,mm; -32767 =
missing), fits ~25 constituents referenced to 2024-01-01T00:00Z, and prints a
``TideStation(...)`` block ready to paste. See docs/tide.md.
"""

from __future__ import annotations

import argparse
import csv
from datetime import UTC, datetime
import io
import math
import urllib.request

EPOCH = datetime(2024, 1, 1, tzinfo=UTC)

# constituent speeds, deg/hour (Doodson / IHO)
SPEEDS: dict[str, float] = {
    "SA": 0.0410686,
    "SSA": 0.0821373,
    "MM": 0.5443747,
    "MSF": 1.0158958,
    "MF": 1.0980331,
    "Q1": 13.3986609,
    "O1": 13.9430356,
    "M1": 14.4966939,
    "P1": 14.9589314,
    "K1": 15.0410686,
    "J1": 15.5854433,
    "OO1": 16.1391017,
    "2N2": 27.8953548,
    "MU2": 27.9682084,
    "N2": 28.4397295,
    "NU2": 28.5125831,
    "M2": 28.9841042,
    "LAM2": 29.4556253,
    "L2": 29.5284789,
    "T2": 29.9589333,
    "S2": 30.0,
    "K2": 30.0821373,
    "M4": 57.9682084,
    "MS4": 58.9841042,
    "MN4": 57.4238337,
    "M6": 86.9523127,
}


def _solve(a: list[list[float]], b: list[float]) -> list[float]:
    n = len(a)
    m = [[*row[:], b[i]] for i, row in enumerate(a)]
    for col in range(n):
        piv = max(range(col, n), key=lambda r: abs(m[r][col]))
        m[col], m[piv] = m[piv], m[col]
        pv = m[col][col]
        for j in range(col, n + 1):
            m[col][j] /= pv
        for r in range(n):
            if r != col and m[r][col]:
                f = m[r][col]
                for j in range(col, n + 1):
                    m[r][j] -= f * m[col][j]
    return [m[i][n] for i in range(n)]


def load_uhslc(station: int) -> list[tuple[float, float]]:
    url = f"https://uhslc.soest.hawaii.edu/data/csv/fast/hourly/h{station}.csv"
    with urllib.request.urlopen(url, timeout=120) as resp:
        text = resp.read().decode()
    pts: list[tuple[float, float]] = []
    for row in csv.reader(io.StringIO(text)):
        if len(row) < 5:
            continue
        try:
            y, mo, da, hr, mm = map(int, row[:5])
        except ValueError:
            continue
        if mm == -32767:
            continue
        hrs = (datetime(y, mo, da, hr, tzinfo=UTC) - EPOCH).total_seconds() / 3600.0
        pts.append((hrs, mm / 1000.0))
    return pts


def fit(points: list[tuple[float, float]], names: list[str]) -> list[float]:
    rows: list[list[float]] = []
    rhs: list[float] = []
    for hrs, v in points:
        row = [1.0]
        for nm in names:
            w = math.radians(SPEEDS[nm]) * hrs
            row += [math.cos(w), math.sin(w)]
        rows.append(row)
        rhs.append(v)
    nc = len(rows[0])
    ata = [[sum(rw[i] * rw[j] for rw in rows) for j in range(nc)] for i in range(nc)]
    atb = [sum(rw[i] * rhs[k] for k, rw in enumerate(rows)) for i in range(nc)]
    return _solve(ata, atb)


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--uhslc", type=int, required=True, help="UHSLC station number, e.g. 175")
    p.add_argument("--name", required=True)
    p.add_argument("--lat", type=float, required=True)
    p.add_argument("--lon", type=float, required=True)
    p.add_argument("--min-amp-mm", type=float, default=3.0)
    args = p.parse_args()

    pts = load_uhslc(args.uhslc)
    print(f"# {len(pts)} valid hourly points")
    names = list(SPEEDS)
    coef = fit(pts, names)

    lines = []
    for i, nm in enumerate(names):
        a, b = coef[1 + 2 * i], coef[2 + 2 * i]
        amp = math.hypot(a, b)
        if amp * 1000 < args.min_amp_mm:
            continue
        phase = math.degrees(math.atan2(b, a)) % 360
        lines.append((amp, f'        _c("{nm}", {SPEEDS[nm]}, {amp:.4f}, {phase:.1f}),'))
    lines.sort(key=lambda x: -x[0])

    resid = math.sqrt(
        sum((_predict(coef, names, h) - v) ** 2 for h, v in pts[-2000:]) / min(2000, len(pts))
    )
    print(f"# recent self-check RMS ~{resid * 1000:.0f} mm  (non-tidal residual floor)\n")
    print(f"{args.name.upper()} = TideStation(")
    print(f'    key="{args.name}",')
    print(f'    name="{args.name.title()}",')
    print(f"    latitude={args.lat},")
    print(f"    longitude={args.lon},")
    print(f"    mean_m={coef[0]:.3f},")
    print(f'    source="least-squares fit to UHSLC hourly gauge #{args.uhslc}",')
    print("    constituents=(")
    for _, line in lines:
        print(line)
    print("    ),")
    print(")")


def _predict(coef: list[float], names: list[str], hrs: float) -> float:
    v = coef[0]
    for i, nm in enumerate(names):
        w = math.radians(SPEEDS[nm]) * hrs
        v += coef[1 + 2 * i] * math.cos(w) + coef[2 + 2 * i] * math.sin(w)
    return v


if __name__ == "__main__":
    main()
