"""Inspect public OGLE photometry for RomanMAST's historical benchmark."""

import argparse
import csv
import math
from pathlib import Path
from statistics import median
from typing import NamedTuple
from urllib.request import urlopen


PHOTOMETRY_URL = "https://www.astrouw.edu.pl/ogle/ogle4/ews/2011/blg-0462/phot.dat"
PEAK_HJD = 2455763.327  # OGLE event page's reported time of maximum.
BASELINE_START_HJD = 2455260.5
BASELINE_END_HJD = 2455284.0
PEAK_HALF_WINDOW_DAYS = 1.5


class Measurement(NamedTuple):
    hjd: float
    i_magnitude: float
    i_magnitude_error: float
    seeing_pixels: float
    sky_level: float


def parse_photometry(text):
    measurements = []
    for line_number, raw_line in enumerate(text.splitlines(), start=1):
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        try:
            row = Measurement(*map(float, line.split()))
        except (ValueError, TypeError) as error:
            raise ValueError(f"line {line_number}: expected five numeric columns") from error
        if not all(map(math.isfinite, row)) or row.i_magnitude_error <= 0:
            raise ValueError(f"line {line_number}: expected finite values and positive magnitude error")
        measurements.append(row)
    return sorted(measurements)


def relative_flux(i_magnitude, baseline_magnitude):
    return 10 ** (0.4 * (baseline_magnitude - i_magnitude))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, help="use a previously downloaded OGLE phot.dat")
    parser.add_argument("--csv", type=Path, help="write a normalized copy of the light curve as CSV")
    args = parser.parse_args()
    if args.input and args.csv and args.input.resolve() == args.csv.resolve():
        parser.error("the input and CSV output must be different files")

    try:
        if args.input:
            text = args.input.read_text(encoding="ascii")
        else:
            with urlopen(PHOTOMETRY_URL, timeout=30) as response:
                text = response.read().decode("ascii")
        rows = parse_photometry(text)
        baseline = [row.i_magnitude for row in rows
                    if BASELINE_START_HJD <= row.hjd < BASELINE_END_HJD]
        near_peak = [row.i_magnitude for row in rows
                     if abs(row.hjd - PEAK_HJD) <= PEAK_HALF_WINDOW_DAYS]
        if not baseline or not near_peak:
            raise ValueError("the input must cover both the reference and near-peak windows")

        baseline_magnitude = median(baseline)
        near_peak_magnitude = median(near_peak)
        peak_flux_ratio = relative_flux(near_peak_magnitude, baseline_magnitude)
        if args.csv:
            with args.csv.open("w", encoding="utf-8", newline="") as output:
                writer = csv.writer(output)
                writer.writerow((*Measurement._fields, "days_from_reported_peak", "relative_i_flux"))
                for row in rows:
                    writer.writerow((*row, row.hjd - PEAK_HJD,
                                     relative_flux(row.i_magnitude, baseline_magnitude)))
    except (OSError, ValueError, OverflowError) as error:
        parser.exit(1, f"OGLE photometry: {error}\n")

    print("OGLE-2011-BLG-0462 (observed OGLE I-band photometry)")
    print(f"Measurements loaded: {len(rows)}")
    print(f"Reference window: {len(baseline)} measurements, median I = {baseline_magnitude:.3f} mag")
    print(f"Near-peak window: {len(near_peak)} measurements, median I = {near_peak_magnitude:.3f} mag")
    print(f"Near-peak / reference measured flux: {peak_flux_ratio:.2f}x")


if __name__ == "__main__":
    main()
