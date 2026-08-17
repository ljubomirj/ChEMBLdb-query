SELECT t1.activity_id, t2.chembl_id, t1.standard_relation, t1.standard_value, t1.standard_units, t1.standard_type, t3.chembl_id
FROM activities AS t1
INNER JOIN assays AS t2 ON t1.assay_id = t2.assay_id
INNER JOIN molecule_dictionary AS t3 ON t1.molregno = t3.molregno
WHERE t2.tid=165 AND t1.standard_type='IC50';
