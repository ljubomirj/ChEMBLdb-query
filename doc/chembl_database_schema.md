# ChEMBL SQLite schema (auto-generated)
Database: database/latest/chembl_36/chembl_36_sqlite/chembl_36.db
Tables: 73

## Table: action_type
Columns:
- action_type VARCHAR(50) NOT NULL PK
- description VARCHAR(200) NOT NULL
- parent_type VARCHAR(50) NULL

Sample rows:
| action_type | description | parent_type |
|---|---|---|
| ACTIVATOR | Positively effects the normal functioning of the protein e.g., activation of ... | POSITIVE MODULATOR |
| AGONIST | Binds to and activates a receptor, often mimicking the effect of the endogeno... | POSITIVE MODULATOR |
| ALLOSTERIC ANTAGONIST | Binds to a receptor at an allosteric site and prevents activation by a positi... | NEGATIVE MODULATOR |

## Table: activities
Columns:
- activity_id BIGINT NOT NULL PK
- assay_id BIGINT NOT NULL
- doc_id BIGINT NULL
- record_id BIGINT NOT NULL
- molregno BIGINT NULL
- standard_relation VARCHAR(50) NULL
- standard_value NUMERIC NULL
- standard_units VARCHAR(100) NULL
- standard_flag SMALLINT NULL
- standard_type VARCHAR(250) NULL
- activity_comment VARCHAR(4000) NULL
- data_validity_comment VARCHAR(30) NULL
- potential_duplicate SMALLINT NULL
- pchembl_value NUMERIC(4, 2) NULL
- bao_endpoint VARCHAR(11) NULL
- uo_units VARCHAR(10) NULL
- qudt_units VARCHAR(70) NULL
- toid INTEGER NULL
- upper_value NUMERIC NULL
- standard_upper_value NUMERIC NULL
- src_id INTEGER NULL
- type VARCHAR(250) NOT NULL
- relation VARCHAR(50) NULL
- value NUMERIC NULL
- units VARCHAR(100) NULL
- text_value VARCHAR(1000) NULL
- standard_text_value VARCHAR(1000) NULL
- action_type VARCHAR(50) NULL

Sample rows:
| activity_id | assay_id | doc_id | record_id | molregno | standard_relation | standard_value | standard_units | standard_flag | standard_type | activity_comment | data_validity_comment | potential_duplicate | pchembl_value | bao_endpoint | uo_units | qudt_units | toid | upper_value | standard_upper_value | src_id | type | relation | value | units | text_value | standard_text_value | action_type |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 31863 | 54505 | 6424 | 206172 | 180094 | > | 100000 | nM | 1 | IC50 | NULL | NULL | 0 | NULL | BAO_0000190 | UO_0000065 | http://www.openphacts.org/units/Nanomolar | NULL | NULL | NULL | 1 | IC50 | > | 100 | uM | NULL | NULL | NULL |
| 31864 | 83907 | 6432 | 208970 | 182268 | = | 2500 | nM | 1 | IC50 | NULL | NULL | 0 | 5.6 | BAO_0000190 | UO_0000065 | http://www.openphacts.org/units/Nanomolar | NULL | NULL | NULL | 1 | IC50 | = | 2.5 | uM | NULL | NULL | NULL |
| 31865 | 88152 | 6432 | 208970 | 182268 | > | 50000 | nM | 1 | IC50 | NULL | NULL | 0 | NULL | BAO_0000190 | UO_0000065 | http://www.openphacts.org/units/Nanomolar | NULL | NULL | NULL | 1 | IC50 | > | 50 | uM | NULL | NULL | NULL |

## Table: activity_properties
Columns:
- ap_id BIGINT NOT NULL PK
- activity_id BIGINT NOT NULL
- type VARCHAR(250) NOT NULL
- relation VARCHAR(50) NULL
- value NUMERIC NULL
- units VARCHAR(100) NULL
- text_value VARCHAR(2000) NULL
- standard_type VARCHAR(250) NULL
- standard_relation VARCHAR(50) NULL
- standard_value NUMERIC NULL
- standard_units VARCHAR(100) NULL
- standard_text_value VARCHAR(2000) NULL
- comments VARCHAR(2000) NULL
- result_flag SMALLINT NOT NULL

Sample rows:
| ap_id | activity_id | type | relation | value | units | text_value | standard_type | standard_relation | standard_value | standard_units | standard_text_value | comments | result_flag |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | 17126237 | DATASET | NULL | NULL | NULL | Hematology | DATASET | NULL | NULL | NULL | Hematology | NULL | 0 |
| 2 | 17126237 | ACTIVITY_TEST | NULL | NULL | NULL | RBC (Erythrocytes) | ACTIVITY_TEST | NULL | NULL | NULL | RBC (Erythrocytes) | NULL | 0 |
| 3 | 17126237 | TISSUE | NULL | NULL | NULL | Blood | TISSUE | NULL | NULL | NULL | Blood | NULL | 0 |

## Table: activity_smid
Columns:
- smid BIGINT NOT NULL PK

Sample rows:
| smid |
|---|
| 1 |
| 2 |
| 3 |

## Table: activity_stds_lookup
Columns:
- std_act_id BIGINT NOT NULL PK
- standard_type VARCHAR(250) NOT NULL
- definition VARCHAR(500) NULL
- standard_units VARCHAR(100) NOT NULL
- normal_range_min NUMERIC(24, 12) NULL
- normal_range_max NUMERIC(24, 12) NULL

Sample rows:
| std_act_id | standard_type | definition | standard_units | normal_range_min | normal_range_max |
|---|---|---|---|---|---|
| 1 | CC50 | Concentration required for 50% cytotoxicity | nM | 1 | 10000000 |
| 2 | EC50 | Effective concentration for 50% activity | nM | 0.01 | 100000 |
| 3 | GI50 | Concentration required for 50% growth inhibition | nM | 1 | 10000000 |

## Table: activity_supp
Columns:
- as_id BIGINT NOT NULL PK
- rgid BIGINT NOT NULL
- smid BIGINT NULL
- type VARCHAR(250) NOT NULL
- relation VARCHAR(50) NULL
- value NUMERIC NULL
- units VARCHAR(100) NULL
- text_value VARCHAR(1000) NULL
- standard_type VARCHAR(250) NULL
- standard_relation VARCHAR(50) NULL
- standard_value NUMERIC NULL
- standard_units VARCHAR(100) NULL
- standard_text_value VARCHAR(1000) NULL
- comments VARCHAR(4000) NULL

Sample rows:
| as_id | rgid | smid | type | relation | value | units | text_value | standard_type | standard_relation | standard_value | standard_units | standard_text_value | comments |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | 1 | 1012613 | Liver_Deposit, glycogen (Peripheral) | NULL | NULL | NULL | slight | Liver_Deposit, glycogen (Peripheral) | NULL | NULL | NULL | slight | SAMPLE_ID: 0698011; SP_FLG: true; BARCODE: No ChipData |
| 2 | 2 | 1012614 | Liver_Deposit, glycogen (Peripheral) | NULL | NULL | NULL | slight | Liver_Deposit, glycogen (Peripheral) | NULL | NULL | NULL | slight | SAMPLE_ID: 0698025; SP_FLG: true; BARCODE: No ChipData |
| 3 | 3 | 1012615 | Liver_Degeneration, fatty (Peripheral) | NULL | NULL | NULL | slight | Liver_Degeneration, fatty (Peripheral) | NULL | NULL | NULL | slight | SAMPLE_ID: 0698051; SP_FLG: false; BARCODE: 003017906001 |

## Table: activity_supp_map
Columns:
- actsm_id BIGINT NOT NULL PK
- activity_id BIGINT NOT NULL
- smid BIGINT NOT NULL

Sample rows:
| actsm_id | activity_id | smid |
|---|---|---|
| 1 | 17126840 | 2938 |
| 2 | 17126841 | 2939 |
| 3 | 17126842 | 2940 |

## Table: assay_class_map
Columns:
- ass_cls_map_id BIGINT NOT NULL PK
- assay_id BIGINT NOT NULL
- assay_class_id BIGINT NOT NULL

