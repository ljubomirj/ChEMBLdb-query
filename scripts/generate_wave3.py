#!/usr/bin/env python3
"""
Generate wave3 cases using v5 backward path.
Focus: human_target_molecule_smiles, target_ic50_with_pubmed_or_doi, document
"""
from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from pathlib import Path

import zstandard as zstd

REPO_ROOT = Path(__file__).resolve().parent.parent
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from compressed_io import read_text_maybe_compressed
from db_llm_v5.artifacts import V5ArtifactPaths, V5CaseManifest, V5CaseMetadata
from db_llm_v5.backward import run_pb_sql, run_pb_up
from db_llm_v5.io import load_case_manifest, load_prompt_pack
from db_llm_v5.provider import EndpointConfig, build_provider, resolve_profile
from db_llm_v5.workspace import persist_generated_step

DEFAULT_DB_PATH = REPO_ROOT / "database/latest/chembl_36/chembl_36_sqlite/chembl_36.db"
DEFAULT_PROMPT_PACK = REPO_ROOT / "experiments" / "prompt_pack_v5.9.yaml"
DEFAULT_CANDIDATES_PATH = REPO_ROOT / "experiments" / "wave3_candidates_v4.9.json"
DEFAULT_FIXTURE_BASE = "web_scrape"
DEFAULT_ROUND_BASE = 90  # Continue from wave2 which ended at 89

TEMPLATE_TYPE_MAP = {
    "human_target_molecule_smiles_export": "other",
    "target_activity_with_pubmed_or_doi": "other",
    "document_molecules_export": "document",
}

# Benchmark spec templates for each template type
BENCHMARK_SPEC_TEMPLATES = {
    "human_target_molecule_smiles_export": "Export all distinct human {target_name} compounds with their canonical SMILES from ChEMBL.",
    "target_activity_with_pubmed_or_doi": "Export all IC50 activities (in nM) for human {target_name} with provenance (PubMed ID or DOI).",
    "document_molecules_export": "Export all molecules associated with document {doc_chembl_id} from ChEMBL.",
}


def get_placeholder_uq(template: str, **kwargs) -> str:
    """Get a placeholder UQ for the template."""
    if template == "human_target_molecule_smiles_export":
        target_name = kwargs.get("target_name", "the target")
        return f"Show me all distinct compounds and their canonical SMILES for the human target {target_name}."
    elif template == "target_activity_with_pubmed_or_doi":
        target_name = kwargs.get("target_name", "the target")
        return f"Get all IC50 values (in nM) for human {target_name} with their PubMed ID or DOI provenance."
    elif template == "document_molecules_export":
        doc_chembl_id = kwargs.get("doc_chembl_id", "the document")
        return f"List all molecules and their properties associated with document {doc_chembl_id}."
    return "Query ChEMBL database."


def write_fixture(case_id: str, sql: str, db_path: Path, fixture_dir: Path) -> int:
    """Write SQL fixture and generate ground-truth CSV."""
    import csv
    import io

    fixture_dir.mkdir(parents=True, exist_ok=True)

    # Write sqlite.sql
    sql_path = fixture_dir / "sqlite.sql"
    sql_path.write_text(sql)

    # Write source.sql
    (fixture_dir / "source.sql").write_text(sql)

    # Execute SQL and write ground-truth.csv.zst
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    cur.execute(sql)
    rows = cur.fetchall()

    if not rows:
        row_count = 0
    else:
        # Write CSV with proper quoting for values containing commas/quotes/newlines
        buf = io.StringIO()
        writer = csv.writer(buf)
        writer.writerow(rows[0].keys())
        for row in rows:
            writer.writerow([str(v) if v is not None else "" for v in row])
        csv_text = buf.getvalue()

        # Compress and write
        csv_bytes = csv_text.encode("utf-8")
        compressed = zstd.ZstdCompressor().compress(csv_bytes)
        (fixture_dir / "ground-truth.csv.zst").write_bytes(compressed)
        row_count = len(rows)

    conn.close()
    return row_count


