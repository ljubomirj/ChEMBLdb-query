select distinct act.* from molecule_dictionary md, activities act, assays, assay2target, target_dictionary td
where 
#assay_organism="Homo sapiens" and
assay2target.assay_id=assays.assay_id and act.assay_id=assays.assay_id
and act.molregno=md.molregno
and assay2target.tid=td.tid
and td.chembl_id="CHEMBL3880"
;
