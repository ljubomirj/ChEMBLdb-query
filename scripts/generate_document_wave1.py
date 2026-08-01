#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
import sqlite3
import subprocess
import sys
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parent.parent
SRC_ROOT = REPO_ROOT / 'src'
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from db_llm_v5.artifacts import V5ArtifactPaths, V5CaseManifest, V5CaseMetadata
from db_llm_v5.backward import run_pb_sql, run_pb_up
from db_llm_v5.io import load_prompt_pack, save_case_manifest
from db_llm_v5.provider import build_provider, resolve_profile, write_json


DB_PATH = REPO_ROOT / 'database/latest/chembl_36/chembl_36_sqlite/chembl_36.db'
CANDIDATES_PATH = REPO_ROOT / 'experiments/document_wave1_candidates_v4.8.json'
MAIN_CASES = REPO_ROOT / 'tests/cases/web_scrape_hq_cases.json'
FIXTURES_BASE = REPO_ROOT / 'tests/fixtures'
MANIFEST_ROOT = REPO_ROOT / 'tests/v5_manifests/web_scrape_hq'
DEFAULT_STAGE_REGISTRY = REPO_ROOT / 'tests/cases/web_scrape_hq_cases_v4.8_document_wave1_staging.json'
DEFAULT_FRAGMENT = REPO_ROOT / 'experiments/document_wave1_registry_fragment_v4.8.json'
DEFAULT_SUMMARY = REPO_ROOT / 'experiments/document_wave1_generated_v4.8.json'
DEFAULT_REPORT = REPO_ROOT / 'experiments/document_wave1_generated_v4.8.md'


def write_csv(sql: str, out_csv: Path) -> tuple[int, list[str]]:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        cur = conn.cursor()
        cur.execute(sql)
        cols = [d[0] for d in cur.description]
        n = 0
        with out_csv.open('w', newline='') as f:
            w = csv.DictWriter(f, fieldnames=cols, quoting=csv.QUOTE_MINIMAL)
            w.writeheader()
            for row in cur:
                n += 1
                w.writerow({c: '' if row[c] is None else str(row[c]) for c in cols})
        return n, cols
    finally:
        conn.close()


def compress_csv(path: Path) -> None:
    subprocess.run(['zstd', '-f', str(path), '-o', str(path.with_suffix('.csv.zst'))], check=True, capture_output=True)