Sample rows:
| ass_cls_map_id | assay_id | assay_class_id |
|---|---|---|
| 2749981 | 585237 | 344 |
| 2749982 | 511570 | 344 |
| 2749983 | 511565 | 344 |

## Table: assay_classification
Columns:
- assay_class_id BIGINT NOT NULL PK
- l1 VARCHAR(100) NULL
- l2 VARCHAR(100) NULL
- l3 VARCHAR(1000) NULL
- class_type VARCHAR(50) NULL
- source VARCHAR(50) NULL

Sample rows:
| assay_class_id | l1 | l2 | l3 | class_type | source |
|---|---|---|---|---|---|
| 1 | ALIMENTARY TRACT AND METABOLISM | Anti-Obesity Activity | Computer-Assisted Measurement of Food Consumption in Rats Anorectic Activity | In vivo efficacy | Vogel_2008 |
| 2 | ALIMENTARY TRACT AND METABOLISM | Anti-Obesity Activity | Food Consumption in Rats Anorectic Activity | In vivo efficacy | Vogel_2008 |
| 3 | ALIMENTARY TRACT AND METABOLISM | Anti-Obesity Activity | General Anti-Obesity activity | In vivo efficacy | phenotype |

## Table: assay_parameters
Columns:
- assay_param_id BIGINT NOT NULL PK
- assay_id BIGINT NOT NULL
- type VARCHAR(250) NOT NULL
- relation VARCHAR(50) NULL
- value NUMERIC NULL
- units VARCHAR(100) NULL
- text_value VARCHAR(4000) NULL
- standard_type VARCHAR(250) NULL
- standard_relation VARCHAR(50) NULL
- standard_value NUMERIC NULL
- standard_units VARCHAR(100) NULL
- standard_text_value VARCHAR(4000) NULL
- comments VARCHAR(4000) NULL

Sample rows:
| assay_param_id | assay_id | type | relation | value | units | text_value | standard_type | standard_relation | standard_value | standard_units | standard_text_value | comments |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 3710880 | 1640162 | assay_method | NULL | NULL | NULL | SPR | assay_method | NULL | NULL | NULL | SPR | NULL |
| 3710881 | 1640162 | data_collection_rate | NULL | 10 | Hz | NULL | data_collection_rate | NULL | 10 | Hz | NULL | NULL |
| 3710882 | 1640162 | fitting_model | NULL | NULL | NULL | 1:1 + mass transport | fitting_model | NULL | NULL | NULL | 1:1 + mass transport | NULL |

## Table: assay_type
Columns:
- assay_type VARCHAR(1) NOT NULL PK
- assay_desc VARCHAR(250) NULL

Sample rows:
| assay_type | assay_desc |
|---|---|
| A | ADME |
| B | Binding |
| F | Functional |

## Table: assays
Columns:
- assay_id BIGINT NOT NULL PK
- doc_id BIGINT NOT NULL
- description VARCHAR(4000) NULL
- assay_type VARCHAR(1) NULL
- assay_test_type VARCHAR(20) NULL
- assay_category VARCHAR(50) NULL
- assay_organism VARCHAR(250) NULL
- assay_tax_id BIGINT NULL
- assay_strain VARCHAR(200) NULL
- assay_tissue VARCHAR(100) NULL
- assay_cell_type VARCHAR(100) NULL
- assay_subcellular_fraction VARCHAR(100) NULL
- tid BIGINT NULL
- relationship_type VARCHAR(1) NULL
- confidence_score SMALLINT NULL
- curated_by VARCHAR(32) NULL
- src_id INTEGER NOT NULL
- src_assay_id VARCHAR(50) NULL
- chembl_id VARCHAR(20) NOT NULL
- cell_id BIGINT NULL
- bao_format VARCHAR(11) NULL
- tissue_id BIGINT NULL
- variant_id BIGINT NULL
- aidx VARCHAR(200) NOT NULL
- assay_group VARCHAR(200) NULL

Sample rows:
| assay_id | doc_id | description | assay_type | assay_test_type | assay_category | assay_organism | assay_tax_id | assay_strain | assay_tissue | assay_cell_type | assay_subcellular_fraction | tid | relationship_type | confidence_score | curated_by | src_id | src_assay_id | chembl_id | cell_id | bao_format | tissue_id | variant_id | aidx | assay_group |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | 11087 | The compound was tested for the in vitro inhibition of platelet 12-lipoxygena... | B | NULL | NULL | NULL | NULL | NULL | NULL | NULL | NULL | 12052 | H | 8 | Autocuration | 1 | NULL | CHEMBL615117 | NULL | BAO_0000019 | NULL | NULL | CLD0 | NULL |
| 2 | 684 | Compound was evaluated for its ability to mobilize calcium in 1321NI cells | F | NULL | NULL | NULL | NULL | NULL | NULL | NULL | NULL | 22226 | U | 0 | Autocuration | 1 | NULL | CHEMBL615118 | NULL | BAO_0000219 | NULL | NULL | CLD0 | NULL |
| 3 | 15453 | NULL | B | NULL | NULL | NULL | NULL | NULL | NULL | NULL | NULL | 22229 | U | 0 | Autocuration | 1 | NULL | CHEMBL615119 | NULL | BAO_0000019 | NULL | NULL | CLD0 | NULL |

## Table: atc_classification
Columns:
- who_name VARCHAR(2000) NULL
- level1 VARCHAR(10) NULL
- level2 VARCHAR(10) NULL
- level3 VARCHAR(10) NULL
- level4 VARCHAR(10) NULL
- level5 VARCHAR(10) NOT NULL PK
- level1_description VARCHAR(2000) NULL
- level2_description VARCHAR(2000) NULL
- level3_description VARCHAR(2000) NULL
- level4_description VARCHAR(2000) NULL

Sample rows:
| who_name | level1 | level2 | level3 | level4 | level5 | level1_description | level2_description | level3_description | level4_description |
|---|---|---|---|---|---|---|---|---|---|
| sodium fluoride | A | A01 | A01A | A01AA | A01AA01 | ALIMENTARY TRACT AND METABOLISM | STOMATOLOGICAL PREPARATIONS | STOMATOLOGICAL PREPARATIONS | Caries prophylactic agents |
| sodium monofluorophosphate | A | A01 | A01A | A01AA | A01AA02 | ALIMENTARY TRACT AND METABOLISM | STOMATOLOGICAL PREPARATIONS | STOMATOLOGICAL PREPARATIONS | Caries prophylactic agents |
| olaflur | A | A01 | A01A | A01AA | A01AA03 | ALIMENTARY TRACT AND METABOLISM | STOMATOLOGICAL PREPARATIONS | STOMATOLOGICAL PREPARATIONS | Caries prophylactic agents |

## Table: binding_sites
Columns:
- site_id BIGINT NOT NULL PK
- site_name VARCHAR(200) NULL
- tid BIGINT NULL

Sample rows:
| site_id | site_name | tid |
|---|---|---|
| 2 | UDP-glucuronosyltransferase 1-10, UDPGT domain | 104088 |
| 3 | Mitogen-activated protein kinase 8, Pkinase domain | 104254 |
| 4 | Inosine-5'-monophosphate dehydrogenase 1, IMPDH domain | 84 |

## Table: bio_component_sequences
Columns:
- component_id BIGINT NOT NULL PK
- component_type VARCHAR(50) NULL
- description VARCHAR(200) NULL
- sequence TEXT NULL
- sequence_md5sum VARCHAR(32) NULL
- tax_id BIGINT NULL
- organism VARCHAR(150) NULL

Sample rows:
| component_id | component_type | description | sequence | sequence_md5sum | tax_id | organism |
|---|---|---|---|---|---|---|
| 24362 | NULL | Disulfide bridges | 22-96 $ 22''-96'' $ 22'-89' $ 22'''-89''' $ 138'-197' $ 138'''-197''' $ 144-2... | 30B10ECD103F1C5B50C26CC3C24F5428 | NULL | NULL |
| 24363 | Protein | Sequence | NDWFL | 3B57E34FE0EB7BDF38B9234170196F72 | NULL | NULL |
| 24364 | Protein | Light chain | QSVLTQPPSASGTPGQRVTISCSGSISNIGRNPVNWYQQLPGTAPKLLIYLDNLRLSGVPDRFSGSKSGTSASLAIS... | 537DE6817F4AEFC8DFF18C52E8403818 | NULL | NULL |

