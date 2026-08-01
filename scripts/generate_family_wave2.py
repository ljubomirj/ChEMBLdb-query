#!/usr/bin/env python3
"""Generic family wave2 generator: salts, metabolism, or document.

Reads candidates JSON, runs grounded SQL + PB_SQL + PB_UP for each.
Modeled on generate_other_wave2.py.
"""
from __future__ import annotations

import argparse
import csv
import json
import sqlite3
import subprocess
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parent.parent
SRC_ROOT = REPO_ROOT / 'src'
import sys
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from db_llm_v5.artifacts import V5ArtifactPaths, V5CaseManifest, V5CaseMetadata
from db_llm_v5.backward import run_pb_sql, run_pb_up
from db_llm_v5.io import load_prompt_pack, save_case_manifest
from db_llm_v5.provider import build_provider, resolve_profile, write_json

DB_PATH = REPO_ROOT / 'database/latest/chembl_36/chembl_36_sqlite/chembl_36.db'
FIXTURES_BASE = REPO_ROOT / 'tests/fixtures'
MANIFEST_ROOT = REPO_ROOT / 'tests/v5_manifests/web_scrape_hq'


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
    subprocess.run(['zstd', '-f', str(path), '-o', str(path.with_suffix('.csv.zst'))],
                   check=True, capture_output=True)


def round_for_index(index: int, round_base: int, cases_per_round: int) -> int:
    return round_base + (index // cases_per_round)


def size_class_for_rows(n: int) -> str:
    if n < 100: return 'small'
    if n < 10000: return 'medium'
    return 'large'


def benchmark_spec(candidate: dict, family: str) -> str:
    desc = candidate.get('description', '')
    if family == 'salts':
        return (
            f"Retrieve IC50 activity records with provenance (PubMed/DOI) for salt forms of "
            f"{candidate.get('parent_name', candidate.get('parent_chembl_id',''))} "
            f"(parent {candidate.get('parent_chembl_id','')}) against "
            f"{candidate.get('target_name', candidate.get('target_chembl_id',''))} "
            f"({candidate.get('target_chembl_id','')}). "
            f"Return compound ChEMBL ID, canonical SMILES, compound key, pubmed_id_or_doi, "
            f"assay description, standard type/relation/value/units, activity comment, "
            f"target ChEMBL ID/name/organism."
        )
    elif family == 'metabolism':
        return desc or f"Retrieve metabolism records. {candidate.get('case_id','')}"
    elif family == 'document':
        return (
            f"List distinct compound ChEMBL IDs, compound names, and canonical SMILES "
            f"for molecules reported in document {candidate.get('doc_chembl_id','')} "
            f"({candidate.get('doc_title','')})."
        )
    return desc


def placeholder_uq(candidate: dict, family: str) -> str:
    if family == 'salts':
        return f"Show IC50 data for salt forms of {candidate.get('parent_name','the compound')} against {candidate.get('target_name','the target')}."
    elif family == 'metabolism':
        return f"Show metabolism data for {candidate.get('organism') or candidate.get('enzyme_name') or 'substrates'}."
    elif family == 'document':
        return f"Which compounds are reported in document {candidate.get('doc_chembl_id','')}?"
    return candidate.get('description', 'Run this query.')


def build_manifest(case_id: str, round_num: int, candidate: dict,
                   family: str, columns: list[str], row_count: int) -> V5CaseManifest:
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
            family=family,
            origin='templated_from_sql',
            source_title=f"Synthetic {family} case: {case_id}",
            source_url='synthetic_generated',
            realism_level='realistic_surface',
            ambiguity_level='unambiguous',
            size_class=size_class_for_rows(row_count),
            expected_output_columns=columns,
            sort_keys=columns,
            tags=[family, 'wave2'],
            allows_multiple_sql_forms=True,
            requires_schema_alias_fidelity=False,
            normalize={'lowercase_columns': True, 'strip_values': True, 'lowercase_values': []},
            column_rename_map={},
            float_cols=[],
            int_cols=[],
            float_tol=1e-6,
            notes=f"Staged {family} wave-2 case.",
        ),
    )


