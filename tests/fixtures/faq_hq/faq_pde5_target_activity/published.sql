-- Target is Human PDE5 (CHEMBL1827)
SELECT m.chembl_id AS compound_chembl_id,
s.canonical_smiles,
r.compound_key,
NVL(TO_CHAR(d.pubmed_id),d.doi) AS pubmed_id_or_doi,
a.description                   AS assay_description,
act.standard_type,
act.standard_relation,
act.standard_value,
act.standard_units,
act.activity_comment
FROM chembl.compound_structures s
 RIGHT JOIN chembl.molecule_dictionary m on s.molregno = m.molregno
 JOIN chembl.compound_records r on m.molregno = r.molregno
 JOIN chembl.docs d on r.doc_id = d.doc_id
 JOIN chembl.activities act on r.record_id = act.record_id
 JOIN chembl.assays a on act.assay_id = a.assay_id
 JOIN chembl.target_dictionary t on a.tid = t.tid
AND t.chembl_id = 'CHEMBL1827';
