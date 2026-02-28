#!/usr/bin/env python3
"""Build ERCT V3 RDF from merged_file.csv + World Bank indicators via R2RML.

Pipeline:
1) Prepare normalized CSV sources in data/r2rml/
2) Materialize RDF with morph-kgc using mappings/erct_v3_r2rml.ttl

This uses rr:TriplesMap-based mappings (with RML CSV logical sources).
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import time
import re
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Sequence, Tuple

import requests
from rdflib import Graph

WB_API_BASE = "https://api.worldbank.org/v2"
DEFAULT_INDICATORS = ["NY.GDP.PCAP.CD", "SP.POP.TOTL", "SP.DYN.LE00.IN"]


@dataclass
class CountryMatch:
    name: str
    iso2: str
    iso3: str


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Materialize ERCT V3 TTL from merged_file.csv and World Bank indicators."
    )
    parser.add_argument("--input-csv", type=Path, default=Path("merged_file.csv"))
    parser.add_argument("--mapping", type=Path, default=Path("mappings/erct_v3_r2rml.ttl"))
    parser.add_argument("--sources-dir", type=Path, default=Path("data/r2rml"))
    parser.add_argument("--output", type=Path, default=Path("generated/mapped_data.ttl"))
    parser.add_argument("--indicators", nargs="+", default=DEFAULT_INDICATORS)
    parser.add_argument("--start-year", type=int, default=2015)
    parser.add_argument("--end-year", type=int, default=2024)
    parser.add_argument("--timeout", type=int, default=30)
    parser.add_argument("--max-rows", type=int, default=0, help="0 = all")
    parser.add_argument(
        "--max-countries",
        type=int,
        default=0,
        help="Cap countries for WB fetch during testing (0 = all)",
    )
    parser.add_argument(
        "--prepare-only",
        action="store_true",
        help="Only generate CSV source tables; skip RDF materialization.",
    )
    args = parser.parse_args()

    if args.start_year > args.end_year:
        parser.error("--start-year must be <= --end-year")
    if not args.input_csv.exists():
        parser.error(f"Input CSV not found: {args.input_csv}")
    if not args.mapping.exists():
        parser.error(f"Mapping file not found: {args.mapping}")

    return args


def clean_text(value: object) -> str:
    if value is None:
        return ""
    text = str(value).replace("\xa0", " ").strip()
    if text.lower() in {"", "nan", "none", "null", "not specifed"}:
        return ""
    return text


def truthy_text(value: str) -> str:
    normalized = clean_text(value).lower()
    if normalized in {"yes", "y", "true", "1"}:
        return "true"
    return "false"


def slugify(value: str) -> str:
    text = clean_text(value).lower()
    text = re.sub(r"[^a-z0-9]+", "_", text)
    text = re.sub(r"_+", "_", text).strip("_")
    return text or "unknown"


def stable_id(*parts: str, size: int = 20) -> str:
    joined = "|".join(parts)
    return hashlib.sha1(joined.encode("utf-8")).hexdigest()[:size]


def wb_get_json(session: requests.Session, endpoint: str, params: Dict[str, str], timeout: int) -> list:
    last_error: Optional[Exception] = None
    for attempt in range(4):
        try:
            response = session.get(
                f"{WB_API_BASE}{endpoint}",
                params={"format": "json", **params},
                timeout=timeout,
            )
            response.raise_for_status()
            payload = response.json()
            if not isinstance(payload, list):
                raise RuntimeError(
                    f"Unexpected World Bank payload for {endpoint}: {json.dumps(payload)[:300]}"
                )
            return payload
        except (requests.RequestException, json.JSONDecodeError, RuntimeError) as exc:
            last_error = exc
            if attempt < 3:
                time.sleep(1.5 * (attempt + 1))
                continue
            break
    raise RuntimeError(f"World Bank request failed for {endpoint} with params={params}: {last_error}")


def normalize_country_key(name: str) -> str:
    key = clean_text(name).lower()
    key = key.replace("&", " and ")
    key = re.sub(r"[^a-z0-9]+", " ", key)
    key = re.sub(r"\s+", " ", key).strip()
    return key


def fetch_wb_country_lookup(session: requests.Session, timeout: int) -> Dict[str, CountryMatch]:
    payload = wb_get_json(session, "/country", {"per_page": "400"}, timeout)
    entries = payload[1] if len(payload) > 1 and isinstance(payload[1], list) else []

    lookup: Dict[str, CountryMatch] = {}
    for row in entries:
        iso2 = clean_text(row.get("iso2Code") or row.get("id"))
        iso3 = clean_text(row.get("id"))
        name = clean_text(row.get("name"))
        if not iso2 or iso2 in {"XX", "1A", "Z4"}:
            continue

        match = CountryMatch(name=name, iso2=iso2.upper(), iso3=iso3.upper())
        lookup[normalize_country_key(name)] = match
        lookup[normalize_country_key(iso2)] = match
        lookup[normalize_country_key(iso3)] = match

    # Common aliases seen in merged_file.csv or WB shorthand.
    aliases = {
        "congo dem rep": "Congo, Dem. Rep.",
        "congo rep": "Congo, Rep.",
        "egypt arab rep": "Egypt, Arab Rep.",
        "gambia the": "Gambia, The",
        "iran islamic rep": "Iran, Islamic Rep.",
        "kyrgyz republic": "Kyrgyz Republic",
        "lao pdr": "Lao PDR",
        "slovak republic": "Slovak Republic",
        "turkiye": "Turkey",
        "venezuela rb": "Venezuela, RB",
        "yemen rep": "Yemen, Rep.",
        "cote d ivoire": "Cote d'Ivoire",
    }
    for alias_key, canonical in aliases.items():
        canonical_match = lookup.get(normalize_country_key(canonical))
        if canonical_match:
            lookup[alias_key] = canonical_match

    return lookup


def resolve_country(name: str, country_lookup: Dict[str, CountryMatch]) -> Optional[CountryMatch]:
    key = normalize_country_key(name)
    if not key:
        return None
    return country_lookup.get(key)


def split_country_candidates(country: str, countries: str) -> List[str]:
    primary = clean_text(country)
    if primary:
        return [primary]

    fallback = clean_text(countries)
    if not fallback:
        return []

    if ";" in fallback:
        return [clean_text(part) for part in fallback.split(";") if clean_text(part)]
    if "|" in fallback:
        return [clean_text(part) for part in fallback.split("|") if clean_text(part)]

    return [fallback]


def fetch_indicator_meta(session: requests.Session, code: str, timeout: int) -> Tuple[str, str]:
    try:
        payload = wb_get_json(session, f"/indicator/{code}", {}, timeout)
        entries = payload[1] if len(payload) > 1 and isinstance(payload[1], list) else []
        if not entries:
            return code, ""
        row = entries[0]
        return clean_text(row.get("name") or code), clean_text(row.get("unit"))
    except Exception:
        return code, ""


def fetch_indicator_rows(
    session: requests.Session,
    iso2: str,
    indicator_code: str,
    start_year: int,
    end_year: int,
    timeout: int,
) -> Iterable[Tuple[int, str]]:
    params = {"per_page": "20000", "date": f"{start_year}:{end_year}", "page": "1"}
    endpoint = f"/country/{iso2}/indicator/{indicator_code}"

    while True:
        payload = wb_get_json(session, endpoint, params, timeout)
        meta = payload[0] if payload and isinstance(payload[0], dict) else {}
        entries = payload[1] if len(payload) > 1 and isinstance(payload[1], list) else []

        for row in entries:
            year_raw = clean_text(row.get("date"))
            value = row.get("value")
            if value is None or not year_raw.isdigit():
                continue
            year = int(year_raw)
            if start_year <= year <= end_year:
                yield year, str(value)

        page = int(meta.get("page", 1))
        pages = int(meta.get("pages", 1))
        if page >= pages:
            break
        params["page"] = str(page + 1)


def write_csv(path: Path, fieldnames: Sequence[str], rows: Iterable[Dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def prepare_sources(args: argparse.Namespace) -> Dict[str, int]:
    session = requests.Session()
    session.headers.update({"User-Agent": "InterDev-ERCT-V3-R2RML/1.0"})
    country_lookup = fetch_wb_country_lookup(session, args.timeout)

    trials: List[Dict[str, str]] = []
    randomised_trials: List[Dict[str, str]] = []
    trial_countries: List[Dict[str, str]] = []
    authors: List[Dict[str, str]] = []

    sectors: Dict[str, Dict[str, str]] = {}
    eval_methods: Dict[str, Dict[str, str]] = {}
    countries_all: Dict[str, Dict[str, str]] = {}
    countries_resolved: Dict[str, Dict[str, str]] = {}

    with args.input_csv.open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        for row_index, row in enumerate(reader, start=1):
            if args.max_rows and row_index > args.max_rows:
                break

            title = clean_text(row.get("Title"))
            abstract = clean_text(row.get("Abstract"))
            source_url = clean_text(row.get("source_url"))
            if not title and not abstract and not source_url:
                continue

            doi = clean_text(row.get("DOI"))
            if doi.lower() in {"no doi", "no doi.", "no_doi"}:
                doi = ""

            trial_id = stable_id(str(row_index), title.lower(), doi.lower(), source_url.lower(), size=24)
            evaluation_design = clean_text(row.get("Evaluation design"))
            evaluation_method = clean_text(row.get("Evaluation method")) or evaluation_design or "Unspecified"
            evaluation_method_id = slugify(evaluation_method)
            sector = clean_text(row.get("Sector")) or "Unspecified"
            sector_id = slugify(sector)

            trial_row = {
                "trial_id": trial_id,
                "title": title or f"Trial {row_index}",
                "abstract": abstract,
                "doi": doi,
                "authors_raw": clean_text(row.get("Authors")),
                "evaluation_design": evaluation_design,
                "evaluation_method": evaluation_method,
                "evaluation_method_id": evaluation_method_id,
                "sector": sector,
                "sector_id": sector_id,
                "sub_sector": clean_text(row.get("Sub-sector")),
                "project_name": clean_text(row.get("Project name")),
                "research_funding_agency": clean_text(row.get("Research funding agency")),
                "implementation_agency": clean_text(row.get("Implementation agency")),
                "keywords": clean_text(row.get("Keywords")),
                "language": clean_text(row.get("Language")),
                "open_access": clean_text(row.get("Open Access")),
                "pre_registration": clean_text(row.get("Pre-Registration")),
                "primary_dataset_availability": clean_text(row.get("Primary Dataset Availability")),
                "protocol_pre_analysis_plan": clean_text(row.get("Protocol Pre-Analysis Plan")),
                "unit_of_observation": clean_text(row.get("Unit of observation")),
                "crs_voluntary_dac_code": clean_text(row.get("CRS Voluntary DAC Code")),
                "equity_focus": clean_text(row.get("Equity focus")),
                "ethics_approval": clean_text(row.get("Ethics Approval")),
                "mixed_method": clean_text(row.get("Mixed method")),
                "additional_dataset_information": clean_text(row.get("Additional Dataset Information")),
                "secondary_dataset_name": clean_text(row.get("Secondary Dataset Name")),
                "state_province_name": clean_text(row.get("State/Province name")),
                "is_published": truthy_text(row.get("Journal Article", "")),
                "source_url": source_url,
            }
            trials.append(trial_row)

            sectors[sector_id] = {"sector_id": sector_id, "sector_name": sector}
            eval_methods[evaluation_method_id] = {
                "evaluation_method_id": evaluation_method_id,
                "evaluation_method_label": evaluation_method,
            }

            if "random" in evaluation_method.lower() or "random" in evaluation_design.lower():
                randomised_trials.append({"trial_id": trial_id})

            author_field = clean_text(row.get("Authors"))
            if author_field:
                author_names = [clean_text(a) for a in author_field.split(";") if clean_text(a)]
                if not author_names:
                    author_names = [author_field]
            else:
                author_names = []

            for author_name in author_names:
                author_id = slugify(author_name)
                if author_id == "unknown":
                    author_id = stable_id(trial_id, author_name, size=12)
                authors.append(
                    {
                        "trial_id": trial_id,
                        "author_id": author_id,
                        "author_name": author_name,
                        "author_affiliation": clean_text(row.get("Implementation agency")),
                    }
                )

            for country_raw in split_country_candidates(row.get("Country", ""), row.get("Countries", "")):
                resolved = resolve_country(country_raw, country_lookup)
                country_name = resolved.name if resolved else country_raw
                iso2 = resolved.iso2 if resolved else ""
                iso3 = resolved.iso3 if resolved else ""
                country_id = iso2.lower() if iso2 else slugify(country_name)
                if country_id == "unknown":
                    country_id = stable_id(country_name, trial_id, size=8)

                trial_countries.append(
                    {
                        "trial_id": trial_id,
                        "country_id": country_id,
                        "country_name": country_name,
                        "country_iso2": iso2,
                        "country_iso3": iso3,
                    }
                )
                countries_all[country_id] = {
                    "country_id": country_id,
                    "country_name": country_name,
                }
                if iso2:
                    countries_resolved[country_id] = {
                        "country_id": country_id,
                        "country_iso2": iso2,
                        "country_iso3": iso3,
                    }

    # De-duplicate row-based tables.
    def unique_rows(rows: List[Dict[str, str]], keys: Sequence[str]) -> List[Dict[str, str]]:
        seen = set()
        out: List[Dict[str, str]] = []
        for row in rows:
            marker = tuple(row[k] for k in keys)
            if marker in seen:
                continue
            seen.add(marker)
            out.append(row)
        return out

    authors = unique_rows(authors, ["trial_id", "author_id"])
    trial_countries = unique_rows(trial_countries, ["trial_id", "country_id"])
    randomised_trials = unique_rows(randomised_trials, ["trial_id"])

    # Build World Bank indicator table for resolved countries.
    resolved_country_rows = sorted(countries_resolved.values(), key=lambda x: x["country_id"])
    if args.max_countries:
        resolved_country_rows = resolved_country_rows[: args.max_countries]

    indicator_meta = {
        code: fetch_indicator_meta(session, code, args.timeout) for code in args.indicators
    }

    wb_rows: List[Dict[str, str]] = []
    for country_row in resolved_country_rows:
        iso2 = country_row["country_iso2"]
        country_id = country_row["country_id"]
        country_name = countries_all[country_id]["country_name"]

        for code in args.indicators:
            name, unit = indicator_meta[code]
            try:
                for year, value in fetch_indicator_rows(
                    session,
                    iso2=iso2,
                    indicator_code=code,
                    start_year=args.start_year,
                    end_year=args.end_year,
                    timeout=args.timeout,
                ):
                    # Keep only numeric values for erct:hasValue xsd:decimal.
                    value_text = clean_text(value)
                    if not re.fullmatch(r"-?\d+(?:\.\d+)?", value_text):
                        continue
                    indicator_id = stable_id(country_id, code, str(year), size=20)
                    wb_rows.append(
                        {
                            "country_id": country_id,
                            "country_iso2": iso2,
                            "country_iso3": country_row["country_iso3"],
                            "country_name": country_name,
                            "indicator_code": code,
                            "indicator_name": name,
                            "indicator_unit": unit,
                            "year": str(year),
                            "value": value_text,
                            "indicator_id": indicator_id,
                        }
                    )
            except Exception as exc:
                print(f"[warn] Skipping indicator fetch for {iso2}/{code}: {exc}", file=sys.stderr)

    wb_rows = unique_rows(wb_rows, ["indicator_id"])

    # Write source tables.
    write_csv(
        args.sources_dir / "trials.csv",
        [
            "trial_id",
            "title",
            "abstract",
            "doi",
            "authors_raw",
            "evaluation_design",
            "evaluation_method",
            "evaluation_method_id",
            "sector",
            "sector_id",
            "sub_sector",
            "project_name",
            "research_funding_agency",
            "implementation_agency",
            "keywords",
            "language",
            "open_access",
            "pre_registration",
            "primary_dataset_availability",
            "protocol_pre_analysis_plan",
            "unit_of_observation",
            "crs_voluntary_dac_code",
            "equity_focus",
            "ethics_approval",
            "mixed_method",
            "additional_dataset_information",
            "secondary_dataset_name",
            "state_province_name",
            "is_published",
            "source_url",
        ],
        trials,
    )
    write_csv(args.sources_dir / "randomised_trials.csv", ["trial_id"], randomised_trials)
    write_csv(
        args.sources_dir / "trial_countries.csv",
        ["trial_id", "country_id", "country_name", "country_iso2", "country_iso3"],
        trial_countries,
    )
    write_csv(
        args.sources_dir / "authors.csv",
        ["trial_id", "author_id", "author_name", "author_affiliation"],
        authors,
    )
    write_csv(args.sources_dir / "countries_all.csv", ["country_id", "country_name"], countries_all.values())
    write_csv(
        args.sources_dir / "countries_resolved.csv",
        ["country_id", "country_iso2", "country_iso3"],
        countries_resolved.values(),
    )
    write_csv(args.sources_dir / "sectors.csv", ["sector_id", "sector_name"], sectors.values())
    write_csv(
        args.sources_dir / "evaluation_methods.csv",
        ["evaluation_method_id", "evaluation_method_label"],
        eval_methods.values(),
    )
    write_csv(
        args.sources_dir / "world_bank_indicators.csv",
        [
            "country_id",
            "country_iso2",
            "country_iso3",
            "country_name",
            "indicator_code",
            "indicator_name",
            "indicator_unit",
            "year",
            "value",
            "indicator_id",
        ],
        wb_rows,
    )

    return {
        "trials": len(trials),
        "trial_countries": len(trial_countries),
        "countries": len(countries_all),
        "resolved_countries": len(countries_resolved),
        "authors": len(authors),
        "sectors": len(sectors),
        "evaluation_methods": len(eval_methods),
        "wb_indicator_rows": len(wb_rows),
    }


def run_morph_kgc(mapping_file: Path, sources_dir: Path, output_file: Path) -> None:
    output_file.parent.mkdir(parents=True, exist_ok=True)
    temp_nt = output_file.with_suffix(output_file.suffix + ".nt")
    sources_prefix = sources_dir.resolve().as_posix().rstrip("/") + "/"
    mapping_text = mapping_file.read_text(encoding="utf-8")
    mapping_text = mapping_text.replace("data/r2rml/", sources_prefix)

    with tempfile.NamedTemporaryFile("w", suffix=".ttl", delete=False) as mapping_tmp:
        mapping_tmp.write(mapping_text)
        mapping_tmp_path = Path(mapping_tmp.name)

    cfg = f"""[CONFIGURATION]
