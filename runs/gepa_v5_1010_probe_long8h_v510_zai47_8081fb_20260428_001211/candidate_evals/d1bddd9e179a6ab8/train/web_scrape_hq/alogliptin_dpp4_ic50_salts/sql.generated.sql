WITH compound_set AS (
    SELECT DISTINCT parent.molregno
    FROM molecule_dictionary parent
    WHERE parent.chembl_id = 'CHEMBL376359'
    UNION
    SELECT DISTINCT child.molregno
    FROM molecule_dictionary parent
    JOIN molecule_hierarchy mh ON mh.parent_molregno = parent.molregno
    JOIN molecule_dictionary child ON child.molregno = mh.molregno
    WHERE parent.chembl_id = 'CHEMBL376359'
)
SELECT
    m.chembl_id AS compound_chembl_id,
    cs.canonical_smiles,
    r.compound_key,
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
FROM compound_set cs_base
JOIN molecule_dictionary m ON m.molregno = cs_base.molregno
LEFT JOIN compound_structures cs ON cs.molregno = m.molregno
JOIN compound_records r ON r.molregno = m.molregno
JOIN docs d ON d.doc_id = r.doc_id
JOIN activities act ON act.record_id = r.record_id
JOIN assays a ON a.assay_id = act.assay_id
JOIN target_dictionary td ON td.tid = a.tid
WHERE act.standard_type = 'IC50'
  AND act.standard_units = 'nM'
  AND td.chembl_id = 'CHEMBL284'
ORDER BY
    m.chembl_id,
    r.compound_key,
    COALESCE(CAST(d.pubmed_id AS TEXT), d.doi),
    a.description,
    act.standard_type,
    act.standard_relation,
    act.standard_value,
    act.standard_units,
    td.chembl_id,
    td.pref_name,
    td.organism
