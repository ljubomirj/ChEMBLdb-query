COPY (
select compound_structures.canonical_smiles,
compound_name, met_conversion,pathway_key from compound_records,
compound_structures, metabolism
where compound_records.record_id=metabolism.substrate_record_id and compound_structures.molregno=compound_records.molregno
 limit(200))
 TO '/Users/iwatobipen/develop/chembldb/test.csv'
 (DELIMITER ',' , FORMAT csv,HEADER TRUE);
