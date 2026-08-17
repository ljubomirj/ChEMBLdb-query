WITH base_compounds AS (
    SELECT DISTINCT parent.molregno
    FROM molecule_dictionary parent
    WHERE parent.chembl_id = 'CHEMBL2105717'
    UNION
    SELECT child.molregno
    FROM molecule_dictionary parent
    JOIN molecule_hierarchy mh ON mh.parent_molregno = parent.molregno
    JOIN molecule_dictionary child ON child.molregno = mh.molregno
    WHERE parent.chembl_id = 'CHEMBL2105717'
)
SELECT
    md.chembl_id AS compound_chembl_id,
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
FROM base_compounds bc
JOIN molecule_dictionary md ON md.molregno = bc.molregno
JOIN compound_structures cs ON cs.molregno = md.molregno
JOIN compound_records cr ON cr.molregno = md.molregno
JOIN docs d ON d.doc_id = cr.doc_id
JOIN activities act ON act.record_id = cr.record_id
JOIN assays a ON a.assay_id = act.assay_id
JOIN target_dictionary td ON td.tid = a.tid
WHERE td.chembl_id = 'CHEMBL3717'
  AND act.standard_type = 'IC50'
  AND act.standard_units = 'nM'
  AND act.standard_value IS NOT NULL
ORDER BY
    md.chembl_id ASC,
    cr.compound_key ASC,
    COALESCE(CAST(d.pubmed_id AS TEXT), d.doi) ASC,
    a.description ASC,
    act.standard_type ASC,
    act.standard_relation ASC,
    act.standard_value ASC,
    act.standard_units ASC,
    td.chembl_id ASC,
    td.pref_name ASC,
    td.organism ASC
