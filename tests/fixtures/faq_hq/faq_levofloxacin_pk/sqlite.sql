-- Data for levofloxacin
SELECT DISTINCT
  d.title,
  MIN(CASE
    WHEN ap.standard_type = 'DATASET' THEN COALESCE(CAST(ap.standard_value AS TEXT), ap.standard_text_value)
  END) AS dataset,
  a.assay_id,
  a.description,
  MIN(CASE
    WHEN actp.standard_type = 'DOSED_COMPOUND_NAME' THEN TRIM(COALESCE(CAST(actp.standard_value AS TEXT), actp.standard_text_value) || ' ' || COALESCE(actp.standard_units, ''))
  END) AS dosed_compound_name,
  MIN(CASE
    WHEN actp.standard_type = 'DOSE' THEN TRIM(COALESCE(CAST(actp.standard_value AS TEXT), actp.standard_text_value) || ' ' || COALESCE(actp.standard_units, ''))
  END) AS dose,
  MIN(CASE
    WHEN actp.standard_type = 'DOSAGE_FORM' THEN TRIM(COALESCE(CAST(actp.standard_value AS TEXT), actp.standard_text_value) || ' ' || COALESCE(actp.standard_units, ''))
  END) AS dosage_form,
  MIN(CASE
    WHEN actp.standard_type = 'REGIMEN' THEN TRIM(COALESCE(CAST(actp.standard_value AS TEXT), actp.standard_text_value) || ' ' || COALESCE(actp.standard_units, ''))
  END) AS regimen,
  MIN(CASE
    WHEN actp.standard_type = 'ROUTE' THEN COALESCE(CAST(actp.standard_value AS TEXT), actp.standard_text_value)
  END) AS route,
  MIN(CASE
    WHEN actp.standard_type = 'GENDER' THEN COALESCE(CAST(actp.standard_value AS TEXT), actp.standard_text_value)
  END) AS gender,
  MIN(CASE
    WHEN actp.standard_type = 'AGE_RANGE' THEN COALESCE(CAST(actp.standard_value AS TEXT), actp.standard_text_value)
  END) AS age_range,
  MIN(CASE
    WHEN actp.standard_type = 'HEALTH_STATUS' THEN COALESCE(CAST(actp.standard_value AS TEXT), actp.standard_text_value)
  END) AS health_status,
  MIN(CASE
    WHEN actp.standard_type = 'TISSUE' THEN COALESCE(CAST(actp.standard_value AS TEXT), actp.standard_text_value)
  END) AS tissue,
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
WHERE s.src_description = 'Curated Drug Pharmacokinetic Data'
  AND cr.compound_name LIKE 'LEVOFLOXACIN%'
GROUP BY d.title, a.assay_id, a.description, cr.molregno, cr.compound_name, act.activity_id, act.toid,
  act.standard_type, act.standard_relation, act.standard_value, act.standard_units, act.activity_comment
ORDER BY cr.compound_name, act.toid, act.standard_type;