def round_for_index(index: int, round_base: int, cases_per_round: int) -> int:
    return round_base + (index // cases_per_round)


def document_sql(document_chembl_id: str) -> str:
    return f"""SELECT DISTINCT
    MOLECULE_DICTIONARY.chembl_id,
    COMPOUND_RECORDS.compound_name,
    COMPOUND_STRUCTURES.canonical_smiles
FROM DOCS
    JOIN COMPOUND_RECORDS ON COMPOUND_RECORDS.doc_id == DOCS.doc_id
    JOIN MOLECULE_DICTIONARY
        ON MOLECULE_DICTIONARY.molregno == COMPOUND_RECORDS.molregno
    JOIN COMPOUND_STRUCTURES
        ON COMPOUND_RECORDS.molregno == COMPOUND_STRUCTURES.molregno
WHERE DOCS.chembl_id = '{document_chembl_id}'
"""


def benchmark_spec_uq(document_chembl_id: str, title: str) -> str:
    label = f"{document_chembl_id} ({title})" if title else document_chembl_id
    return (
        f"Retrieve all distinct molecules mentioned in document {label}, "
        f"returning chembl_id, compound_name, and canonical_smiles. "
        f"Only include molecules with canonical_smiles available."
    )


def placeholder_uq(document_chembl_id: str, title: str) -> str:
    if title:
        return f"Which compounds are reported in document {document_chembl_id} ({title})?"
    return f"Which compounds are reported in document {document_chembl_id}?"


def doc_text(document_chembl_id: str, title: str, journal: str, year: int | None, molecule_count: int) -> str:
    return (
        f"Document: {document_chembl_id}\n\n"
        f"Title: {title}\n"
        f"Journal: {journal}\n"
        f"Year: {year}\n"
        f"Distinct molecules with structures: {molecule_count}\n"
        f"Template family: chembl_downloader_document_molecules_export\n"
    )


def case_entry(*, case_id: str, uq: str, round_num: int, fixture_dir: Path) -> dict[str, Any]:
    return {
        'id': case_id,
        'uq': uq,
        'source_url': 'https://github.com/cthoyt/chembl-downloader/blob/main/src/chembl_downloader/queries.py',
        'source_sql_path': f'tests/fixtures/web_scrape{round_num}/{case_id}/source.sql',
        'sqlite_sql_path': f'tests/fixtures/web_scrape{round_num}/{case_id}/sqlite.sql',
        'result_csv_path': f'tests/fixtures/web_scrape{round_num}/{case_id}/result-last.csv',
        'log_path': f'tests/fixtures/web_scrape{round_num}/{case_id}/run-last.log',
        'db_path': 'database/latest/chembl_36/chembl_36_sqlite/chembl_36.db',
        'size_class': 'medium',
        'sort_keys': ['chembl_id', 'compound_name', 'canonical_smiles'],
        'column_rename_map': {},
        'normalize': {'lowercase_columns': True, 'strip_values': True, 'lowercase_values': []},
        'benchmark_spec_uq_path': str((fixture_dir / 'benchmark_spec_uq.txt').resolve()),
        'uq_style': 'realistic_uq',
    }


def build_manifest(*, case_id: str, round_num: int, title: str, columns: list[str]) -> V5CaseManifest:
    return V5CaseManifest(
        case_id=case_id,
        corpus='web_scrape_hq',
        split=None,
        db_path='database/latest/chembl_36/chembl_36_sqlite/chembl_36.db',
        artifacts=V5ArtifactPaths(
            uq_surface=f'tests/fixtures/web_scrape{round_num}/{case_id}/uq.txt',
            up_exec=f'tests/fixtures/web_scrape{round_num}/{case_id}/up_exec.txt',
            sql_gold=f'tests/fixtures/web_scrape{round_num}/{case_id}/sqlite.sql',
            res_gold=f'tests/fixtures/web_scrape{round_num}/{case_id}/ground-truth.csv.zst',
            uq_benchmark_spec=f'tests/fixtures/web_scrape{round_num}/{case_id}/benchmark_spec_uq.txt',
            source_sql=f'tests/fixtures/web_scrape{round_num}/{case_id}/source.sql',
            sqlite_sql=f'tests/fixtures/web_scrape{round_num}/{case_id}/sqlite.sql',
            documentation=f'tests/fixtures/web_scrape{round_num}/{case_id}/documentation.txt',
        ),
        metadata=V5CaseMetadata(
            family='document',
            origin='templated_from_sql',
            source_title=f'chembl_downloader document molecules instantiated for {case_id.split("_molecules_")[1].upper()}',
            source_url='https://github.com/cthoyt/chembl-downloader/blob/main/src/chembl_downloader/queries.py',
            realism_level='realistic_surface',
            ambiguity_level='unambiguous',
            size_class='medium',
            expected_output_columns=columns,
            sort_keys=columns,
            tags=['document', 'medium', 'wave1'],
            allows_multiple_sql_forms=True,
            requires_schema_alias_fidelity=False,
            normalize={'lowercase_columns': True, 'strip_values': True, 'lowercase_values': []},
            column_rename_map={},
            float_cols=[],
            int_cols=[],
            float_tol=1e-6,
            notes=f'Staged document wave-1 case generated from grounded SQL. {title[:160]}',
        ),
    )


def main() -> None:
    ap = argparse.ArgumentParser(description='Generate staged document wave-1 cases using grounded SQL plus PB_SQL/PB_UP.')
    ap.add_argument('--prompt-pack', default=str(REPO_ROOT / 'experiments/prompt_pack_v5.8.yaml'))
    ap.add_argument('--candidates-path', default=str(CANDIDATES_PATH))
    ap.add_argument('--base-registry', default=str(MAIN_CASES))
    ap.add_argument('--limit', type=int, default=20)
    ap.add_argument('--start-index', type=int, default=0)
    ap.add_argument('--round-base', type=int, default=72)
    ap.add_argument('--cases-per-round', type=int, default=20)
    ap.add_argument('--multi-endpoint-profile', default='zai-glm47-local-fallbacks')
    ap.add_argument('--max-tokens', type=int, default=1200)
    ap.add_argument('--temperature', type=float, default=0.2)
    ap.add_argument('--stage-registry-out', default=str(DEFAULT_STAGE_REGISTRY))
    ap.add_argument('--registry-fragment-out', default=str(DEFAULT_FRAGMENT))
    ap.add_argument('--summary-out', default=str(DEFAULT_SUMMARY))
    ap.add_argument('--report-out', default=str(DEFAULT_REPORT))
    args = ap.parse_args()

    prompt_pack = load_prompt_pack(args.prompt_pack)
    endpoint, fallback = resolve_profile(args.multi_endpoint_profile)
    if endpoint is None:
        raise ValueError('profile resolution failed')
    provider = build_provider(endpoint=endpoint, fallback=fallback)

    candidates_payload = json.loads(Path(args.candidates_path).read_text())
    candidates = candidates_payload['candidates'][args.start_index: args.start_index + args.limit]
    existing_cases = json.loads(Path(args.base_registry).read_text())
    new_entries: list[dict[str, Any]] = []
    generated: list[dict[str, Any]] = []
    failures: list[dict[str, Any]] = []

    for idx, candidate in enumerate(candidates):
        case_id = candidate['case_id']
        document_chembl_id = candidate['document_chembl_id']
        title = candidate['title']
        journal = candidate['journal']
        year = candidate['year']
        round_num = round_for_index(args.start_index + idx, args.round_base, args.cases_per_round)
        fixture_dir = FIXTURES_BASE / f'web_scrape{round_num}' / case_id
        fixture_dir.mkdir(parents=True, exist_ok=True)
        try:
            sql = document_sql(document_chembl_id)
            spec = benchmark_spec_uq(document_chembl_id, title)
            uq_seed = placeholder_uq(document_chembl_id, title)

            (fixture_dir / 'source.sql').write_text(sql)
            (fixture_dir / 'sqlite.sql').write_text(sql)
            (fixture_dir / 'benchmark_spec_uq.txt').write_text(spec + '\n')
            (fixture_dir / 'uq.txt').write_text(uq_seed + '\n')
            (fixture_dir / 'documentation.txt').write_text(doc_text(document_chembl_id, title, journal, year, candidate['molecule_count']))
            metadata = {
                'id': case_id,
                'source_title': f'chembl_downloader document molecules instantiated for {document_chembl_id}',
                'source_url': 'https://github.com/cthoyt/chembl-downloader/blob/main/src/chembl_downloader/queries.py',
                'uq_origin': 'pb_up_from_grounded_sql',
                'uq_style': 'realistic_uq',
                'uq_origin_kind': 'templated_from_sql_then_pb',
                'uq_path': f'tests/fixtures/web_scrape{round_num}/{case_id}/uq.txt',
                'benchmark_spec_uq_path': f'tests/fixtures/web_scrape{round_num}/{case_id}/benchmark_spec_uq.txt',
                'up_exec_path': f'tests/fixtures/web_scrape{round_num}/{case_id}/up_exec.txt',
                'sql_path': f'tests/fixtures/web_scrape{round_num}/{case_id}/source.sql',
                'documentation_path': f'tests/fixtures/web_scrape{round_num}/{case_id}/documentation.txt',
            }
            (fixture_dir / 'metadata.json').write_text(json.dumps(metadata, indent=2) + '\n')

            row_count, columns = write_csv(sql, fixture_dir / 'ground-truth.csv')
            compress_csv(fixture_dir / 'ground-truth.csv')

            manifest = build_manifest(case_id=case_id, round_num=round_num, title=title, columns=columns)
            pb_sql = run_pb_sql(prompt_pack=prompt_pack, manifest=manifest, repo_root=REPO_ROOT, provider=provider, max_tokens=args.max_tokens, temperature=args.temperature)
            write_json(fixture_dir / 'pb_sql.output.json', pb_sql)
            up_exec = (pb_sql.get('execution', {}).get('parsed_json', {}) or {}).get('up_exec')
            if not up_exec:
                raise ValueError('PB_SQL produced no up_exec')
            (fixture_dir / 'up_exec.txt').write_text(str(up_exec).strip() + '\n')

            pb_up = run_pb_up(prompt_pack=prompt_pack, manifest=manifest, repo_root=REPO_ROOT, provider=provider, up_exec_text=str(up_exec), max_tokens=args.max_tokens, temperature=args.temperature)
            write_json(fixture_dir / 'pb_up.output.json', pb_up)
            uq_surface = (pb_up.get('execution', {}).get('parsed_json', {}) or {}).get('uq_surface')
            if not uq_surface:
                raise ValueError('PB_UP produced no uq_surface')
            (fixture_dir / 'uq.txt').write_text(str(uq_surface).strip() + '\n')

            final_manifest = build_manifest(case_id=case_id, round_num=round_num, title=title, columns=columns)
            save_case_manifest(final_manifest, MANIFEST_ROOT / f'{case_id}.json')

            entry = case_entry(case_id=case_id, uq=str(uq_surface).strip(), round_num=round_num, fixture_dir=fixture_dir)
            new_entries.append(entry)
            generated.append({
                'case_id': case_id,
                'document_chembl_id': document_chembl_id,
                'round_num': round_num,
                'row_count': row_count,
                'fixture_dir': str(fixture_dir.resolve()),
                'manifest_path': str((MANIFEST_ROOT / f'{case_id}.json').resolve()),
            })
            print(f"[{len(generated)}/{len(candidates)}] {case_id} rows={row_count} round={round_num}", flush=True)
        except Exception as exc:
            failures.append({'case_id': case_id, 'document_chembl_id': document_chembl_id, 'error': str(exc)})
            print(f"[FAIL] {case_id}: {exc}", flush=True)

    stage_registry = existing_cases + new_entries
    Path(args.stage_registry_out).write_text(json.dumps(stage_registry, indent=2) + '\n')
    Path(args.registry_fragment_out).write_text(json.dumps(new_entries, indent=2) + '\n')
    summary = {
        'prompt_pack': str(Path(args.prompt_pack).resolve()),
        'profile': args.multi_endpoint_profile,
        'base_registry': str(Path(args.base_registry).resolve()),
        'start_index': args.start_index,
        'limit': args.limit,
        'generated_count': len(generated),
        'failure_count': len(failures),
        'generated': generated,
        'failures': failures,
        'stage_registry_out': str(Path(args.stage_registry_out).resolve()),
        'registry_fragment_out': str(Path(args.registry_fragment_out).resolve()),
    }
    Path(args.summary_out).write_text(json.dumps(summary, indent=2) + '\n')

    lines = [
        '# Document Wave 1 Generated v4.8',
        '',
        f"- Prompt pack: `{Path(args.prompt_pack).name}`",
        f"- Provider profile: `{args.multi_endpoint_profile}`",
        f"- Base registry: `{Path(args.base_registry).name}`",
        f"- Generated: `{len(generated)}`",
        f"- Failures: `{len(failures)}`",
        '',
        '## Generated cases',
        '',
    ]
    for item in generated[:40]:
        lines.append(f"- `{item['case_id']}` rows={item['row_count']} round=`web_scrape{item['round_num']}`")
    if failures:
        lines += ['', '## Failures', '']
        for item in failures:
            lines.append(f"- `{item['case_id']}` :: {item['error']}")
    Path(args.report_out).write_text('\n'.join(lines) + '\n')

    print(json.dumps({'summary_out': str(Path(args.summary_out).resolve()), 'generated_count': len(generated), 'failure_count': len(failures)}))


if __name__ == '__main__':
    main()
