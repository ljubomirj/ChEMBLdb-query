WITH compound_set AS (
    SELECT parent.molregno, parent.chembl_id AS parent_chembl_id
    FROM molecule_dictionary parent
    WHERE parent.chembl_id = 'CHEMBL3182437'
),
all_compounds AS (
    SELECT cs.molregno, m.chembl_id, m.pref_name
    FROM compound_set cs
    JOIN molecule_hierarchy mh ON mh.parent_molregno = cs.molregno
    JOIN molecule_dictionary m ON m.molregno = mh.molregno
    UNION ALL
    SELECT cs.molregno, parent.chembl_id, parent.pref_name
    FROM compound_set cs
    JOIN molecule_dictionary parent ON parent.molregno = cs.molregno
)
SELECT
    m.chembl_id AS compound_chembl_id,
    struc.canonical_smiles,
    cr.compound_key,
    COALESCE(CAST(d.pubmed_id AS TEXT), d.doi) AS pubmed_id_or_doi,
    a.description AS assay_description,
    act.standard_type,
    act.standard_relation,
    act.standard_value,
    act.standard_units,
    act.activity_comment,
    td.chembl_id AS target_chembl_id,
    td.pref_name AS target_name,
    td.organism AS target_organism
FROM all_compounds m
JOIN compound_records cr ON cr.molregno = m.molregno
JOIN activities act ON act.record_id = cr.record_id
JOIN assays a ON a.assay_id = act.assay_id
JOIN docs d ON d.doc_id = cr.doc_id
JOIN target_dictionary td ON td.tid = act.tid
LEFT JOIN compound_structures struc ON struc.molregno = m.molregno
WHERE act.standard_type = 'IC50'
  AND td.chembl_id = 'CHEMBL3430885'
ORDER BY
    m.chembl_id,
    struc.canonical_smiles,
    cr.compound_key,
    pubmed_id_or_doi,
    a.description,
    act.standard_type,
    act.standard_relation,
    act.standard_value,
    act.standard_units,
    act.activity_comment,
    td.chembl_id,
    td.pref_name,
    td.organism
