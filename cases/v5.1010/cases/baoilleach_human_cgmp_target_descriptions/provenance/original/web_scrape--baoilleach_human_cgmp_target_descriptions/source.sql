select distinct(td.description) from molecule_dictionary, activities, assays, assay2target, target_dictionary td
where assay_organism="Homo sapiens"
and assay2target.assay_id=assays.assay_id and activities.assay_id=assays.assay_id
and activities.molregno=molecule_dictionary.molregno
and assay2target.tid=td.tid
and td.description like "cGMP%"
;
