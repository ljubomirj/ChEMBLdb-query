-- Data for levofloxacin
SELECT DISTINCT
  d.title,
  min(decode(ap.standard_type, 'DATASET', nvl(to_char(ap.standard_value), ap.standard_text_value)))         dataset,
  a.assay_id,
  a.description,
  min(decode(actp.standard_type, 'DOSED_COMPOUND_NAME',
             nvl(to_char(actp.standard_value), actp.standard_text_value) || ' ' ||
             actp.standard_units))                                                                          dosed_compound_name,
  min(decode(actp.standard_type, 'DOSE',
             nvl(to_char(actp.standard_value), actp.standard_text_value) || ' ' || actp.standard_units))    dose,
  min(decode(actp.standard_type, 'DOSAGE_FORM',
             nvl(to_char(actp.standard_value), actp.standard_text_value) || ' ' || actp.standard_units))    dosage_form,
  min(decode(actp.standard_type, 'REGIMEN',
             nvl(to_char(actp.standard_value), actp.standard_text_value) || ' ' || actp.standard_units))    regimen,
  min(decode(actp.standard_type, 'ROUTE', nvl(to_char(actp.standard_value), actp.standard_text_value)))     route,
  min(decode(actp.standard_type, 'GENDER', nvl(to_char(actp.standard_value), actp.standard_text_value)))    gender,
  min(decode(actp.standard_type, 'AGE_RANGE', nvl(to_char(actp.standard_value), actp.standard_text_value))) age_range,
  min(decode(actp.standard_type, 'HEALTH_STATUS', nvl(to_char(actp.standard_value),
                                                      actp.standard_text_value)))                           health_status,
  min(decode(actp.standard_type, 'TISSUE', nvl(to_char(actp.standard_value),
                                                      actp.standard_text_value)))                           tissue,
  cr.molregno,
  cr.compound_name,
  act.activity_id,
  act.toid,
  act.standard_type,
  act.standard_relation,
  act.standard_value,
  act.standard_units,
  act.activity_comment
FROM source s
  JOIN compound_records cr ON s.src_id = cr.src_id
  JOIN docs d ON d.doc_id = cr.doc_id
  JOIN activities act ON cr.record_id = act.record_id AND cr.doc_id = act.doc_id
  JOIN activity_properties actp ON act.activity_id = actp.activity_id
  JOIN assays a ON act.assay_id = a.assay_id
  JOIN assay_parameters ap ON a.assay_id = ap.assay_id
                              AND s.src_description = 'Curated Drug Pharmacokinetic Data'
                              AND cr.compound_name LIKE 'LEVOFLOXACIN%'
GROUP BY d.title, a.assay_id, a.description, cr.molregno, cr.compound_name, act.activity_id, act.toid,
  act.standard_type, act.standard_relation, act.standard_value, act.standard_units, act.activity_comment
ORDER BY cr.compound_name, act.toid, act.standard_type;
