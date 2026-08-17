SELECT assays.assay_organism AS organism, COUNT(*) AS ic50_count
FROM activities
JOIN assays ON activities.assay_id = assays.assay_id
WHERE activities.standard_type = 'IC50'
GROUP BY assays.assay_organism
ORDER BY assays.assay_organism, ic50_count
