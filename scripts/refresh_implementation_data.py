"""Import the saved implementation-shock diagnostic for the public board.

Requires Python 3.11+. This does not solve or simulate the model. It copies curated
outputs, converts metadata to JSON with relative source paths, and packages the
response series for the browser. Existing board data is left untouched.
"""
from pathlib import Path
import argparse
import csv
import hashlib
import json
import math
import re
import shutil
import tomllib


def scalar(value):
    if value in {"true", "false"}:
        return value == "true"
    if re.fullmatch(r"[-+]?\d+", value):
        return int(value)
    try:
        number = float(value)
    except ValueError:
        return value
    assert math.isfinite(number), f"Non-finite CSV value: {value}"
    return number


def read_csv(path):
    with path.open(newline="") as stream:
        return [{key: scalar(value) for key, value in row.items()}
                for row in csv.DictReader(stream)]


def refresh_implementation(experiment_dir, site_dir=None):
    """Refresh dedicated implementation files and return the browser payload."""
    src = Path(experiment_dir).resolve()
    site = Path(site_dir or Path(__file__).resolve().parents[1] / "site").resolve()
    research = src.parents[1]
    for directory in ["data", "assets/figures", "downloads"]:
        (site / directory).mkdir(parents=True, exist_ok=True)

    def public_metadata(value):
        if isinstance(value, dict):
            return {public_metadata(key): public_metadata(item)
                    for key, item in value.items()}
        if isinstance(value, list):
            return [public_metadata(item) for item in value]
        if isinstance(value, str):
            value = value.replace(str(research) + "/", "")
            assert not any(p in value for p in ["/Users/", "/home/", "/private/", "/tmp/"]), \
                "Unrecognized local path in metadata"
        return value

    downloads, provenance = [], {}
    section = "Implementation shock"

    def source_label(path):
        return path.relative_to(research).as_posix()

    def record_file(origin, relative, label, transformation=None):
        target = site / relative
        entry = {"source": source_label(origin),
                 "source_sha256": hashlib.sha256(origin.read_bytes()).hexdigest(),
                 "sha256": hashlib.sha256(target.read_bytes()).hexdigest()}
        if transformation:
            entry["transformation"] = transformation
        provenance[relative] = entry
        downloads.append({"label": label, "file": relative,
                          "kind": target.suffix[1:].upper(), "section": section})

    csv_files = {
        "responses": "All paired responses and Monte Carlo standard errors",
        "levels": "All implementation-shock arm levels",
        "impact_decomposition": "Impact spread decomposition",
        "predictive_adherence": "Posterior predictive rule-exceedance probabilities",
        "checks": "Implementation-shock numerical checks",
    }
    tables = {}
    for name, label in csv_files.items():
        origin = src / f"{name}.csv"
        contents = origin.read_text()
        assert not any(p in contents for p in ["/Users/", "/home/", "/private/", "/tmp/"]), \
            f"Local path in {origin.name}"
        target = f"data/implementation_shock_{name}.csv"
        shutil.copyfile(origin, site / target)
        record_file(origin, target, label)
        tables[name] = read_csv(origin)

    metadata_origin = src / "experiment.toml"
    metadata = public_metadata(tomllib.loads(metadata_origin.read_text()))
    metadata["date"] = "2026-10-28"
    metadata_target = "data/implementation_shock_experiment.json"
    (site / metadata_target).write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2, allow_nan=False) + "\n")
    record_file(metadata_origin, metadata_target, "Experiment definition and source hashes",
                "TOML converted to JSON; research source paths made relative")

    for suffix, directory, label in [
        ("png", "assets/figures", "Implementation-shock response figure (PNG)"),
        ("pdf", "downloads", "Implementation-shock response figure (PDF)"),
    ]:
        origin = src / f"implementation_shock_paths.{suffix}"
        target = f"{directory}/{origin.name}"
        shutil.copyfile(origin, site / target)
        record_file(origin, target, label)

    columns = ["horizon", "response", "mcse", "baseline_mean", "shock_mean"]
    series, cases = {}, {}
    for row in tables["responses"]:
        key = "|".join([row["beta_case"], row["arm"], row["variable"]])
        series.setdefault(key, []).append([row[column] for column in columns])
        cases[row["beta_case"]] = {
            "label": "Baseline patience" if row["beta_case"] == "baseline" else "Lower patience",
            "annual_beta": row["annual_beta"], "quarterly_beta": row["quarterly_beta"],
        }
        assert row["actual_debt_pct"] == metadata["initial_debt_pct_annual"]
        assert row["prior"] == metadata["initial_prior"]
        assert row["n_paths"] == metadata["K"]
    for values in series.values():
        values.sort(key=lambda row: row[0])
        assert [row[0] for row in values] == list(range(metadata["H"]))
        for _, response, mcse, baseline, shock in values:
            assert mcse >= 0
            assert math.isclose(shock-baseline, response, rel_tol=1e-8, abs_tol=1e-10)
    assert set(cases) == {"baseline", "lower"}
    assert len(series) == 52 and len(tables["responses"]) == 2132
    assert len(tables["levels"]) == 3198
    assert len(tables["impact_decomposition"]) == len(tables["checks"]) == 6
    assert len(tables["predictive_adherence"]) == 72
    for row in tables["impact_decomposition"]:
        assert math.isclose(row["total_spread_response_bp"],
                            row["debt_first_component_bp"] + row["learning_at_new_debt_component_bp"],
                            abs_tol=1e-10)
    for row in tables["predictive_adherence"]:
        assert row["date0_excluded"] is True and row["equilibria_resolved"] is False
        for column in ["probability_excess", "probability_any_excess_through_horizon"]:
            assert 0 <= row[column] <= 1
    for row in tables["checks"]:
        assert row["debt_outside_grid_count"] == row["optimizer_calls"] == 0
        assert row["native_engine_error"] < 1e-11 and row["max_budget_error"] < 1e-10

    result = {
        "schema_version": 1,
        "metadata": metadata,
        "patience_cases": cases,
        "arms": {
            "positive": {"epsilon0": .05, "label": "Borrowing overshoot (+0.05)"},
            "negative": {"epsilon0": -.05, "label": "Borrowing undershoot (−0.05)"},
        },
        "response_columns": columns,
        "responses": series,
        "impacts": tables["impact_decomposition"],
        "predictive": tables["predictive_adherence"],
        "checks": tables["checks"],
        "downloads": downloads,
        "provenance": provenance,
    }
    output = site / "data/implementation-shock.json"
    encoded = json.dumps(result, ensure_ascii=False, separators=(",", ":"), allow_nan=False) + "\n"
    assert not any(p in encoded for p in ["/Users/", "/home/", "/private/", "/tmp/"])
    output.write_text(encoded)
    print(f"Wrote {output.name}: {len(series)} response series; "
          f"{len(result['predictive'])} predictive rows; {len(downloads)} downloads.")
    print("Verified complete horizons, paired differences, spread decomposition, "
          "probability bounds, simulation checks, and absence of local absolute paths.")
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--experiment-dir", type=Path, required=True)
    parser.add_argument("--site-dir", type=Path,
                        default=Path(__file__).resolve().parents[1] / "site")
    args = parser.parse_args()
    refresh_implementation(args.experiment_dir, args.site_dir)


if __name__ == "__main__":
    main()
