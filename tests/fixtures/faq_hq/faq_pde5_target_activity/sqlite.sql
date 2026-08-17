-- Target is Human PDE5 (CHEMBL1827)
SELECT m.chembl_id AS compound_chembl_id,
s.canonical_smiles,
r.compound_key,
COALESCE(CAST(d.pubmed_id AS TEXT), d.doi) AS pubmed_id_or_doi,
a.description AS assay_description,
act.standard_type,
act.standard_relation,
act.standard_value,
act.standard_units,
act.activity_comment
FROM molecule_dictionary m
LEFT JOIN compound_structures s ON s.molregno = m.molregno
JOIN compound_records r ON m.molregno = r.molregno
JOIN docs d ON r.doc_id = d.doc_id
JOIN activities act ON r.record_id = act.record_id
JOIN assays a ON act.assay_id = a.assay_id
JOIN target_dictionary t ON a.tid = t.tid
WHERE t.chembl_id = 'CHEMBL1827';
