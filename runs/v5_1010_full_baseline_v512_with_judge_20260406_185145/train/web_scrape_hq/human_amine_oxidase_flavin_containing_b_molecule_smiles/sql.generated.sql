SELECT DISTINCT md.chembl_id AS molecule_chembl_id, cs.canonical_smiles AS canonical_smiles
FROM molecule_dictionary md
JOIN activities act ON act.molregno = md.molregno
JOIN assays a ON act.assay_id = a.assay_id
JOIN target_dictionary td ON a.tid = td.tid
JOIN compound_structures cs ON cs.molregno = md.molregno
WHERE td.target_type = 'SINGLE PROTEIN'
  AND td.pref_name = 'Human amine oxidase B (flavin‑containing)'
  AND a.assay_type = 'B'
  AND a.assay_organism = 'Homo sapiens'
  AND act.standard_type = 'IC50'
  AND act.standard_relation = '='
ORDER BY molecule_chembl_id
