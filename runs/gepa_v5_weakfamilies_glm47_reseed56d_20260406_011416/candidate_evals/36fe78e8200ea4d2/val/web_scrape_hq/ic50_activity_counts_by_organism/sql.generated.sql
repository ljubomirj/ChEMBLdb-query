SELECT
  a.assay_organism AS organism,
  COUNT(*) AS ic50_count
FROM activities act
JOIN assays a ON act.assay_id = a.assay_id
WHERE act.standard_type = 'IC50'
GROUP BY a.assay_organism
ORDER BY a.assay_organism ASC, ic50_count ASC