## Table: bioassay_ontology
Columns:
- bao_id VARCHAR(11) NOT NULL PK
- label VARCHAR(100) NOT NULL

Sample rows:
| bao_id | label |
|---|---|
| BAO_0000006 | percent cytotoxicity |
| BAO_0000007 | nucleosome format |
| BAO_0000008 | bioassay type |

## Table: biotherapeutic_components
Columns:
- biocomp_id BIGINT NOT NULL PK
- molregno BIGINT NOT NULL
- component_id BIGINT NOT NULL

Sample rows:
| biocomp_id | molregno | component_id |
|---|---|---|
| 3702 | 2096437 | 26904 |
| 3703 | 2832659 | 27014 |
| 3704 | 2832303 | 27018 |

## Table: biotherapeutics
Columns:
- molregno BIGINT NOT NULL PK
- description VARCHAR(2000) NULL
- helm_notation VARCHAR(4000) NULL

Sample rows:
| molregno | description | helm_notation |
|---|---|---|
| 197 | NULL | PEPTIDE1{A.L.Y.A.S.K.L.S.[am]}$$$$ |
| 326 | NULL | PEPTIDE1{[meR].K.P.W.[Tle].L}$$$$ |
| 364 | NULL | PEPTIDE1{[X833].[dP].W.[Tle].[X454]}$$$$ |

## Table: cell_dictionary
Columns:
- cell_id BIGINT NOT NULL PK
- cell_name VARCHAR(50) NOT NULL
- cell_description VARCHAR(200) NULL
- cell_source_tissue VARCHAR(50) NULL
- cell_source_organism VARCHAR(150) NULL
- cell_source_tax_id BIGINT NULL
- clo_id VARCHAR(11) NULL
- efo_id VARCHAR(12) NULL
- cellosaurus_id VARCHAR(15) NULL
- cl_lincs_id VARCHAR(8) NULL
- chembl_id VARCHAR(20) NULL
- cell_ontology_id VARCHAR(10) NULL

Sample rows:
| cell_id | cell_name | cell_description | cell_source_tissue | cell_source_organism | cell_source_tax_id | clo_id | efo_id | cellosaurus_id | cl_lincs_id | chembl_id | cell_ontology_id |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | DC3F | DC3F | Lung | Cricetulus griseus | 10029 | NULL | NULL | CVCL_4704 | NULL | CHEMBL3307241 | NULL |
| 2 | P3HR-1 | P3HR-1 | Lyphoma | Homo sapiens | 9606 | CLO_0008331 | EFO_0002312 | CVCL_2676 | LCL-2024 | CHEMBL3307242 | NULL |
| 3 | UCLA P-3 | UCLA P-3 | Lung Adenocarcinoma | Homo sapiens | 9606 | NULL | NULL | CVCL_N513 | NULL | CHEMBL3307243 | NULL |

## Table: chembl_id_lookup
Columns:
- chembl_id VARCHAR(20) NOT NULL PK
- entity_type VARCHAR(50) NOT NULL
- entity_id BIGINT NOT NULL
- status VARCHAR(10) NOT NULL
- last_active INTEGER NULL

Sample rows:
| chembl_id | entity_type | entity_id | status | last_active |
|---|---|---|---|---|
| CHEMBL1 | COMPOUND | 517180 | ACTIVE | 36 |
| CHEMBL10 | COMPOUND | 250 | ACTIVE | 36 |
| CHEMBL100 | COMPOUND | 12356 | ACTIVE | 36 |

## Table: chembl_release
Columns:
- chembl_release_id INTEGER NOT NULL PK
- chembl_release VARCHAR(20) NULL
- creation_date DATETIME NULL

Sample rows:
| chembl_release_id | chembl_release | creation_date |
|---|---|---|
| 1 | CHEMBL_1 | 2009-09-03 00:00:00.000000 |
| 2 | CHEMBL_2 | 2009-11-30 00:00:00.000000 |
| 3 | CHEMBL_3 | 2010-04-16 00:00:00.000000 |

## Table: component_class
Columns:
- component_id BIGINT NOT NULL
- protein_class_id BIGINT NOT NULL
- comp_class_id BIGINT NOT NULL PK

Sample rows:
| component_id | protein_class_id | comp_class_id |
|---|---|---|
| 1 | 1173 | 1 |
| 2 | 422 | 2 |
| 3 | 12 | 3 |

## Table: component_domains
Columns:
- compd_id BIGINT NOT NULL PK
- domain_id BIGINT NULL
- component_id BIGINT NOT NULL
- start_position BIGINT NULL
- end_position BIGINT NULL

Sample rows:
| compd_id | domain_id | component_id | start_position | end_position |
|---|---|---|---|---|
| 516101 | 3658 | 47 | 38 | 241 |
| 516102 | 3658 | 48 | 42 | 249 |
| 516103 | 3658 | 49 | 39 | 242 |

## Table: component_go
Columns:
- comp_go_id BIGINT NOT NULL PK
- component_id BIGINT NOT NULL
- go_id VARCHAR(10) NOT NULL

Sample rows:
| comp_go_id | component_id | go_id |
|---|---|---|
| 2833043 | 1 | GO:0005575 |
| 2833044 | 1 | GO:0005886 |
| 2833045 | 1 | GO:0016020 |

## Table: component_sequences
Columns:
- component_id BIGINT NOT NULL PK
- component_type VARCHAR(50) NULL
- accession VARCHAR(25) NULL
- sequence TEXT NULL
- sequence_md5sum VARCHAR(32) NULL
- description VARCHAR(200) NULL
- tax_id BIGINT NULL
- organism VARCHAR(150) NULL
- db_source VARCHAR(25) NULL
- db_version VARCHAR(10) NULL

Sample rows:
| component_id | component_type | accession | sequence | sequence_md5sum | description | tax_id | organism | db_source | db_version |
|---|---|---|---|---|---|---|---|---|---|
| 1 | PROTEIN | O09028 | MSYSLYLAFVCLNLLAQRMCIQGNQFNVEVSRSDKLSLPGFENLTAGYNKFLRPNFGGDPVRIALTLDIASISSISE... | 7473be17a767c25bb1d57beee67ffff7 | Gamma-aminobutyric acid receptor subunit pi | 10116 | Rattus norvegicus | SWISS-PROT | 2025_03 |
| 2 | PROTEIN | P02708 | MEPWPLLLLFSLCSAGLVLGSEHETRLVAKLFKDYSSVVRPVEDHRQVVEVTVGLQLIQLINVDEVNQIVTTNVRLK... | c55fcab2ffecb6bac66c25960ddfe057 | Acetylcholine receptor subunit alpha | 9606 | Homo sapiens | SWISS-PROT | 2025_03 |
| 3 | PROTEIN | P04637 | MEEPQSDPSVEPPLSQETFSDLWKLLPENNVLSPLPSQAMDDLMLSPDDIEQWFTEDPGPDEAPRMPEAAPPVAPAP... | c133dfce69f606f20865e9008199f852 | Cellular tumor antigen p53 | 9606 | Homo sapiens | SWISS-PROT | 2025_03 |

## Table: component_synonyms
Columns:
- compsyn_id BIGINT NOT NULL PK
- component_id BIGINT NOT NULL
- component_synonym VARCHAR(500) NULL
- syn_type VARCHAR(20) NULL

Sample rows:
| compsyn_id | component_id | component_synonym | syn_type |
|---|---|---|---|
| 860862 | 48 | Gabra-1 | GENE_SYMBOL_OTHER |
| 860867 | 49 | Gabrb-3 | GENE_SYMBOL_OTHER |
| 860872 | 50 | Gabrb-2 | GENE_SYMBOL_OTHER |

