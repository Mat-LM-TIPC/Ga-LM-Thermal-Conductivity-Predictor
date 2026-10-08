"""Write a user-defined mass-percent Ga-In-Sn grid as a predictor input CSV."""

import argparse
import csv
from decimal import Decimal, InvalidOperation
import sys


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ga-min", default="75")
    parser.add_argument("--ga-max", default="90")
    parser.add_argument("--step", default="0.5")
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    try:
        lower, upper, step = map(Decimal, (args.ga_min, args.ga_max, args.step))
        if not all(x.is_finite() for x in (lower, upper, step)):
            raise ValueError("grid arguments must be finite")
        if not (0 < lower <= upper < 100 and step > 0):
            raise ValueError("require 0 < ga-min <= ga-max < 100 and step > 0")
        with open(args.output, "x", newline="", encoding="utf-8") as target:
            writer = csv.writer(target)
            writer.writerow(["sample_id", "Ga", "In", "Sn", "T_K"])
            ga, count = lower, 0
            while ga <= upper:
                indium, remainder = Decimal(0), Decimal(100) - ga
                while indium <= remainder:
                    count += 1
                    writer.writerow([count, ga, indium, remainder - indium, 298])
                    indium += step
                ga += step
        print(f"Wrote {count} mass-percent compositions.", file=sys.stderr)
    except (ValueError, InvalidOperation, OSError) as error:
        parser.error(str(error))


if __name__ == "__main__":
    main()