output_file = {temp_nt.resolve()}
output_format = N-TRIPLES

[DataSource1]
mappings = {mapping_tmp_path.resolve()}
"""

    with tempfile.NamedTemporaryFile("w", suffix=".ini", delete=False) as tmp:
        tmp.write(cfg)
        cfg_path = Path(tmp.name)

    try:
        proc = subprocess.run(
            [sys.executable, "-m", "morph_kgc", str(cfg_path)],
            capture_output=True,
            text=True,
            check=False,
        )
    finally:
        cfg_path.unlink(missing_ok=True)
        mapping_tmp_path.unlink(missing_ok=True)

    if proc.returncode != 0:
        raise RuntimeError(
            "morph-kgc failed. Install requirements and retry:\n"
            "pip install morph-kgc rdflib requests\n\n"
            f"stdout:\n{proc.stdout}\n\n"
            f"stderr:\n{proc.stderr}"
        )

    graph = Graph()
    graph.parse(temp_nt, format="nt")
    graph.bind("erct", "https://erct.adaptcentre.com/ontology#", override=True, replace=True)
    graph.bind("wb", "https://interdev.adaptcentre.com/worldbank/", override=True, replace=True)
    graph.bind("gn", "http://www.geonames.org/ontology#", override=True, replace=True)
    graph.bind("skos", "http://www.w3.org/2004/02/skos/core#", override=True, replace=True)
    graph.bind("dcterms", "http://purl.org/dc/terms/", override=True, replace=True)
    graph.bind("xsd", "http://www.w3.org/2001/XMLSchema#", override=True, replace=True)
    graph.bind("rdf", "http://www.w3.org/1999/02/22-rdf-syntax-ns#", override=True, replace=True)
    graph.bind("rdfs", "http://www.w3.org/2000/01/rdf-schema#", override=True, replace=True)
    graph.serialize(destination=output_file, format="turtle")
    temp_nt.unlink(missing_ok=True)


def main() -> None:
    args = parse_args()
    stats = prepare_sources(args)

    print("Prepared source tables:")
    for k, v in stats.items():
        print(f"- {k}: {v}")

    if args.prepare_only:
        print(f"Source CSVs written to: {args.sources_dir.resolve()}")
        return

    run_morph_kgc(args.mapping, args.sources_dir, args.output)
    print(f"Materialized RDF: {args.output.resolve()}")


if __name__ == "__main__":
    main()