## Table: compound_properties
Columns:
- molregno BIGINT NOT NULL PK
- mw_freebase NUMERIC(9, 2) NULL
- alogp NUMERIC(9, 2) NULL
- hba INTEGER NULL
- hbd INTEGER NULL
- psa NUMERIC(9, 2) NULL
- rtb INTEGER NULL
- ro3_pass VARCHAR(3) NULL
- num_ro5_violations SMALLINT NULL
- full_mwt NUMERIC(9, 2) NULL
- aromatic_rings INTEGER NULL
- heavy_atoms INTEGER NULL
- qed_weighted NUMERIC(3, 2) NULL
- full_molformula VARCHAR(100) NULL
- np_likeness_score NUMERIC(3, 2) NULL

Sample rows:
| molregno | mw_freebase | alogp | hba | hbd | psa | rtb | ro3_pass | num_ro5_violations | full_mwt | aromatic_rings | heavy_atoms | qed_weighted | full_molformula | np_likeness_score |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | 341.75 | 2.11 | 5 | 1 | 84.82 | 3 | N | 0 | 341.75 | 3 | 24 | 0.74 | C17H12ClN3O3 | -1.56 |
| 2 | 332.32 | 1.33 | 6 | 1 | 108.61 | 3 | N | 0 | 332.32 | 3 | 25 | 0.73 | C18H12N4O3 | -1.59 |
| 3 | 357.8 | 2.27 | 5 | 2 | 87.98 | 3 | N | 0 | 357.8 | 3 | 25 | 0.75 | C18H16ClN3O3 | -0.82 |

## Table: compound_records
Columns:
- record_id BIGINT NOT NULL PK
- molregno BIGINT NULL
- doc_id BIGINT NOT NULL
- compound_key VARCHAR(250) NULL
- compound_name VARCHAR(4000) NULL
- src_id INTEGER NOT NULL
- src_compound_id VARCHAR(150) NULL
- cidx VARCHAR(200) NOT NULL

