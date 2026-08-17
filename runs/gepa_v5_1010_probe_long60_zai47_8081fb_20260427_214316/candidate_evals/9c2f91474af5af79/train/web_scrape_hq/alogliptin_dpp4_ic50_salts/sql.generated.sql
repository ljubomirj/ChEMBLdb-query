WITH compound_set AS (
    SELECT parent.molregno, parent.chembl_id, parent.pref_name
    FROM molecule_dictionary parent
    WHERE parent.chembl_id = 'CHEMBL376359'
    UNION ALL
    SELECT child.molregno, child.chembl_id, child.pref_name
    FROM molecule_dictionary parent
    JOIN molecule_hierarchy mh ON mh.parent_molregno = parent.molregno
    JOIN molecule_dictionary child ON child.molregno = mh.molregno
    WHERE parent.chembl_id = 'CHEMBL376359'
)
SELECT
    cs.chembl_id AS compound_chembl_id,
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
FROM compound_set cs
JOIN compound_records cr ON cr.molregno = cs.molregno
JOIN activities act ON act.record_id = cr.record_id
JOIN assays a ON a.assay_id = act.assay_id
JOIN target_dictionary td ON td.tid = act.tid
JOIN docs d ON d.doc_id = cr.doc_id
JOIN compound_structures struc ON struc.molregno = cs.molregno
WHERE act.standard_type = 'IC50'
  AND act.standard_units = 'nM'
  AND td.chembl_id = 'CHEMBL284'
ORDER BY cs.chembl_id, cr.compound_key, pubmed_id_or_doi, a.description, act.standard_type, act.standard_relation, act.standard_value, act.standard_units, td.chembl_id, td.pref_name, td.organism