def main() -> None:
    ap = argparse.ArgumentParser(description='Generate family wave2 cases.')
    ap.add_argument('--family', required=True, choices=['salts', 'metabolism', 'document'])
    ap.add_argument('--candidates-path', required=True)
    ap.add_argument('--base-registry', required=True)
    ap.add_argument('--prompt-pack', default=str(REPO_ROOT / 'experiments/prompt_pack_v5.9.yaml'))
    ap.add_argument('--limit', type=int, default=200)
    ap.add_argument('--start-index', type=int, default=0)
    ap.add_argument('--round-base', type=int, default=80)
    ap.add_argument('--cases-per-round', type=int, default=20)
    ap.add_argument('--multi-endpoint-profile', default='zai-glm47-local-fallbacks')
    ap.add_argument('--max-tokens', type=int, default=1200)
    ap.add_argument('--temperature', type=float, default=0.2)
    args = ap.parse_args()

    prompt_pack = load_prompt_pack(args.prompt_pack)
    endpoint, fallback = resolve_profile(args.multi_endpoint_profile)
    if endpoint is None:
        raise ValueError(f'profile resolution failed for {args.multi_endpoint_profile}')
    provider = build_provider(endpoint=endpoint, fallback=fallback)

    candidates_payload = json.loads(Path(args.candidates_path).read_text())
    candidates = candidates_payload['candidates'][args.start_index: args.start_index + args.limit]
    existing_cases = json.loads(Path(args.base_registry).read_text())
    new_entries: list[dict[str, Any]] = []
    generated: list[dict[str, Any]] = []
    failures: list[dict[str, Any]] = []

    for idx, candidate in enumerate(candidates):
        case_id = candidate['case_id']
        sql = candidate['sql']
        family = args.family
        round_num = round_for_index(args.start_index + idx, args.round_base, args.cases_per_round)
        fixture_dir = FIXTURES_BASE / f'web_scrape{round_num}' / case_id
        fixture_dir.mkdir(parents=True, exist_ok=True)
        try:
            spec = benchmark_spec(candidate, family)
            uq_seed = placeholder_uq(candidate, family)

            (fixture_dir / 'source.sql').write_text(sql + '\n')
            (fixture_dir / 'sqlite.sql').write_text(sql + '\n')
            (fixture_dir / 'benchmark_spec_uq.txt').write_text(spec + '\n')
            (fixture_dir / 'uq.txt').write_text(uq_seed + '\n')

            row_count, columns = write_csv(sql, fixture_dir / 'ground-truth.csv')
            compress_csv(fixture_dir / 'ground-truth.csv')

            if row_count < 1:
                raise ValueError(f'SQL produced {row_count} rows')

            doc_text = f"Case: {case_id}\nFamily: {family}\nRows: {row_count}\nColumns: {', '.join(columns)}\n"
            (fixture_dir / 'documentation.txt').write_text(doc_text)

            metadata = {
                'id': case_id,
                'source_title': f'Synthetic {family} case: {case_id}',
                'source_url': 'synthetic_generated',
                'uq_origin': 'pb_up_from_grounded_sql',
                'uq_style': 'realistic_uq',
            }
            (fixture_dir / 'metadata.json').write_text(json.dumps(metadata, indent=2) + '\n')

            manifest = build_manifest(case_id, round_num, candidate, family, columns, row_count)

            pb_sql_result = run_pb_sql(prompt_pack=prompt_pack, manifest=manifest, repo_root=REPO_ROOT,
                                       provider=provider, max_tokens=args.max_tokens,
                                       temperature=args.temperature)
            write_json(fixture_dir / 'pb_sql.output.json', pb_sql_result)
            up_exec = (pb_sql_result.get('execution', {}).get('parsed_json', {}) or {}).get('up_exec')
            if not up_exec:
                raise ValueError('PB_SQL produced no up_exec')
            (fixture_dir / 'up_exec.txt').write_text(str(up_exec).strip() + '\n')

            pb_up_result = run_pb_up(prompt_pack=prompt_pack, manifest=manifest, repo_root=REPO_ROOT,
                                     provider=provider, up_exec_text=str(up_exec),
                                     max_tokens=args.max_tokens, temperature=args.temperature)
            write_json(fixture_dir / 'pb_up.output.json', pb_up_result)
            uq_surface = (pb_up_result.get('execution', {}).get('parsed_json', {}) or {}).get('uq_surface')
            if not uq_surface:
                raise ValueError('PB_UP produced no uq_surface')
            (fixture_dir / 'uq.txt').write_text(str(uq_surface).strip() + '\n')

            final_manifest = build_manifest(case_id, round_num, candidate, family, columns, row_count)
            save_case_manifest(final_manifest, MANIFEST_ROOT / f'{case_id}.json')

            entry = {
                'id': case_id,
                'uq': str(uq_surface).strip(),
                'source_url': 'synthetic_generated',
                'source_sql_path': f'tests/fixtures/web_scrape{round_num}/{case_id}/source.sql',
                'sqlite_sql_path': f'tests/fixtures/web_scrape{round_num}/{case_id}/sqlite.sql',
                'result_csv_path': f'tests/fixtures/web_scrape{round_num}/{case_id}/result-last.csv',
                'log_path': f'tests/fixtures/web_scrape{round_num}/{case_id}/run-last.log',
                'db_path': 'database/latest/chembl_36/chembl_36_sqlite/chembl_36.db',
                'size_class': size_class_for_rows(row_count),
                'sort_keys': columns,
                'column_rename_map': {},
                'normalize': {'lowercase_columns': True, 'strip_values': True, 'lowercase_values': []},
                'benchmark_spec_uq_path': str((fixture_dir / 'benchmark_spec_uq.txt').resolve()),
                'uq_style': 'realistic_uq',
            }
            new_entries.append(entry)
            generated.append({
                'case_id': case_id,
                'family': family,
                'round_num': round_num,
                'row_count': row_count,
                'fixture_dir': str(fixture_dir.resolve()),
            })
            print(f"[{len(generated)}/{len(candidates)}] {case_id} rows={row_count} round={round_num}", flush=True)
        except Exception as exc:
            failures.append({'case_id': case_id, 'error': str(exc)})
            print(f"[FAIL] {case_id}: {exc}", flush=True)

    # Write outputs
    family_tag = args.family
    stage_registry = existing_cases + new_entries
    stage_path = REPO_ROOT / f'tests/cases/web_scrape_hq_cases_v4.9_{family_tag}_wave2_staging.json'
    frag_path = REPO_ROOT / f'experiments/{family_tag}_wave2_registry_fragment_v4.9.json'
    summary_path = REPO_ROOT / f'experiments/{family_tag}_wave2_generated_v4.9.json'
    report_path = REPO_ROOT / f'experiments/{family_tag}_wave2_generated_v4.9.md'

    stage_path.write_text(json.dumps(stage_registry, indent=2) + '\n')
    frag_path.write_text(json.dumps(new_entries, indent=2) + '\n')
    summary_path.write_text(json.dumps({
        'family': family_tag,
        'generated_count': len(generated),
        'failure_count': len(failures),
        'generated': generated,
        'failures': failures,
    }, indent=2) + '\n')

    lines = [f'# {family_tag.title()} Wave2 Generated v4.9', '',
             f'- Generated: {len(generated)}', f'- Failures: {len(failures)}', '']
    for item in generated:
        lines.append(f"- `{item['case_id']}` rows={item['row_count']} round={item['round_num']}")
    if failures:
        lines.extend(['', '## Failures', ''])
        for item in failures:
            lines.append(f"- `{item['case_id']}`: {item['error']}")
    report_path.write_text('\n'.join(lines) + '\n')

    print(json.dumps({'generated_count': len(generated), 'failure_count': len(failures)}, indent=2))


if __name__ == '__main__':
    main()