Sample rows:
| record_id | molregno | doc_id | compound_key | compound_name | src_id | src_compound_id | cidx |
|---|---|---|---|---|---|---|---|
| 1 | 1798298 | 11788 | X | Bis(3-[14-Benzyl-11-(1H-indol-3-ylmethyl)-2-isobutyl-13-methyl-5-(2-methylsul... | 1 | NULL | CLD0 |
| 2 | 1798410 | 11788 | V | 3-[11,14-Dibenzyl-2-isobutyl-5-(2-methylsulfanyl-ethyl)-3,6,9,12,15,20-hexaox... | 1 | NULL | CLD0 |
| 3 | 1798299 | 11788 | IX | 3-[14-Benzyl-11-(1H-indol-3-ylmethyl)-2-isobutyl-13-methyl-5-(2-methylsulfany... | 1 | NULL | CLD0 |

## Table: compound_structural_alerts
Columns:
- cpd_str_alert_id BIGINT NOT NULL PK
- molregno BIGINT NOT NULL
- alert_id BIGINT NOT NULL

Sample rows:
| cpd_str_alert_id | molregno | alert_id |
|---|---|---|
| 83590421 | 103 | 1 |
| 83590422 | 105 | 1 |
| 83590423 | 638 | 1 |

## Table: compound_structures
Columns:
- molregno BIGINT NOT NULL PK
- molfile TEXT NULL
- standard_inchi VARCHAR(4000) NULL
- standard_inchi_key VARCHAR(27) NOT NULL
- canonical_smiles VARCHAR(4000) NULL

Sample rows:
| molregno | molfile | standard_inchi | standard_inchi_key | canonical_smiles |
|---|---|---|---|---|
| 1 | \n     RDKit          2D\n\n 24 26  0  0  0  0  0  0  0  0999 V2000\n    5.27... | InChI=1S/C17H12ClN3O3/c1-10-8-11(21-17(24)20-15(22)9-19-21)6-7-12(10)16(23)13... | OWRSAHYFSSNENM-UHFFFAOYSA-N | Cc1cc(-n2ncc(=O)[nH]c2=O)ccc1C(=O)c1ccccc1Cl |
| 2 | \n     RDKit          2D\n\n 25 27  0  0  0  0  0  0  0  0999 V2000\n    5.27... | InChI=1S/C18H12N4O3/c1-11-8-14(22-18(25)21-16(23)10-20-22)6-7-15(11)17(24)13-... | ZJYUMURGSZQFMH-UHFFFAOYSA-N | Cc1cc(-n2ncc(=O)[nH]c2=O)ccc1C(=O)c1ccc(C#N)cc1 |
| 3 | \n     RDKit          2D\n\n 25 27  0  0  0  0  0  0  0  0999 V2000\n    3.80... | InChI=1S/C18H16ClN3O3/c1-10-7-14(22-18(25)21-15(23)9-20-22)8-11(2)16(10)17(24... | YOMWDCALSDWFSV-UHFFFAOYSA-N | Cc1cc(-n2ncc(=O)[nH]c2=O)cc(C)c1C(O)c1ccc(Cl)cc1 |

## Table: confidence_score_lookup
Columns:
- confidence_score SMALLINT NOT NULL PK
- description VARCHAR(100) NOT NULL
- target_mapping VARCHAR(30) NOT NULL

Sample rows:
| confidence_score | description | target_mapping |
|---|---|---|
| 0 | Default value - Target unknown or has yet to be assigned | Unassigned |
| 1 | Target assigned is non-molecular | Non-molecular |
| 2 | Target assigned is subcellular fraction | Subcellular fraction |

## Table: curation_lookup
Columns:
- curated_by VARCHAR(32) NOT NULL PK
- description VARCHAR(100) NOT NULL

Sample rows:
| curated_by | description |
|---|---|
| Autocuration | Curated against extractor target assignment |
| Expert | Curated against ChEMBL target assignment from original publication |
| Intermediate | Curated against ChEMBL target assignment from assay description |

## Table: data_validity_lookup
Columns:
- data_validity_comment VARCHAR(30) NOT NULL PK
- description VARCHAR(200) NULL

Sample rows:
| data_validity_comment | description |
|---|---|
| Author confirmed error | Error in publication - Author confirmed (personal communication) |
| Manually validated | Data have been checked against the publication and are believed to be accurate |
| Non standard unit for type | Units for this activity type are unusual and may be incorrect (or the standar... |

## Table: defined_daily_dose
Columns:
- atc_code VARCHAR(10) NOT NULL
- ddd_units VARCHAR(200) NULL
- ddd_admr VARCHAR(1000) NULL
- ddd_comment VARCHAR(2000) NULL
- ddd_id BIGINT NOT NULL PK
- ddd_value NUMERIC NULL

Sample rows:
| atc_code | ddd_units | ddd_admr | ddd_comment | ddd_id | ddd_value |
|---|---|---|---|---|---|
| A01AA03 | mg | O | NULL | 2 | 1.1 |
| A01AB02 | mg | O | NULL | 3 | 60 |
| A01AB03 | mg | O | NULL | 4 | 30 |

## Table: docs
Columns:
- doc_id BIGINT NOT NULL PK
- journal VARCHAR(50) NULL
- year INTEGER NULL
- volume VARCHAR(50) NULL
- issue VARCHAR(50) NULL
- first_page VARCHAR(50) NULL
- last_page VARCHAR(50) NULL
- pubmed_id BIGINT NULL
- doi VARCHAR(100) NULL
- chembl_id VARCHAR(20) NOT NULL
- title VARCHAR(500) NULL
- doc_type VARCHAR(50) NOT NULL
- authors VARCHAR(4000) NULL
- abstract TEXT NULL
- patent_id VARCHAR(20) NULL
- ridx VARCHAR(200) NOT NULL
- src_id INTEGER NOT NULL
- chembl_release_id INTEGER NULL
- contact VARCHAR(200) NULL

Sample rows:
| doc_id | journal | year | volume | issue | first_page | last_page | pubmed_id | doi | chembl_id | title | doc_type | authors | abstract | patent_id | ridx | src_id | chembl_release_id | contact |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| -1 | NULL | NULL | NULL | NULL | NULL | NULL | NULL | NULL | CHEMBL1158643 | Unpublished dataset | DATASET | NULL | NULL | NULL | CLD0 | 0 | 7 | NULL |
| 1 | J Med Chem | 2004 | 47 | 1 | 1 | 9 | 14695813 | 10.1021/jm030283g | CHEMBL1139451 | The discovery of ezetimibe: a view from outside the receptor. | PUBLICATION | Clader JW. | NULL | NULL | CLD0 | 1 | 1 | NULL |
| 2 | J Med Chem | 2004 | 47 | 1 | 10 | 13 | 14695814 | 10.1021/jm034189b | CHEMBL1148466 | Self-association of okadaic acid upon complexation with potassium ion. | PUBLICATION | Daranas AH, Fernández JJ, Morales EQ, Norte M, Gavín JA. | Okadaic acid (OA) is a toxin responsible for diarrhetic shellfish poisoning a... | NULL | CLD0 | 1 | 1 | NULL |

## Table: domains
Columns:
- domain_id BIGINT NOT NULL PK
- domain_type VARCHAR(20) NOT NULL
- source_domain_id VARCHAR(20) NOT NULL
- domain_name VARCHAR(100) NULL
- domain_description VARCHAR(500) NULL

Sample rows:
| domain_id | domain_type | source_domain_id | domain_name | domain_description |
|---|---|---|---|---|
| 2627 | Pfam-A | PF00001 | 7tm_1 | NULL |
| 2628 | Pfam-A | PF00002 | 7tm_2 | NULL |
| 2629 | Pfam-A | PF00003 | 7tm_3 | NULL |

## Table: drug_indication
Columns:
- drugind_id BIGINT NOT NULL PK
- record_id BIGINT NOT NULL
- molregno BIGINT NULL
- max_phase_for_ind NUMERIC(2, 1) NULL
- mesh_id VARCHAR(20) NOT NULL
- mesh_heading VARCHAR(200) NOT NULL
- efo_id VARCHAR(20) NULL
- efo_term VARCHAR(200) NULL

Sample rows:
| drugind_id | record_id | molregno | max_phase_for_ind | mesh_id | mesh_heading | efo_id | efo_term |
|---|---|---|---|---|---|---|---|
| 22606 | 1390869 | 675774 | 2 | D045743 | Scleroderma, Diffuse | EFO:0000404 | diffuse scleroderma |
| 22607 | 1390869 | 675774 | 4 | D001172 | Arthritis, Rheumatoid | EFO:0000685 | rheumatoid arthritis |
| 22609 | 1343491 | 675576 | 3 | D009203 | Myocardial Infarction | EFO:0000612 | myocardial infarction |

## Table: drug_mechanism
Columns:
- mec_id BIGINT NOT NULL PK
- record_id BIGINT NOT NULL
- molregno BIGINT NULL
- mechanism_of_action VARCHAR(250) NULL
- tid BIGINT NULL
- site_id BIGINT NULL
- action_type VARCHAR(50) NULL
- direct_interaction SMALLINT NULL
- molecular_mechanism SMALLINT NULL
- disease_efficacy SMALLINT NULL
- mechanism_comment VARCHAR(2000) NULL
- selectivity_comment VARCHAR(1000) NULL
- binding_site_comment VARCHAR(1000) NULL
- variant_id BIGINT NULL

Sample rows:
| mec_id | record_id | molregno | mechanism_of_action | tid | site_id | action_type | direct_interaction | molecular_mechanism | disease_efficacy | mechanism_comment | selectivity_comment | binding_site_comment | variant_id |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 13 | 1343810 | 1124 | Carbonic anhydrase VII inhibitor | 11060 | NULL | INHIBITOR | 1 | 1 | 1 | NULL | NULL | NULL | NULL |
| 14 | 1344053 | 675068 | Carbonic anhydrase I inhibitor | 10193 | NULL | INHIBITOR | 1 | 1 | 1 | NULL | NULL | NULL | NULL |
| 15 | 1344649 | 674765 | Carbonic anhydrase I inhibitor | 10193 | NULL | INHIBITOR | 1 | 1 | 1 | Expressed in eye | NULL | NULL | NULL |

## Table: drug_warning
Columns:
- warning_id BIGINT NOT NULL PK
- record_id BIGINT NULL
- molregno BIGINT NULL
- warning_type VARCHAR(20) NULL
- warning_class VARCHAR(100) NULL
- warning_description VARCHAR(4000) NULL
- warning_country VARCHAR(1000) NULL
- warning_year INTEGER NULL
- efo_term VARCHAR(200) NULL
- efo_id VARCHAR(20) NULL
- efo_id_for_warning_class VARCHAR(20) NULL

Sample rows:
| warning_id | record_id | molregno | warning_type | warning_class | warning_description | warning_country | warning_year | efo_term | efo_id | efo_id_for_warning_class |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | 1343079 | 2341159 | Black Box Warning | hepatotoxicity | NULL | United States | NULL | NULL | NULL | EFO:0011052 |
| 2 | 1343079 | 2341159 | Black Box Warning | metabolic toxicity | NULL | United States | NULL | NULL | NULL | EFO:0011054 |
| 3 | 1343079 | 2341159 | Black Box Warning | immune system toxicity | NULL | United States | NULL | NULL | NULL | EFO:0011053 |

## Table: formulations
Columns:
- product_id VARCHAR(30) NOT NULL
- ingredient VARCHAR(200) NULL
- strength VARCHAR(300) NULL
- record_id BIGINT NOT NULL
- molregno BIGINT NULL
- formulation_id BIGINT NOT NULL PK

Sample rows:
| product_id | ingredient | strength | record_id | molregno | formulation_id |
|---|---|---|---|---|---|
| PRODUCT_202428_001 | TAZAROTENE | 0.1% | 1344996 | 495572 | 102341 |
| PRODUCT_021812_001 | MINOXIDIL | 5% | 1343290 | 51042 | 102345 |
| PRODUCT_022563_001 | CALCIPOTRIENE | 0.005% | 1343920 | 674617 | 102349 |

## Table: go_classification
Columns:
- go_id VARCHAR(10) NOT NULL PK
- parent_go_id VARCHAR(10) NULL
- pref_name VARCHAR(200) NULL
- class_level SMALLINT NULL
- aspect VARCHAR(1) NULL
- path VARCHAR(1000) NULL

Sample rows:
| go_id | parent_go_id | pref_name | class_level | aspect | path |
|---|---|---|---|---|---|
| GO:0000003 | GO:0008150 | reproduction | 1 | P | biological_process  reproduction |
| GO:0000149 | GO:0005515 | SNARE binding | 2 | F | molecular_function  protein binding  SNARE binding |
| GO:0000166 | GO:0003674 | nucleotide binding | 1 | F | molecular_function  nucleotide binding |

## Table: indication_refs
Columns:
- indref_id BIGINT NOT NULL PK
- drugind_id BIGINT NOT NULL
- ref_type VARCHAR(50) NOT NULL
- ref_id VARCHAR(4000) NOT NULL
- ref_url VARCHAR(4000) NOT NULL

Sample rows:
| indref_id | drugind_id | ref_type | ref_id | ref_url |
|---|---|---|---|---|
| 682606 | 126883 | FDA | label/2015/205739s000lbl.pdf | http://www.accessdata.fda.gov/drugsatfda_docs/label/2015/205739s000lbl.pdf |
| 682608 | 22630 | EMA | EMEA/H/C/002211 | https://www.ema.europa.eu/en/medicines/human/EPAR/eklira-genuair |
| 682609 | 22630 | ClinicalTrials | NCT00358436,NCT00363896,NCT00435760,NCT00500318,NCT00626522,NCT00891462,NCT00... | https://clinicaltrials.gov/search?term=NCT00358436%20NCT00363896%20NCT0043576... |

## Table: ligand_eff
Columns:
- activity_id BIGINT NOT NULL PK
- bei NUMERIC(9, 2) NULL
- sei NUMERIC(9, 2) NULL
- le NUMERIC(9, 2) NULL
- lle NUMERIC(9, 2) NULL

Sample rows:
| activity_id | bei | sei | le | lle |
|---|---|---|---|---|
| 31864 | 14.06 | 5.56 | 0.26 | 1.3 |
| 31866 | 9.69 | 4.23 | 0.18 | -0.63 |
| 31868 | 9.94 | 6.93 | 0.2 | 1.13 |

## Table: mechanism_refs
Columns:
- mecref_id BIGINT NOT NULL PK
- mec_id BIGINT NOT NULL
- ref_type VARCHAR(50) NOT NULL
- ref_id VARCHAR(400) NULL
- ref_url VARCHAR(400) NULL

Sample rows:
| mecref_id | mec_id | ref_type | ref_id | ref_url |
|---|---|---|---|---|
| 2 | 13 | PubMed | 18336310 | http://europepmc.org/abstract/MED/18336310 |
| 3 | 13 | DailyMed | setid=8e162b6d-8fa6-45f6-80d8-5132d94c1207 | http://dailymed.nlm.nih.gov/dailymed/lookup.cfm?setid=8e162b6d-8fa6-45f6-80d8... |
| 4 | 14 | PubMed | 1460006 | http://europepmc.org/abstract/MED/1460006 |

## Table: metabolism
Columns:
- met_id BIGINT NOT NULL PK
- drug_record_id BIGINT NULL
- substrate_record_id BIGINT NULL
- metabolite_record_id BIGINT NULL
- pathway_id BIGINT NULL
- pathway_key VARCHAR(50) NULL
- enzyme_name VARCHAR(200) NULL
- enzyme_tid BIGINT NULL
- met_conversion VARCHAR(200) NULL
- organism VARCHAR(100) NULL
- tax_id BIGINT NULL
- met_comment VARCHAR(1000) NULL

Sample rows:
| met_id | drug_record_id | substrate_record_id | metabolite_record_id | pathway_id | pathway_key | enzyme_name | enzyme_tid | met_conversion | organism | tax_id | met_comment |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 119 | 2468083 | 2468090 | 2468102 | 1 | Fig. 2, p.19 | NULL | NULL | NULL | Homo sapiens | 9606 | NULL |
| 120 | 2468083 | 2468083 | 2468093 | 1 | Fig. 2, p.19 | NULL | NULL | NULL | Homo sapiens | 9606 | NULL |
| 121 | 2468083 | 2468083 | 2468103 | 1 | Fig. 2, p.19 | NULL | NULL | NULL | Homo sapiens | 9606 | NULL |

## Table: metabolism_refs
Columns:
- metref_id BIGINT NOT NULL PK
- met_id BIGINT NOT NULL
- ref_type VARCHAR(50) NOT NULL
- ref_id VARCHAR(200) NULL
- ref_url VARCHAR(400) NULL

Sample rows:
| metref_id | met_id | ref_type | ref_id | ref_url |
|---|---|---|---|---|
| 39 | 119 | OTHER | http://www.accessdata.fda.gov/drugsatfda_docs/nda/99/50-778_Ellence_biopharmr... | http://www.accessdata.fda.gov/drugsatfda_docs/nda/99/50-778_Ellence_biopharmr... |
| 40 | 120 | OTHER | http://www.accessdata.fda.gov/drugsatfda_docs/nda/99/50-778_Ellence_biopharmr... | http://www.accessdata.fda.gov/drugsatfda_docs/nda/99/50-778_Ellence_biopharmr... |
| 41 | 121 | OTHER | http://www.accessdata.fda.gov/drugsatfda_docs/nda/99/50-778_Ellence_biopharmr... | http://www.accessdata.fda.gov/drugsatfda_docs/nda/99/50-778_Ellence_biopharmr... |

## Table: molecule_atc_classification
Columns:
- mol_atc_id BIGINT NOT NULL PK
- level5 VARCHAR(10) NOT NULL
- molregno BIGINT NOT NULL

Sample rows:
| mol_atc_id | level5 | molregno |
|---|---|---|
| 95928 | L01EA06 | 2286380 |
| 95929 | L01EX15 | 2089491 |
| 95930 | L01EX10 | 608601 |

## Table: molecule_dictionary
Columns:
- molregno BIGINT NOT NULL PK
- pref_name VARCHAR(255) NULL
- chembl_id VARCHAR(20) NOT NULL
- max_phase NUMERIC(2, 1) NULL
- therapeutic_flag SMALLINT NOT NULL
- dosed_ingredient SMALLINT NOT NULL
- structure_type VARCHAR(10) NOT NULL
- molecule_type VARCHAR(30) NULL
- first_approval INTEGER NULL
- oral SMALLINT NOT NULL
- parenteral SMALLINT NOT NULL
- topical SMALLINT NOT NULL
- black_box_warning SMALLINT NOT NULL
- natural_product SMALLINT NOT NULL
- first_in_class SMALLINT NOT NULL
- chirality SMALLINT NOT NULL
- prodrug SMALLINT NOT NULL
- inorganic_flag SMALLINT NOT NULL
- usan_year INTEGER NULL
- availability_type SMALLINT NULL
- usan_stem VARCHAR(50) NULL
- polymer_flag SMALLINT NULL
- usan_substem VARCHAR(50) NULL
- usan_stem_definition VARCHAR(1000) NULL
- withdrawn_flag SMALLINT NOT NULL
- chemical_probe SMALLINT NOT NULL
- orphan SMALLINT NOT NULL
- veterinary SMALLINT NULL

Sample rows:
| molregno | pref_name | chembl_id | max_phase | therapeutic_flag | dosed_ingredient | structure_type | molecule_type | first_approval | oral | parenteral | topical | black_box_warning | natural_product | first_in_class | chirality | prodrug | inorganic_flag | usan_year | availability_type | usan_stem | polymer_flag | usan_substem | usan_stem_definition | withdrawn_flag | chemical_probe | orphan | veterinary |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | NULL | CHEMBL6329 | NULL | 0 | 0 | MOL | Small molecule | NULL | 0 | 0 | 0 | 0 | 0 | -1 | -1 | -1 | -1 | NULL | -1 | NULL | 0 | NULL | NULL | 0 | 0 | -1 | -1 |
| 2 | NULL | CHEMBL6328 | NULL | 0 | 0 | MOL | Small molecule | NULL | 0 | 0 | 0 | 0 | 0 | -1 | -1 | -1 | -1 | NULL | -1 | NULL | 0 | NULL | NULL | 0 | 0 | -1 | -1 |
| 3 | NULL | CHEMBL265667 | NULL | 0 | 0 | MOL | Small molecule | NULL | 0 | 0 | 0 | 0 | 0 | -1 | -1 | -1 | -1 | NULL | -1 | NULL | 0 | NULL | NULL | 0 | 0 | -1 | -1 |

## Table: molecule_hierarchy
Columns:
- molregno BIGINT NOT NULL PK
- parent_molregno BIGINT NULL
- active_molregno BIGINT NULL

Sample rows:
| molregno | parent_molregno | active_molregno |
|---|---|---|
| 1 | 1 | 1 |
| 2 | 2 | 2 |
| 3 | 3 | 3 |

## Table: molecule_synonyms
Columns:
- molregno BIGINT NOT NULL
- syn_type VARCHAR(50) NOT NULL
- molsyn_id BIGINT NOT NULL PK
- synonyms VARCHAR(250) NULL

Sample rows:
| molregno | syn_type | molsyn_id | synonyms |
|---|---|---|---|
| 463 | RESEARCH_CODE | 93 | Ro-481220 |
| 634 | RESEARCH_CODE | 119 | Ro-151310 |
| 868 | RESEARCH_CODE | 194 | Ro-147437 |

## Table: organism_class
Columns:
- oc_id BIGINT NOT NULL PK
- tax_id BIGINT NULL
- l1 VARCHAR(200) NULL
- l2 VARCHAR(200) NULL
- l3 VARCHAR(200) NULL

Sample rows:
| oc_id | tax_id | l1 | l2 | l3 |
|---|---|---|---|---|
| 1 | 10030 | Eukaryotes | Mammalia | Rodentia |
| 2 | 9593 | Eukaryotes | Mammalia | Primates |
| 3 | 470 | Bacteria | Gram-Negative | Acinetobacter |

## Table: patent_use_codes
Columns:
- patent_use_code VARCHAR(8) NOT NULL PK
- definition VARCHAR(500) NOT NULL

Sample rows:
| patent_use_code | definition |
|---|---|
| U-1 | PREVENTION OF PREGNANCY |
| U-10 | DIAGNOSTIC METHOD FOR DISTINGUISHING BETWEEN HYPOTHALAMIC MALFUNCTIONS OR LES... |
| U-100 | METHOD OF TREATING OCULAR INFLAMMATION |

## Table: pesticide_class_mapping
Columns:
- mol_pest_id BIGINT NOT NULL PK
- pest_class_id BIGINT NULL
- molregno BIGINT NULL

Sample rows:
| mol_pest_id | pest_class_id | molregno |
|---|---|---|
| 1 | 1 | 347123 |
| 2 | 2 | 387915 |
| 3 | 3 | 1494107 |

## Table: pesticide_classification
Columns:
- pest_class_id BIGINT NOT NULL PK
- compound_name VARCHAR(2000) NULL
- mec_id BIGINT NULL
- mechanism_comment VARCHAR(2000) NULL
- ref_type VARCHAR(50) NULL
- ref_id VARCHAR(400) NULL
- ref_url VARCHAR(400) NULL

Sample rows:
| pest_class_id | compound_name | mec_id | mechanism_comment | ref_type | ref_id | ref_url |
|---|---|---|---|---|---|---|
| 1 | acibenzolar-S-methyl | NULL | salicylate-related | FRAC | FRAC Code List 2024 | https://www.frac.info/knowledge-database/downloads |
| 2 | fenazaquin | NULL | complex I NADH oxido-reductase | FRAC | FRAC Code List 2024 | https://www.frac.info/knowledge-database/downloads |
| 3 | probenazole | NULL | salicylate-related | FRAC | FRAC Code List 2024 | https://www.frac.info/knowledge-database/downloads |

## Table: predicted_binding_domains
Columns:
- predbind_id BIGINT NOT NULL PK
- activity_id BIGINT NULL
- site_id BIGINT NULL
- prediction_method VARCHAR(50) NULL
- confidence VARCHAR(10) NULL

Sample rows:
| predbind_id | activity_id | site_id | prediction_method | confidence |
|---|---|---|---|---|
| 7699241 | 1451903 | 1466 | Single domain | high |
| 7699242 | 1451927 | 1133 | Single domain | high |
| 7699243 | 1452215 | 1248 | Single domain | high |

## Table: product_patents
Columns:
- prod_pat_id BIGINT NOT NULL PK
- product_id VARCHAR(30) NOT NULL
- patent_no VARCHAR(20) NOT NULL
- patent_expire_date DATETIME NOT NULL
- drug_substance_flag SMALLINT NOT NULL
- drug_product_flag SMALLINT NOT NULL
- patent_use_code VARCHAR(10) NULL
- delist_flag SMALLINT NOT NULL
- submission_date DATETIME NULL

Sample rows:
| prod_pat_id | product_id | patent_no | patent_expire_date | drug_substance_flag | drug_product_flag | patent_use_code | delist_flag | submission_date |
|---|---|---|---|---|---|---|---|---|
| 257 | PRODUCT_050805_001 | 8394406 | 2024-04-07 00:00:00.000000 | 0 | 1 | U-925 | 0 | 2013-03-25 00:00:00.000000 |
| 259 | PRODUCT_050808_008 | 8268804 | 2025-06-24 00:00:00.000000 | 0 | 0 | U-1078 | 0 | NULL |
| 260 | PRODUCT_050808_007 | 7919483 | 2027-03-07 00:00:00.000000 | 0 | 0 | U-1078 | 0 | NULL |

## Table: products
Columns:
- dosage_form VARCHAR(200) NULL
- route VARCHAR(200) NULL
- trade_name VARCHAR(200) NULL
- approval_date DATETIME NULL
- ad_type VARCHAR(5) NULL
- oral SMALLINT NULL
- topical SMALLINT NULL
- parenteral SMALLINT NULL
- black_box_warning SMALLINT NULL
- applicant_full_name VARCHAR(200) NULL
- innovator_company SMALLINT NULL
- product_id VARCHAR(30) NOT NULL PK
- nda_type VARCHAR(10) NULL

Sample rows:
| dosage_form | route | trade_name | approval_date | ad_type | oral | topical | parenteral | black_box_warning | applicant_full_name | innovator_company | product_id | nda_type |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| SOLUTION/DROPS | OPHTHALMIC | PAREDRINE | 1982-01-01 00:00:00.000000 | DISCN | 0 | 1 | 0 | NULL | PHARMICS INC | 0 | PRODUCT_000004_004 | N |
| TABLET | ORAL | SULFAPYRIDINE | 1982-01-01 00:00:00.000000 | DISCN | 1 | 0 | 0 | NULL | ELI LILLY AND CO | 0 | PRODUCT_000159_001 | N |
| INJECTABLE | INJECTION | LIQUAEMIN SODIUM | 1982-01-01 00:00:00.000000 | DISCN | 0 | 0 | 1 | NULL | ASPEN GLOBAL INC | 0 | PRODUCT_000552_001 | N |

## Table: protein_class_synonyms
Columns:
- protclasssyn_id BIGINT NOT NULL PK
- protein_class_id BIGINT NOT NULL
- protein_class_synonym VARCHAR(1000) NULL
- syn_type VARCHAR(20) NULL

Sample rows:
| protclasssyn_id | protein_class_id | protein_class_synonym | syn_type |
|---|---|---|---|
| 33666 | 1 | Enzyme | CONCEPT_WIKI |
| 33667 | 1 | Enzymes | CONCEPT_WIKI |
| 33668 | 1 | Biocatalysts | CONCEPT_WIKI |

## Table: protein_classification
Columns:
- protein_class_id BIGINT NOT NULL PK
- parent_id BIGINT NULL
- pref_name VARCHAR(500) NULL
- short_name VARCHAR(50) NULL
- protein_class_desc VARCHAR(410) NOT NULL
- definition VARCHAR(4000) NULL
- class_level BIGINT NOT NULL

Sample rows:
| protein_class_id | parent_id | pref_name | short_name | protein_class_desc | definition | class_level |
|---|---|---|---|---|---|---|
| 0 | NULL | Protein class | Protein class | protein class | Root of the ChEMBL protein family classification | 0 |
| 1 | 0 | Enzyme | Enzyme | enzyme | Biological molecules that possess catalytic activity. They may occur naturall... | 1 |
| 2 | 0 | Adhesion | Adhesion | adhesion | Surface ligands, usually glycoproteins, that mediate cell-to-cell adhesion. T... | 1 |

## Table: relationship_type
Columns:
- relationship_type VARCHAR(1) NOT NULL PK
- relationship_desc VARCHAR(250) NULL

Sample rows:
| relationship_type | relationship_desc |
|---|---|
| D | Direct protein target assigned |
| H | Homologous protein target assigned |
| M | Molecular target other than protein assigned |

## Table: site_components
Columns:
- sitecomp_id BIGINT NOT NULL PK
- site_id BIGINT NOT NULL
- component_id BIGINT NULL
- domain_id BIGINT NULL
- site_residues VARCHAR(2000) NULL

Sample rows:
| sitecomp_id | site_id | component_id | domain_id | site_residues |
|---|---|---|---|---|
| 2 | 1504 | 4968 | 2748 | NULL |
| 3 | 1505 | 4800 | 2951 | NULL |
| 4 | 2 | 4909 | 2781 | NULL |

## Table: source
Columns:
- src_id INTEGER NOT NULL PK
- src_description VARCHAR(500) NULL
- src_short_name VARCHAR(20) NULL
- src_comment VARCHAR(1200) NULL
- src_url VARCHAR(200) NULL
- ddid_pattern VARCHAR(2000) NULL

Sample rows:
| src_id | src_description | src_short_name | src_comment | src_url | ddid_pattern |
|---|---|---|---|---|---|
| 0 | Undefined | UNDEFINED | NULL | NULL | NULL |
| 1 | Scientific Literature | LITERATURE | The medicinal chemistry literature provides a valuable source of bioactivity ... | NULL | NULL |
| 2 | GSK Malaria Screening | GSK_TCMDC | Bioactivity data for a published subset of GlaxoSmithKlines compound library ... | NULL | NULL |

## Table: structural_alert_sets
Columns:
- alert_set_id BIGINT NOT NULL PK
- set_name VARCHAR(100) NOT NULL
- priority SMALLINT NOT NULL

Sample rows:
| alert_set_id | set_name | priority |
|---|---|---|
| 1 | Glaxo | 8 |
| 2 | Dundee | 4 |
| 3 | BMS | 7 |

## Table: structural_alerts
Columns:
- alert_id BIGINT NOT NULL PK
- alert_set_id BIGINT NOT NULL
- alert_name VARCHAR(100) NOT NULL
- smarts VARCHAR(4000) NOT NULL

Sample rows:
| alert_id | alert_set_id | alert_name | smarts |
|---|---|---|---|
| 1 | 1 | R1 Reactive alkyl halides | [Br,Cl,I][CX4;CH,CH2] |
| 2 | 1 | R2 Acid halides | [S,C](=[O,S])[F,Br,Cl,I] |
| 3 | 1 | R3 Carbazides | O=CN=[N+]=[N-] |

## Table: target_components
Columns:
- tid BIGINT NOT NULL
- component_id BIGINT NOT NULL
- targcomp_id BIGINT NOT NULL PK
- homologue SMALLINT NOT NULL

Sample rows:
| tid | component_id | targcomp_id | homologue |
|---|---|---|---|
| 11004 | 3090 | 1 | 0 |
| 11028 | 1166 | 4 | 0 |
| 11037 | 1888 | 5 | 0 |

## Table: target_dictionary
Columns:
- tid BIGINT NOT NULL PK
- target_type VARCHAR(30) NULL
- pref_name VARCHAR(200) NOT NULL
- tax_id BIGINT NULL
- organism VARCHAR(150) NULL
- chembl_id VARCHAR(20) NOT NULL
- species_group_flag SMALLINT NOT NULL

Sample rows:
| tid | target_type | pref_name | tax_id | organism | chembl_id | species_group_flag |
|---|---|---|---|---|---|---|
| 1 | SINGLE PROTEIN | Maltase-glucoamylase | 9606 | Homo sapiens | CHEMBL2074 | 0 |
| 2 | SINGLE PROTEIN | ATP-binding cassette sub-family C member 9 | 9606 | Homo sapiens | CHEMBL1971 | 0 |
| 3 | SINGLE PROTEIN | cGMP-specific 3',5'-cyclic phosphodiesterase | 9606 | Homo sapiens | CHEMBL1827 | 0 |

## Table: target_relations
Columns:
- tid BIGINT NOT NULL
- relationship VARCHAR(20) NOT NULL
- related_tid BIGINT NOT NULL
- targrel_id BIGINT NOT NULL PK

Sample rows:
| tid | relationship | related_tid | targrel_id |
|---|---|---|---|
| 11699 | SUBSET OF | 104812 | 618116 |
| 12261 | SUBSET OF | 104822 | 618117 |
| 12261 | SUBSET OF | 118329 | 618118 |

## Table: target_type
Columns:
- target_type VARCHAR(30) NOT NULL PK
- target_desc VARCHAR(250) NULL
- parent_type VARCHAR(25) NULL

Sample rows:
| target_type | target_desc | parent_type |
|---|---|---|
| 3D CELL CULTURE | Target is a 3D cell culture model such as an organoid, sphereoid or tumoroid ... | NON-MOLECULAR |
| ADMET | Target is not applicable for an ADMET assay (e.g., physchem property) | UNDEFINED |
| CELL-LINE | Target is a specific cell-line | NON-MOLECULAR |

## Table: tissue_dictionary
Columns:
- tissue_id BIGINT NOT NULL PK
- uberon_id VARCHAR(15) NULL
- pref_name VARCHAR(200) NOT NULL
- efo_id VARCHAR(20) NULL
- chembl_id VARCHAR(20) NOT NULL
- bto_id VARCHAR(20) NULL
- caloha_id VARCHAR(7) NULL

Sample rows:
| tissue_id | uberon_id | pref_name | efo_id | chembl_id | bto_id | caloha_id |
|---|---|---|---|---|---|---|
| 2 | UBERON:0000002 | Uterine cervix | EFO:0000979 | CHEMBL3988026 | BTO:0001421 | TS-0134 |
| 4 | UBERON:0000004 | Nose | NULL | CHEMBL3987869 | BTO:0000840 | TS-2037 |
| 6 | UBERON:0000006 | Islets of langerhans | EFO:0000856 | CHEMBL4296343 | BTO:0000991 | TS-0741 |

## Table: usan_stems
Columns:
- usan_stem_id BIGINT NOT NULL PK
- stem VARCHAR(100) NOT NULL
- subgroup VARCHAR(100) NULL
- annotation VARCHAR(2000) NULL
- stem_class VARCHAR(100) NULL

Sample rows:
| usan_stem_id | stem | subgroup | annotation | stem_class |
|---|---|---|---|---|
| 4141 | -ac | NULL | anti-inflammatory agents (acetic acid derivatives) | suffix |
| 4142 | -ac | -zolac | anti-inflammatory agents (acetic acid derivatives): anti-inflammatory; pyrazo... | suffix |
| 4143 | -actant | NULL | pulmonary surfactants | suffix |

## Table: variant_sequences
Columns:
- variant_id BIGINT NOT NULL PK
- mutation VARCHAR(2000) NULL
- accession VARCHAR(25) NULL
- version BIGINT NULL
- isoform BIGINT NULL
- sequence TEXT NULL
- organism VARCHAR(200) NULL
- tax_id BIGINT NULL

Sample rows:
| variant_id | mutation | accession | version | isoform | sequence | organism | tax_id |
|---|---|---|---|---|---|---|---|
| -1 | UNDEFINED MUTATION | NULL | NULL | NULL | NULL | NULL | NULL |
| 100 | M197L | Q2HRB6 | 1 | NULL | MAQGLYVGGFVDVVSCPKLEQELYLDPDQVTDYLPVTEPLPITIEHLPETEVGWTLGLFQVSHGIFCTGAITSPAFL... | Human herpesvirus 8 | 868565 |
| 101 | R374A | Q9UM07 | 2 | NULL | MAQGTLIRVTPEQPTHAVCVLGTLTQLDICSSAPEDCTSFSINASPGVVVDIAHGPPAKKKSTGSSTWPLDPGVEVT... | Homo sapiens | 9606 |

## Table: version
Columns:
- name VARCHAR(50) NOT NULL PK
- creation_date DATETIME NULL
- comments VARCHAR(2000) NULL

Sample rows:
| name | creation_date | comments |
|---|---|---|
| Bioassay Ontology 2.0 | NULL | BAO version used for assays (http://bioassayontology.org/) |
| COCONUT 2025-07 | NULL | COCONUT version used for natural product flagging (https://coconut.naturalpro... |
| ChEMBL_36 | 2025-07-28 00:00:00.000000 | ChEMBL Release 36 (https://www.ebi.ac.uk/chembl) |

## Table: warning_refs
Columns:
- warnref_id BIGINT NOT NULL PK
- warning_id BIGINT NULL
- ref_type VARCHAR(50) NULL
- ref_id VARCHAR(4000) NULL
- ref_url VARCHAR(4000) NULL

Sample rows:
| warnref_id | warning_id | ref_type | ref_id | ref_url |
|---|---|---|---|---|
| 11 | 1 | DailyMed | de109a2b-e36c-40d0-85fc-a67a9e7f1ae8 | https://dailymed.nlm.nih.gov/dailymed/drugInfo.cfm?setid=de109a2b-e36c-40d0-8... |
| 20 | 2 | DailyMed | de109a2b-e36c-40d0-85fc-a67a9e7f1ae8 | https://dailymed.nlm.nih.gov/dailymed/drugInfo.cfm?setid=de109a2b-e36c-40d0-8... |
| 35 | 3 | DailyMed | de109a2b-e36c-40d0-85fc-a67a9e7f1ae8 | https://dailymed.nlm.nih.gov/dailymed/drugInfo.cfm?setid=de109a2b-e36c-40d0-8... |
