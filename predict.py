#!/usr/bin/env python3
"""Single and streaming CSV predictions from the Ga-In-Sn analytical equation."""

import argparse
import csv
import math
import os
from pathlib import Path
import sys
import tempfile

MODEL_VERSION = "ga-in-sn-sisso-prediction-1.0.0"
ATOMIC_MASSES = (69.723, 114.818, 118.710)
COEFFICIENTS = (338.236530420978, 17.311961900090623,
                -206.62289982277122, 41.12322518002994)
FIELDS = ["sample_id", "Ga", "In", "Sn", "basis", "T_K", "system",
          "x_Ga", "x_In", "x_Sn", "k_298_W_mK", "b_W_mK2", "k_W_mK",
          "temperature_mode", "status", "error"]


def predict(ga, indium, tin, temperature=298.0, basis="wt-percent",
            engineering_temperature=False):
    """Return equation estimates; compositions are percentages summing to 100.

    Temperature extension is an opt-in conditional engineering approximation.
    Phase eligibility and the applicable experimental window are assessed by
    the user. This function does not provide prediction confidence intervals.
    """
    values = tuple(float(v) for v in (ga, indium, tin))
    temperature = float(temperature)
    if basis not in ("wt-percent", "at-percent"):
        raise ValueError("basis must be wt-percent or at-percent")
    if not all(math.isfinite(v) and v >= 0 for v in values):
        raise ValueError("Ga, In and Sn must be finite, nonnegative percentages")
    if not math.isclose(math.fsum(values), 100.0, rel_tol=0, abs_tol=1e-6):
        raise ValueError("Ga + In + Sn must equal 100 percent (tolerance 1e-6)")
    if values[0] <= 0 or (values[1] == 0 and values[2] == 0):
        raise ValueError("enter a Ga-containing binary or ternary alloy")
    if not math.isfinite(temperature) or temperature <= 0:
        raise ValueError("temperature must be finite and positive, in kelvin")
    if basis == "wt-percent":
        amounts = tuple(v / m for v, m in zip(values, ATOMIC_MASSES))
    else:
        amounts = values
    total = math.fsum(amounts)
    x_ga, x_in, x_sn = (v / total for v in amounts)
    system = "Ga-In-Sn" if values[1] > 0 and values[2] > 0 else (
        "Ga-In" if values[1] > 0 else "Ga-Sn")
    a, c_ga, c_in, c_sn = COEFFICIENTS
    k298 = a * x_ga * x_in + c_ga * x_ga + c_in * x_in + c_sn * x_sn
    slope = 0.0
    mode = "reference_298K"
    if temperature != 298.0:
        if system == "Ga-Sn":
            raise ValueError("Ga-Sn supports 298 K only; no temperature slope is assigned")
        if not engineering_temperature:
            raise ValueError("non-298 K estimates require --engineering-temperature")
        slope = 0.055 if system == "Ga-In" else 0.060
        mode = "conditional_engineering"
    estimate = k298 + slope * (temperature - 298.0)
    return {"Ga": values[0], "In": values[1], "Sn": values[2], "basis": basis,
            "T_K": temperature, "system": system,
            "x_Ga": x_ga, "x_In": x_in, "x_Sn": x_sn,
            "k_298_W_mK": k298, "b_W_mK2": slope, "k_W_mK": estimate,
            "temperature_mode": mode,
            "status": "ok" if estimate > 0 else "nonpositive_equation_value",
            "error": ""}


def batch(input_path, output_path, *, basis="wt-percent", temperature=298.0,
          engineering_temperature=False, overwrite=False):
    """Stream rows to a new CSV; invalid rows are retained with an error status."""
    input_path, output_path = Path(input_path), Path(output_path)
    if input_path.resolve() == output_path.resolve():
        raise ValueError("input and output must be different files")
    if output_path.exists() and not overwrite:
        raise ValueError("output exists; choose another name or use --overwrite")
    good = bad = 0
    temporary = None
    try:
        with input_path.open(newline="", encoding="utf-8-sig") as source:
            reader = csv.DictReader(source)
            names = reader.fieldnames or []
            if len(names) != len(set(names)):
                raise ValueError("duplicate CSV column names")
            if not {"Ga", "In", "Sn"}.issubset(names):
                raise ValueError("CSV must contain Ga, In and Sn columns")
            with tempfile.NamedTemporaryFile(mode="w", newline="", encoding="utf-8",
                                             dir=output_path.parent, delete=False) as target:
                temporary = Path(target.name)
                writer = csv.DictWriter(target, fieldnames=FIELDS)
                writer.writeheader()
                for number, row in enumerate(reader, start=1):
                    sample = row.get("sample_id") or str(number)
                    row_temperature = row.get("T_K") or temperature
                    result = {"sample_id": sample, "Ga": row.get("Ga"),
                              "In": row.get("In"), "Sn": row.get("Sn"),
                              "basis": basis, "T_K": row_temperature}
                    try:
                        if None in row or any(value is None for value in row.values()):
                            raise ValueError("CSV row has a different number of fields from its header")
                        result.update(predict(row["Ga"], row["In"], row["Sn"],
                                              row_temperature, basis, engineering_temperature))
                        good += 1
                    except (ValueError, TypeError, OverflowError) as error:
                        result.update(status="error", error=str(error))
                        bad += 1
                    writer.writerow(result)
        os.replace(temporary, output_path)
        temporary = None
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)
    return good, bad


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--version", action="version", version=MODEL_VERSION)
    parser.add_argument("--ga", type=float, help="Ga percentage for a single prediction")
    parser.add_argument("--in", dest="indium", type=float, default=0, help="In percentage")
    parser.add_argument("--sn", type=float, default=0, help="Sn percentage")
    parser.add_argument("--basis", choices=["wt-percent", "at-percent"], default="wt-percent")
    parser.add_argument("--temperature", type=float, default=298.0, help="temperature in kelvin")
    parser.add_argument("--engineering-temperature", action="store_true",
                        help="enable the conditional Ga-In / Ga-In-Sn temperature approximation")
    parser.add_argument("--input", type=Path, help="input CSV for batch predictions")
    parser.add_argument("--output", type=Path, help="output CSV for batch predictions")
    parser.add_argument("--overwrite", action="store_true", help="replace an existing output CSV")
    args = parser.parse_args(argv)
    if args.input is not None:
        if args.output is None:
            parser.error("--input requires --output")
        if args.ga is not None or args.indium != 0 or args.sn != 0:
            parser.error("use CSV compositions or single-composition arguments, not both")
        try:
            good, bad = batch(args.input, args.output, basis=args.basis,
                              temperature=args.temperature,
                              engineering_temperature=args.engineering_temperature,
                              overwrite=args.overwrite)
        except (ValueError, OSError, csv.Error) as error:
            parser.error(str(error))
        print(f"Wrote {good + bad} rows: {good} calculated, {bad} invalid.", file=sys.stderr)
        return 2 if bad else 0
    if args.ga is None:
        parser.error("provide --ga for one alloy, or --input and --output for a CSV")
    if args.output is not None or args.overwrite:
        parser.error("--output and --overwrite are batch options")
    try:
        result = predict(args.ga, args.indium, args.sn, args.temperature,
                         args.basis, args.engineering_temperature)
    except (ValueError, TypeError, OverflowError) as error:
        parser.error(str(error))
    writer = csv.DictWriter(sys.stdout, fieldnames=FIELDS)
    writer.writeheader()
    writer.writerow(dict(sample_id="1", **result))
    return 0


if __name__ == "__main__":
    sys.exit(main())
