-- The source id for PubChem data is found in the SOURCE table and is '7'.
-- Please note that this will bring back over 4,000,000 data points
SELECT DISTINCT
  md.molregno,
  cs.canonical_smiles,
  md.chembl_id,
  act.standard_type,
  act.standard_value,
  act.standard_units
FROM activities act
  JOIN molecule_dictionary md ON act.molregno = md.molregno
  JOIN compound_structures cs ON md.molregno = cs.molregno
  JOIN compound_records cr ON cr.molregno = act.molregno
  JOIN source src ON src.src_id = cr.src_id
    AND src.src_id = '7';
