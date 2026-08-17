SELECT DISTINCT m.chembl_id AS compound_chembl_id, cs.canonical_smiles
FROM activities act
JOIN assays a ON act.assay_id = a.assay_id
JOIN target_dictionary td ON a.tid = td.tid
JOIN molecule_dictionary m ON act.molregno = m.molregno
JOIN compound_structures cs ON m.molregno = cs.molregno
WHERE a.assay_organism = 'Caenorhabditis elegans'
  AND td.chembl_id IN ('CHEMBL2971', 'CHEMBL2835')
  AND act.standard_relation = '='
  AND act.standard_units = 'nM'
  AND act.value IS NOT NULL
  AND (act.value < 50 OR act.value > 200)
GROUP BY m.chembl_id, cs.canonical_smiles
HAVING COUNT(DISTINCT td.chembl_id) = 2
ORDER BY m.chembl_id, cs.canonical_smiles;
