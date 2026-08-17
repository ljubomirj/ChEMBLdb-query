select distinct md.* from molecule_dictionary md, activities, assays, assay2target, target_dictionary td
where assay_organism="Homo sapiens"
and assay2target.assay_id=assays.assay_id and activities.assay_id=assays.assay_id
and activities.molregno=md.molregno
and assay2target.tid=td.tid
and td.chembl_id="CHEMBL3880"
;
