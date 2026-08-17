WITH parent AS (
    SELECT molregno
    FROM molecule_dictionary
    WHERE chembl_id = 'CHEMBL376359'
), compound_set AS (
    SELECT DISTINCT p.molregno AS parent_molregno,
           COALESCE(mh.molregno, p.molregno) AS molregno
    FROM parent p
    LEFT JOIN molecule_hierarchy mh ON mh.parent_molregno = p.molregno
)
SELECT DISTINCT
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
FROM compound_set cs
JOIN molecule_dictionary md ON md.molregno = cs.molregno
JOIN compound_records cr ON cr.molregno = md.molregno
JOIN activities act ON act.record_id = cr.record_id
JOIN docs d ON d.doc_id = cr.doc_id
JOIN assays a ON a.assay_id = act.assay_id
JOIN target_dictionary td ON td.tid = a.tid
JOIN compound_structures cs_struct ON cs_struct.molregno = md.molregno
WHERE td.chembl_id = 'CHEMBL284'
  AND act.standard_type = 'IC50'
  AND act.standard_units = 'nM'
ORDER BY md.chembl_id, cr.compound_key, pubmed_id_or_doi, a.description, act.standard_type, act.standard_relation, act.standard_value, act.standard_units, td.chembl_id, td.pref_name, td.organism
