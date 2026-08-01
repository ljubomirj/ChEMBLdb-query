#!/usr/bin/env python3
from __future__ import annotations

import json
from collections import Counter, defaultdict
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
MANIFEST_ROOT = REPO_ROOT / 'tests' / 'v5_manifests' / 'web_scrape_hq'
OUT_JSON = REPO_ROOT / 'experiments' / 'non_target_sql_family_inventory_v4.8.json'
OUT_MD = REPO_ROOT / 'experiments' / 'non_target_sql_family_inventory_v4.8.md'
NON_TARGET_FAMILIES = {'assay_exact', 'document', 'salts', 'metabolism', 'other'}


def template_key(case_id: str, family: str) -> str:
    if family == 'assay_exact':
        if 'bioassay_metadata' in case_id:
            return 'baoilleach_bioassay_metadata_export'
        return 'chembl_downloader_assay_exact_export'
    if family == 'document':
        return 'chembl_downloader_document_molecules_export'
    if family == 'salts':
        return 'faq_parent_and_salts_activity_provenance'
    if family == 'metabolism':
        if 'parent_names' in case_id:
            return 'metabolism_first_n_with_parent_name_enrichment'
        if 'record_keys' in case_id:
            return 'metabolism_first_n_with_record_keys'
        return 'metabolism_example_export'
    if family == 'other':
        if case_id.startswith('human_') and case_id.endswith('_molecule_smiles'):
            return 'human_target_molecule_smiles_export'
        if case_id.startswith('baoilleach_') and 'target_descriptions' in case_id:
            return 'target_description_list'
        if case_id.startswith('target_ic50_with_pubmed_or_doi_'):
            return 'target_activity_with_pubmed_or_doi'
        if 'approved_drugs_with_indications' in case_id:
            return 'approved_drugs_with_indications_export'
        if case_id == 'chembl_downloader_drug_indications':
            return 'drug_indications_export'
        if case_id == 'approved_drugs_with_mechanisms':
            return 'approved_drugs_with_mechanisms_export'
        return 'other_grounded_sql_family'
    return 'unknown'


def main() -> None:
    manifests = []
    for path in sorted(MANIFEST_ROOT.glob('*.json')):
        obj = json.loads(path.read_text())
        family = obj['metadata']['family']
        if family not in NON_TARGET_FAMILIES:
            continue
        case_id = obj['case_id']
        manifests.append({
            'case_id': case_id,
            'family': family,
            'template_key': template_key(case_id, family),
            'source_manifest': str(path.resolve()),
            'sql_gold_path': obj['artifacts']['sql_gold'],
            'uq_surface_path': obj['artifacts']['uq_surface'],
            'uq_benchmark_spec_path': obj['artifacts'].get('uq_benchmark_spec'),
            'realism_level': obj['metadata']['realism_level'],
        })

    family_counts = Counter(item['family'] for item in manifests)
    template_counts = defaultdict(Counter)
    examples = defaultdict(lambda: defaultdict(list))
    for item in manifests:
        family = item['family']
        key = item['template_key']
        template_counts[family][key] += 1
        if len(examples[family][key]) < 5:
            examples[family][key].append(item['case_id'])

    payload = {
        'total_non_target_cases': len(manifests),
        'family_counts': dict(family_counts),
        'template_counts': {family: dict(counter) for family, counter in template_counts.items()},
        'examples': {family: dict(group) for family, group in examples.items()},
        'cases': manifests,
    }
    OUT_JSON.write_text(json.dumps(payload, indent=2) + '\n')

    lines = [
        '# Non-Target SQL Family Inventory v4.8',
        '',
        f"- Total non-target cases inventoried: {len(manifests)}",
        '',
        '## Family counts',
        '',
    ]
    for family in sorted(family_counts):
        lines.append(f"- `{family}`: {family_counts[family]}")
    for family in sorted(template_counts):
        lines.extend(['', f'## {family}', ''])
        for key, count in template_counts[family].most_common():
            lines.append(f"- `{key}`: {count}")
            for case_id in examples[family][key]:
                lines.append(f"  - `{case_id}`")
    OUT_MD.write_text('\n'.join(lines) + '\n')
    print(json.dumps({'out_json': str(OUT_JSON.resolve()), 'out_md': str(OUT_MD.resolve()), 'family_counts': dict(family_counts)}, indent=2))


if __name__ == '__main__':
    main()
