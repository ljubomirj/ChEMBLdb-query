WITH parent AS (
    SELECT molregno
    FROM molecule_dictionary
    WHERE chembl_id = 'CHEMBL3182437'
),
compound_set AS (
    SELECT molregno
    FROM parent
    UNION ALL
    SELECT mh.molregno
    FROM parent p
    JOIN molecule_hierarchy mh ON mh.parent_molregno = p.molregno
)
SELECT 
    m.chembl_id AS compound_chembl_id,
    cs.canonical_smiles,
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
FROM compound_set cs
JOIN molecule_dictionary m ON m.molregno = cs.molregno
LEFT JOIN compound_structures cs ON cs.molregno = m.molregno
JOIN compound_records cr ON cr.molregno = m.molregno
JOIN activities act ON act.record_id = cr.record_id
JOIN assays a ON a.assay_id = act.assay_id
JOIN target_dictionary td ON td.tid = a.tid
JOIN docs d ON d.doc_id = act.doc_id
WHERE act.standard_type = 'IC50'
  AND td.chembl_id = 'CHEMBL3430885'
ORDER BY 
    m.chembl_id,
    cs.canonical_smiles,
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
