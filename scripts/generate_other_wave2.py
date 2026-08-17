#!/usr/bin/env python3
"""Generate 'other' family wave 2 cases using grounded SQL + PB_SQL + PB_UP.

Modeled directly on scripts/generate_assay_exact_wave1.py.
Reads candidates from experiments/other_wave2_candidates_v4.9.json.
For each candidate: writes fixtures, executes SQL, runs PB_SQL/PB_UP, writes manifests.
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
from db_llm_v5.provider import build_provider, resolve_profile, EndpointConfig, write_json

DB_PATH = REPO_ROOT / 'database/latest/chembl_36/chembl_36_sqlite/chembl_36.db'
CANDIDATES_PATH = REPO_ROOT / 'experiments/other_wave2_candidates_v4.9.json'
MAIN_CASES = REPO_ROOT / 'cases/registries/archive/web_scrape_hq_cases_v4.9_retargeted_staging.json'
FIXTURES_BASE = REPO_ROOT / 'tests/fixtures'
MANIFEST_ROOT = REPO_ROOT / 'tests/v5_manifests/web_scrape_hq'
DEFAULT_STAGE_REGISTRY = REPO_ROOT / 'cases/registries/archive/web_scrape_hq_cases_v4.9_other_wave2_staging.json'
DEFAULT_FRAGMENT = REPO_ROOT / 'experiments/other_wave2_registry_fragment_v4.9.json'
DEFAULT_SUMMARY = REPO_ROOT / 'experiments/other_wave2_generated_v4.9.json'
DEFAULT_REPORT = REPO_ROOT / 'experiments/other_wave2_generated_v4.9.md'


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
    if n < 100:
        return 'small'
    if n < 10000:
        return 'medium'
    return 'large'


def benchmark_spec_for_candidate(candidate: dict) -> str:
    """Generate benchmark spec UQ text from the candidate."""
    template = candidate['template']
    sql = candidate['sql']

    if template == 'human_target_molecule_smiles_export':
        return (
            f"List distinct compound ChEMBL IDs and canonical SMILES for molecules tested against "
            f"the human target {candidate.get('target_name', '')} ({candidate.get('target_chembl_id', '')}). "
            f"Only include molecules with activity in Homo sapiens assays for that target."
        )
    elif template == 'target_activity_with_pubmed_or_doi':
        return (
            f"For the human single-protein target {candidate.get('target_name', '')} ({candidate.get('target_chembl_id', '')}), "
            f"retrieve IC50 activity records with publication provenance (PubMed ID or DOI). "
            f"Return compound ChEMBL ID, canonical SMILES, compound key, pubmed_id_or_doi, "
            f"assay description, standard type/relation/value/units, activity comment, "
            f"target ChEMBL ID, target name, and target organism. "
            f"Only include non-null SMILES and provenance. Use the indexed assay_id path."
        )
    elif template == 'approved_drugs_with_indications_export':
        return (
            f"List approved phase-4 drugs with the indication '{candidate.get('efo_term', '')}'. "
            f"Return ChEMBL ID, pref_name, canonical SMILES, EFO ID, indication label, and max_phase_for_ind."
        )
    elif template == 'target_description_list':
        return (
            f"List distinct target descriptions (pref_name) for assays with organism "
            f"'{candidate.get('organism', '')}'."
        )
    elif template == 'approved_drugs_with_mechanisms_export':
        return (
            f"List approved phase-4 drugs with mechanism action_type '{candidate.get('action_type', '')}'. "
            f"Return ChEMBL ID, pref_name, canonical SMILES, max_phase, mechanism of action, action type, "
            f"and target ChEMBL ID and name."
        )
    elif template == 'drug_indications_export':
        return (
            f"List drug indications for phase-4 drugs with max_phase_for_ind = {candidate.get('max_phase', '')}. "
            f"Return drug ChEMBL ID, pref_name, mesh_id, mesh_heading, EFO ID, indication label, "
            f"and max_phase_for_ind."
        )
    else:  # other_grounded_sql_family
        return candidate.get('description', 'Execute the grounded SQL query.')


def placeholder_uq_for_candidate(candidate: dict) -> str:
    """Generate a seed UQ that will be overwritten by PB_UP."""
    template = candidate['template']
    if template == 'human_target_molecule_smiles_export':
        return f"Get SMILES for molecules active against {candidate.get('target_name', '')}."
    elif template == 'target_activity_with_pubmed_or_doi':
        return f"Show IC50 data with references for {candidate.get('target_name', '')}."
    elif template == 'approved_drugs_with_indications_export':
        return f"Which approved drugs treat {candidate.get('efo_term', '')}?"
    elif template == 'target_description_list':
        return f"List target descriptions for {candidate.get('organism', '')}."
    elif template == 'approved_drugs_with_mechanisms_export':
        return f"Which approved drugs are {candidate.get('action_type', '')}s?"
    elif template == 'drug_indications_export':
        return f"Show drug indications at phase {candidate.get('max_phase', '')}."
    else:
        return candidate.get('description', 'Run this query.')


def doc_text_for_candidate(candidate: dict, row_count: int, columns: list[str]) -> str:
    return (
        f"Case: {candidate['case_id']}\n\n"
        f"Template: {candidate['template']}\n"
        f"Description: {candidate.get('description', benchmark_spec_for_candidate(candidate))}\n"
        f"Result rows: {row_count}\n"
        f"Output columns: {', '.join(columns)}\n"
    )


def case_entry(*, case_id: str, uq: str, round_num: int, fixture_dir: Path,
               sort_keys: list[str]) -> dict[str, Any]:
    return {
        'id': case_id,
        'uq': uq,
        'source_url': 'synthetic_generated',
        'source_sql_path': f'tests/fixtures/web_scrape{round_num}/{case_id}/source.sql',
        'sqlite_sql_path': f'tests/fixtures/web_scrape{round_num}/{case_id}/sqlite.sql',
        'result_csv_path': f'tests/fixtures/web_scrape{round_num}/{case_id}/result-last.csv',
        'log_path': f'tests/fixtures/web_scrape{round_num}/{case_id}/run-last.log',
        'db_path': 'database/latest/chembl_36/chembl_36_sqlite/chembl_36.db',
        'size_class': size_class_for_rows(0),  # updated after
        'sort_keys': sort_keys,
        'column_rename_map': {},
        'normalize': {'lowercase_columns': True, 'strip_values': True, 'lowercase_values': []},
        'benchmark_spec_uq_path': str((fixture_dir / 'benchmark_spec_uq.txt').resolve()),
        'uq_style': 'realistic_uq',
    }


def build_manifest(*, case_id: str, round_num: int, fixture_dir: Path,
                   candidate: dict, columns: list[str], row_count: int) -> V5CaseManifest:
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
            family='other',
            origin='templated_from_sql',
            source_title=f"Synthetic {candidate['template']} case: {case_id}",
            source_url='synthetic_generated',
            realism_level='realistic_surface',
            ambiguity_level='unambiguous',
            size_class=size_class_for_rows(row_count),
            expected_output_columns=columns,
            sort_keys=columns,
            tags=['other', candidate['template'], 'wave2'],
            allows_multiple_sql_forms=True,
            requires_schema_alias_fidelity=False,
            normalize={'lowercase_columns': True, 'strip_values': True, 'lowercase_values': []},
            column_rename_map={},
            float_cols=[],
            int_cols=[],
            float_tol=1e-6,
            notes=f"Staged other wave-2 case from {candidate['template']}.",
        ),
    )


def main() -> None:
    ap = argparse.ArgumentParser(description='Generate staged other wave-2 cases.')
    ap.add_argument('--prompt-pack', default=str(REPO_ROOT / 'configs/prompt_packs/prompt_pack_v5.9.yaml'))
    ap.add_argument('--candidates-path', default=str(CANDIDATES_PATH))
    ap.add_argument('--base-registry', default=str(MAIN_CASES))
    ap.add_argument('--limit', type=int, default=200)
    ap.add_argument('--start-index', type=int, default=0)
    ap.add_argument('--round-base', type=int, default=73)
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
        round_num = round_for_index(args.start_index + idx, args.round_base, args.cases_per_round)
        fixture_dir = FIXTURES_BASE / f'web_scrape{round_num}' / case_id
        fixture_dir.mkdir(parents=True, exist_ok=True)
        try:
            spec = benchmark_spec_for_candidate(candidate)
            uq_seed = placeholder_uq_for_candidate(candidate)

            (fixture_dir / 'source.sql').write_text(sql + '\n')
            (fixture_dir / 'sqlite.sql').write_text(sql + '\n')
            (fixture_dir / 'benchmark_spec_uq.txt').write_text(spec + '\n')
            (fixture_dir / 'uq.txt').write_text(uq_seed + '\n')

            row_count, columns = write_csv(sql, fixture_dir / 'ground-truth.csv')
            compress_csv(fixture_dir / 'ground-truth.csv')

            if row_count < 1:
                raise ValueError(f'SQL produced {row_count} rows, skipping')

            (fixture_dir / 'documentation.txt').write_text(
                doc_text_for_candidate(candidate, row_count, columns))

            metadata = {
                'id': case_id,
                'source_title': f"Synthetic {candidate['template']} case: {case_id}",
                'source_url': 'synthetic_generated',
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

            manifest = build_manifest(case_id=case_id, round_num=round_num,
                                       fixture_dir=fixture_dir, candidate=candidate,
                                       columns=columns, row_count=row_count)

            pb_sql = run_pb_sql(prompt_pack=prompt_pack, manifest=manifest, repo_root=REPO_ROOT,
                                provider=provider, max_tokens=args.max_tokens,
                                temperature=args.temperature)
            write_json(fixture_dir / 'pb_sql.output.json', pb_sql)
            up_exec = (pb_sql.get('execution', {}).get('parsed_json', {}) or {}).get('up_exec')
            if not up_exec:
                raise ValueError('PB_SQL produced no up_exec')
            (fixture_dir / 'up_exec.txt').write_text(str(up_exec).strip() + '\n')

            pb_up = run_pb_up(prompt_pack=prompt_pack, manifest=manifest, repo_root=REPO_ROOT,
                              provider=provider, up_exec_text=str(up_exec),
                              max_tokens=args.max_tokens, temperature=args.temperature)
            write_json(fixture_dir / 'pb_up.output.json', pb_up)
            uq_surface = (pb_up.get('execution', {}).get('parsed_json', {}) or {}).get('uq_surface')
            if not uq_surface:
                raise ValueError('PB_UP produced no uq_surface')
            (fixture_dir / 'uq.txt').write_text(str(uq_surface).strip() + '\n')

            final_manifest = build_manifest(case_id=case_id, round_num=round_num,
                                             fixture_dir=fixture_dir, candidate=candidate,
                                             columns=columns, row_count=row_count)
            save_case_manifest(final_manifest, MANIFEST_ROOT / f'{case_id}.json')

            entry = case_entry(case_id=case_id, uq=str(uq_surface).strip(),
                               round_num=round_num, fixture_dir=fixture_dir,
                               sort_keys=columns)
            entry['size_class'] = size_class_for_rows(row_count)
            new_entries.append(entry)
            generated.append({
                'case_id': case_id,
                'template': candidate['template'],
                'round_num': round_num,
                'row_count': row_count,
                'fixture_dir': str(fixture_dir.resolve()),
                'manifest_path': str((MANIFEST_ROOT / f'{case_id}.json').resolve()),
            })
            print(f"[{len(generated)}/{len(candidates)}] {case_id} rows={row_count} round={round_num}", flush=True)
        except Exception as exc:
            failures.append({'case_id': case_id, 'template': candidate['template'],
                             'error': str(exc)})
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
    }
    Path(args.summary_out).write_text(json.dumps(summary, indent=2) + '\n')

    # Markdown report
    lines = [
        '# Other Wave 2 Generated v4.9',
        '',
        f"- Prompt pack: `{Path(args.prompt_pack).name}`",
        f"- Provider profile: `{args.multi_endpoint_profile}`",
        f"- Requested: {args.limit}",
        f"- Generated: {len(generated)}",
        f"- Failures: {len(failures)}",
        '',
        '## Generated cases',
        '',
    ]
    for item in generated:
        lines.append(f"- `{item['case_id']}` template=`{item['template']}` rows={item['row_count']} round={item['round_num']}")
    if failures:
        lines.extend(['', '## Failures', ''])
        for item in failures:
            lines.append(f"- `{item['case_id']}`: {item['error']}")
    Path(args.report_out).write_text('\n'.join(lines) + '\n')

    print(json.dumps({
        'generated_count': len(generated),
        'failure_count': len(failures),
    }, indent=2))


if __name__ == '__main__':
    main()