def create_manifest(
    case_id: str,
    template: str,
    sql: str,
    fixture_path: str,
    row_count: int,
    repo_root: Path,
    target_name: str | None = None,
    doc_chembl_id: str | None = None,
) -> V5CaseManifest:
    """Create a v5 case manifest."""
    family = TEMPLATE_TYPE_MAP.get(template, "other")

    # Build expected output columns from SQL
    if template == "human_target_molecule_smiles_export":
        expected_cols = ["compound_chembl_id", "canonical_smiles"]
        sort_keys = ["compound_chembl_id"]
    elif template == "target_activity_with_pubmed_or_doi":
        expected_cols = [
            "compound_chembl_id", "canonical_smiles", "compound_key", "pubmed_id_or_doi",
            "assay_description", "standard_type", "standard_relation", "standard_value",
            "standard_units", "activity_comment", "target_chembl_id", "target_name", "target_organism",
        ]
        sort_keys = expected_cols
        string_cols = ["pubmed_id_or_doi"]
    elif template == "document_molecules_export":
        expected_cols = ["molecule_chembl_id", "molecule_name", "max_phase", "molecule_type", "canonical_smiles"]
        sort_keys = ["molecule_chembl_id"]
        string_cols = []
    else:
        expected_cols = []
        sort_keys = []
        string_cols = []

    # Size class
    if row_count < 100:
        size_class = "small"
    elif row_count < 1000:
        size_class = "medium"
    elif row_count < 10000:
        size_class = "large"
    else:
        size_class = "xlarge"

    # Build benchmark spec UQ
    format_kwargs = {}
    if target_name:
        format_kwargs["target_name"] = target_name
    if doc_chembl_id:
        format_kwargs["doc_chembl_id"] = doc_chembl_id
    benchmark_spec_uq = BENCHMARK_SPEC_TEMPLATES.get(template, "").format(**format_kwargs)
    placeholder_uq = get_placeholder_uq(template, **format_kwargs)

    # Build artifact paths
    # fixture_path already includes case_id
    artifact_base = fixture_path
    artifacts = V5ArtifactPaths(
        uq_surface=f"{artifact_base}/uq.txt",
        up_exec=f"{artifact_base}/up_exec.txt",
        sql_gold=f"{artifact_base}/sqlite.sql",
        res_gold=f"{artifact_base}/ground-truth.csv.zst",
        uq_benchmark_spec=None,
        source_sql=f"{artifact_base}/source.sql",
        documentation=f"{artifact_base}/documentation.txt",
    )

    # Build metadata
    metadata = V5CaseMetadata(
        family=family,
        origin="templated_from_sql",
        source_title=f"Synthetic {template} case: {case_id}",
        source_url="synthetic_generated",
        realism_level="realistic_surface",
        ambiguity_level="unambiguous",
        size_class=size_class,
        expected_output_columns=expected_cols,
        sort_keys=sort_keys,
        string_cols=string_cols if template == "target_activity_with_pubmed_or_doi" else [],
        tags=[family, template, "wave3"],
        notes=f"Wave3 case from {template}.",
    )

    return V5CaseManifest(
        case_id=case_id,
        corpus="web_scrape_hq",
        split=None,
        db_path=str(db_path := repo_root / "database/latest/chembl_36/chembl_36_sqlite/chembl_36.db"),
        artifacts=artifacts,
        metadata=metadata,
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate wave3 cases from candidates")
    parser.add_argument("--candidates-path", default=str(DEFAULT_CANDIDATES_PATH))
    parser.add_argument("--prompt-pack", default=str(DEFAULT_PROMPT_PACK))
    parser.add_argument("--db-path", default=str(DEFAULT_DB_PATH))
    parser.add_argument("--fixture-base", default=DEFAULT_FIXTURE_BASE)
    parser.add_argument("--multi-endpoint-profile", default="zai-glm47-local-fallbacks")
    parser.add_argument("--round-base", type=int, default=90)
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    # Load candidates
    candidates_data = json.load(open(args.candidates_path))
    candidates = candidates_data["candidates"]
    if args.limit:
        candidates = candidates[:args.limit]

    print(f"Generating {len(candidates)} wave3 cases...")

    # Setup: mixed providers — remote for PB_SQL, local for PB_UP
    prompt_pack = load_prompt_pack(Path(args.prompt_pack))

    # PB_SQL provider: remote GLM-5.1 with local fallback
    sql_endpoint, sql_fallback = resolve_profile(args.multi_endpoint_profile)
    sql_provider = build_provider(endpoint=sql_endpoint, fallback=sql_fallback)

    # PB_UP provider: local nemotron (less demanding linguistic task)
    up_provider = build_provider(
        endpoint=EndpointConfig(
            provider="llamacpp",
            model="nemotron-cascade-2-30b-a3b",
            base_url="http://192.168.1.251:8081",
            temperature=0.2,
            timeout=1200,
        ),
    )
    db_path = Path(args.db_path)
    repo_root = REPO_ROOT

    # Track results
    generated_cases = []
    failures = []

    for idx, candidate in enumerate(candidates):
        case_id = candidate["case_id"]
        template = candidate["template"]
        sql = candidate["sql"]

        # Determine fixture round
        round_num = args.round_base + (idx // 10)
        fixture_dir = repo_root / "tests" / "fixtures" / f"{args.fixture_base}_{round_num}" / case_id
        fixture_relative = f"tests/fixtures/{args.fixture_base}_{round_num}/{case_id}"

        if args.dry_run:
            print(f"DRY RUN: Would generate {case_id}")
            continue

        try:
            # Write fixture and get row count
            row_count = write_fixture(case_id, sql, db_path, fixture_dir)

            # Create manifest
            manifest = create_manifest(
                case_id=case_id,
                template=template,
                sql=sql,
                fixture_path=fixture_relative,
                row_count=row_count,
                repo_root=repo_root,
                target_name=candidate.get("target_name"),
                doc_chembl_id=candidate.get("doc_chembl_id"),
            )

            # Run backward generation
            pb_sql_result = run_pb_sql(
                prompt_pack=prompt_pack,
                manifest=manifest,
                repo_root=repo_root,
                provider=sql_provider,
                max_tokens=4000,
                temperature=0.2,
            )

            up_exec = pb_sql_result["execution"]["parsed_json"].get("up_exec")
            if not up_exec:
                raise ValueError("PB_SQL produced no up_exec")

            # Write up_exec.txt
            (fixture_dir / "up_exec.txt").write_text(up_exec)

            pb_up_result = run_pb_up(
                prompt_pack=prompt_pack,
                manifest=manifest,
                repo_root=repo_root,
                provider=up_provider,
                up_exec_text=up_exec,
                max_tokens=1200,
                temperature=0.2,
            )

            uq_surface = pb_up_result["execution"]["parsed_json"].get("uq_surface")
            if not uq_surface:
                raise ValueError("PB_UP produced no uq_surface")

            # Write uq.txt
            (fixture_dir / "uq.txt").write_text(uq_surface)

            # Write benchmark_spec_uq.txt
            format_kwargs = {}
            if candidate.get("target_name"):
                format_kwargs["target_name"] = candidate["target_name"]
            if candidate.get("doc_chembl_id"):
                format_kwargs["doc_chembl_id"] = candidate["doc_chembl_id"]
            (fixture_dir / "benchmark_spec_uq.txt").write_text(
                BENCHMARK_SPEC_TEMPLATES.get(template, "").format(**format_kwargs)
            )

            # Write metadata.json
            (fixture_dir / "metadata.json").write_text(
                json.dumps(manifest.metadata.to_dict(), indent=2)
            )

            # Write documentation.txt
            (fixture_dir / "documentation.txt").write_text(
                f"Wave3 generated case from template: {template}\n"
                f"Case ID: {case_id}\n"
                f"Row count: {row_count}\n"
                f"Prompt pack: {args.prompt_pack}\n"
            )

            # Write PB outputs for reference
            (fixture_dir / "pb_sql.output.json").write_text(
                json.dumps(pb_sql_result, indent=2)
            )
            (fixture_dir / "pb_up.output.json").write_text(
                json.dumps(pb_up_result, indent=2)
            )

            # Save manifest
            manifest_path = repo_root / "tests" / "v5_manifests" / "web_scrape_hq" / f"{case_id}.json"
            manifest_path.parent.mkdir(parents=True, exist_ok=True)
            with open(manifest_path, "w") as f:
                json.dump(manifest.to_dict(), f, indent=2)

            generated_cases.append({
                "case_id": case_id,
                "template": template,
                "row_count": row_count,
                "round": round_num,
            })

            print(f"Generated {case_id}: {row_count} rows")

        except Exception as e:
            failures.append({"case_id": case_id, "error": str(e)})
            print(f"FAILED {case_id}: {e}")

    # Write summary
    output = {
        "prompt_pack": args.prompt_pack,
        "provider_profile": args.multi_endpoint_profile,
        "requested": len(candidates),
        "generated": len(generated_cases),
        "failures": len(failures),
        "cases": generated_cases,
        "failures_detail": failures,
    }

    summary_path = repo_root / "experiments" / "wave3_generated_v4.9.json"
    with open(summary_path, "w") as f:
        json.dump(output, f, indent=2)

    # Write markdown summary
    (repo_root / "experiments" / "wave3_generated_v4.9.md").write_text(
        f"# Wave3 Generated v4.9\n\n"
        f"- Prompt pack: `{args.prompt_pack}`\n"
        f"- Provider profile: `{args.multi_endpoint_profile}`\n"
        f"- Requested: {len(candidates)}\n"
        f"- Generated: {len(generated_cases)}\n"
        f"- Failures: {len(failures)}\n\n"
        f"## Generated cases\n\n"
    )
    for case in generated_cases:
        (repo_root / "experiments" / "wave3_generated_v4.9.md").open("a").write(
            f"- `{case['case_id']}` template=`{case['template']}` rows={case['row_count']} round={case['round']}\n"
        )

    if failures:
        (repo_root / "experiments" / "wave3_generated_v4.9.md").open("a").write("\n## Failures\n\n")
        for f in failures:
            (repo_root / "experiments" / "wave3_generated_v4.9.md").open("a").write(
                f"- `{f['case_id']}`: {f['error']}\n"
            )

    print(f"\nSummary written to {summary_path}")
    print(f"Generated: {len(generated_cases)}, Failures: {len(failures)}")


if __name__ == "__main__":
    main()
