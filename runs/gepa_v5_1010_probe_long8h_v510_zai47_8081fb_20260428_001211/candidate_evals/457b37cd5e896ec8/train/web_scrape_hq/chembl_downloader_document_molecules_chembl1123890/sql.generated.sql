SELECT DISTINCT
  md.chembl_id,
  cr.compound_name,
  cs.canonical_smiles
FROM docs d
INNER JOIN compound_records cr
  ON d.doc_id = cr.doc_id
INNER JOIN molecule_dictionary md
  ON cr.molregno = md.molregno
INNER JOIN compound_structures cs
  ON md.molregno = cs.molregno
WHERE d.chembl_id = 'CHEMBL1123890'
  AND cs.canonical_smiles IS NOT NULL
ORDER BY md.chembl_id ASC,
         cr.compound_name ASC,
         cs.canonical_smiles ASC
