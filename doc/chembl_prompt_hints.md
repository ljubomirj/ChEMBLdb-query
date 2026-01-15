# ChEMBL prompt hints (auto-generated)
Database: database/latest/chembl_36/chembl_36_sqlite/chembl_36.db

This file includes full contents of small lookup tables for prompt context.

## Table: assay_type
Row count: 6
Columns:
- assay_type VARCHAR(1)
- assay_desc VARCHAR(250)

Full contents:
| assay_type | assay_desc |
| --- | --- |
| A | ADME |
| B | Binding |
| F | Functional |
| P | Physicochemical |
| T | Toxicity |
| U | Unassigned |

## Table: confidence_score_lookup
Row count: 10
Columns:
- confidence_score SMALLINT
- description VARCHAR(100)
- target_mapping VARCHAR(30)

Full contents:
| confidence_score | description | target_mapping |
| --- | --- | --- |
| 0 | Default value - Target unknown or has yet to be assigned | Unassigned |
| 1 | Target assigned is non-molecular | Non-molecular |
| 2 | Target assigned is subcellular fraction | Subcellular fraction |
| 3 | Target assigned is molecular non-protein target | Molecular (non-protein) |
| 4 | Multiple homologous protein targets may be assigned | Multiple homologous proteins |
| 5 | Multiple direct protein targets may be assigned | Multiple proteins |
| 6 | Homologous protein complex subunits assigned | Homologous protein complex |
| 7 | Direct protein complex subunits assigned | Protein complex |
| 8 | Homologous single protein target assigned | Homologous protein |
| 9 | Direct single protein target assigned | Protein |

## Table: data_validity_lookup
Row count: 7
Columns:
- data_validity_comment VARCHAR(30)
- description VARCHAR(200)

Full contents:
| data_validity_comment | description |
| --- | --- |
| Author confirmed error | Error in publication - Author confirmed (personal communication) |
| Manually validated | Data have been checked against the publication and are believed to be accurate |
| Non standard unit for type | Units for this activity type are unusual and may be incorrect (or the standard_type may be incorrect) |
| Outside typical range | Values for this activity type are unusually large/small, so may not be accurate |
| Potential author error | Data have been checked against the publication and are as reported - possibly an error was made by the author |
| Potential missing data | No data provided for value, units or activity_comment, needs further investigation |
| Potential transcription error | Values appear to be an order of magnitude different from previously reported, so units may be incorrect |

## Table: relationship_type
Row count: 6
Columns:
- relationship_type VARCHAR(1)
- relationship_desc VARCHAR(250)

Full contents:
| relationship_type | relationship_desc |
| --- | --- |
| D | Direct protein target assigned |
| H | Homologous protein target assigned |
| M | Molecular target other than protein assigned |
| N | Non-molecular target assigned |
| S | Subcellular target assigned |
| U | Default value - Target has yet to be curated |

## Table: target_type
Row count: 28
Columns:
- target_type VARCHAR(30)
- target_desc VARCHAR(250)
- parent_type VARCHAR(25)

Full contents:
| target_type | target_desc | parent_type |
| --- | --- | --- |
| 3D CELL CULTURE | Target is a 3D cell culture model such as an organoid, sphereoid or tumoroid that mimics tissues or organs | NON-MOLECULAR |
| ADMET | Target is not applicable for an ADMET assay (e.g., physchem property) | UNDEFINED |
| CELL-LINE | Target is a specific cell-line | NON-MOLECULAR |
| CHIMERIC PROTEIN | Target is a fusion of two different proteins, either a synthetic construct or naturally occurring fusion protein | PROTEIN |
| LIPID | Target is a lipid | MOLECULAR |
| MACROMOLECULE | Target is a biological macromolecule (e.g., glycoproteins, hemozoin, hydroxyapatite) | MOLECULAR |
| METAL | Target is a metal e.g., iron | MOLECULAR |
| MOLECULAR | Target has been identified as a defined molecular entity (e.g., protein or nucleic acid) | NULL |
| NO TARGET | Target is not applicable for a screening assay (e.g., negative control/counterscreen) | UNDEFINED |
| NON-MOLECULAR | Target has not been defined at a molecular level, only the non-molecular entity which is affected (e.g., organism, cell line etc) | NULL |
| NUCLEIC-ACID | Target is DNA, RNA or PNA | MOLECULAR |
| OLIGOSACCHARIDE | Target is an oligosaccharide (e.g., heparin, starch) | MOLECULAR |
| ORGANISM | Target is a complete organism | NON-MOLECULAR |
| PHENOTYPE | Target is a biological phenotype or process | NON-MOLECULAR |
| PROTEIN | Target is a protein or group of proteins | MOLECULAR |
| PROTEIN COMPLEX | Target is a defined protein complex, consisting of multiple subunits | PROTEIN |
| PROTEIN COMPLEX GROUP | Target is a poorly defined protein complex, where subunit composition is unclear (e.g., GABA-A receptor) | PROTEIN |
| PROTEIN FAMILY | Target is a group of closely related proteins | PROTEIN |
| PROTEIN NUCLEIC-ACID COMPLEX | Target is a complex consisting of both protein and nucleic-acid components (e.g., ribosome) | MOLECULAR |
| PROTEIN-PROTEIN INTERACTION | Target is the disruption of a protein-protein interaction | PROTEIN |
| SELECTIVITY GROUP | Target is a pair of proteins for which the selectivity has been assessed | PROTEIN |
| SINGLE PROTEIN | Target is a single protein chain | PROTEIN |
| SMALL MOLECULE | Target is a small molecule such as an amino acid, sugar or metabolite) | MOLECULAR |
| SUBCELLULAR | Target is a subcellular fraction | NON-MOLECULAR |
| TISSUE | Target is a healthy or diseased tissue | NON-MOLECULAR |
| UNCHECKED | Target has not yet been assigned | UNDEFINED |
| UNDEFINED | No target has been defined | NULL |
| UNKNOWN | Molecular identity of target is unknown (e.g., pharmacologically defined target) | UNDEFINED |

## Table: action_type
Row count: 35
Columns:
- action_type VARCHAR(50)
- description VARCHAR(200)
- parent_type VARCHAR(50)

Full contents:
| action_type | description | parent_type |
| --- | --- | --- |
| ACTIVATOR | Positively effects the normal functioning of the protein e.g., activation of an enzyme or cleaving a clotting protein precursor | POSITIVE MODULATOR |
| AGONIST | Binds to and activates a receptor, often mimicking the effect of the endogenous ligand | POSITIVE MODULATOR |
| ALLOSTERIC ANTAGONIST | Binds to a receptor at an allosteric site and prevents activation by a positive allosteric modulator at that site | NEGATIVE MODULATOR |
| ANTAGONIST | Binds to a receptor and prevents activation by an agonist through competing for the binding site | NEGATIVE MODULATOR |
| ANTISENSE INHIBITOR | Prevents translation of a complementary mRNA sequence through binding and targeting it for degradation | NEGATIVE MODULATOR |
| BINDING AGENT | Binds to a substance such as a cell surface antigen, targeting a drug to that location, but not necessarily affecting the functioning of the substance itself | OTHER |
| BLOCKER | Negatively effects the normal functioning of an ion channel e.g., prevents or reduces transport of ions through the channel | NEGATIVE MODULATOR |
| CHELATING AGENT | Binds to a metal, reducing its availability for further interactions | OTHER |
| CROSS-LINKING AGENT | Induces cross-linking of proteins or nucleic acids | OTHER |
| DEGRADER | Binds to or antagonizes a receptor, leading to its degradation | NEGATIVE MODULATOR |
| DISRUPTING AGENT | Destabilises or disrupts a protein complex, macromolecular assembly, cell membrane etc | OTHER |
| EXOGENOUS GENE | Nucleic acid from an exogenous source acts as a substitute or supplement for a specific gene which is absent or has reduced function in affected patients | POSITIVE MODULATOR |
| EXOGENOUS PROTEIN | Protein from an exogenous source acts as a substitute or supplement for a specific protein which is absent or has reduced function in affected patients | POSITIVE MODULATOR |
| GENE EDITING NEGATIVE MODULATOR | Gene editing technology is used to modify a relevant DNA sequence to negatively effect the function of the target | NEGATIVE MODULATOR |
| HYDROLYTIC ENZYME | Hydrolyses a substrate through enzymatic reaction | OTHER |
| INHIBITOR | Negatively effects (inhibits) the normal functioning of the protein e.g., prevention of enzymatic reaction or activation of downstream pathway | NEGATIVE MODULATOR |
| INVERSE AGONIST | Binds to and inactivates a receptor | NEGATIVE MODULATOR |
| METHYLATING AGENT | Methylates or participates in methylation (e.g., through donation of a methyl group) of a substrate molecule | OTHER |
| MODULATOR | Effects the normal functioning of a protein in some way e.g., mixed agonist/antagonist or unclear whether action is positive or negative | OTHER |
| NEGATIVE ALLOSTERIC MODULATOR | Reduces or prevents the action of the endogenous ligand of a receptor through binding to a site distinct from that ligand (non-competitive inhibition) | NEGATIVE MODULATOR |
| NEGATIVE MODULATOR | Negatively effects the normal functioning of a protein e.g., receptor antagonist, inverse agonist or negative allosteric modulator | NEGATIVE MODULATOR |
| OPENER | Positively effects the normal functioning of an ion channel e.g., facilitates transport of ions through the channel | POSITIVE MODULATOR |
| OTHER | Other action type, not clearly positively or negatively affecting the normal functioning of a protein e.g., chelation of substances, hydrolysis of substrate | OTHER |
| OXIDATIVE ENZYME | Oxidises a substrate through enzymatic reaction | OTHER |
| PARTIAL AGONIST | Binds to and only partially activates a receptor (relative to the response to a full agonist) | POSITIVE MODULATOR |
| POSITIVE ALLOSTERIC MODULATOR | Enhances the action of the endogenous ligand of a receptor through binding to a site distinct from that ligand | POSITIVE MODULATOR |
| POSITIVE MODULATOR | Positively effects the normal functioning of a protein e.g., receptor agonist, positive allosteric modulator, ion channel activator | POSITIVE MODULATOR |
| PROTEOLYTIC ENZYME | Hydrolyses a protein substrate through enzymatic reaction | OTHER |
| REDUCING AGENT | Modifies a substrate via a reduction reaction | OTHER |
| RELEASING AGENT | Reverses the normal functioning of a transporter, causing release of the substrate, rather than uptake | NEGATIVE MODULATOR |
| RNAI INHIBITOR | Prevents translation of mRNA through binding and targeting it for destruction (e.g., siRNA) | NEGATIVE MODULATOR |
| SEQUESTERING AGENT | Binds to a substance such as a drug, toxin or metabolite reducing its availability for further interactions | OTHER |
| STABILISER | Increases the conformational stability of a protein or complex | OTHER |
| SUBSTRATE | Carried by a transporter, possibly competing with the natural substrate for transport | OTHER |
| VACCINE ANTIGEN | Delivers an antigen and promotes an immune response against the antigen e.g. activating the immune system towards cancer-specific biomarkers | OTHER |

## Table: curation_lookup
Row count: 3
Columns:
- curated_by VARCHAR(32)
- description VARCHAR(100)

Full contents:
| curated_by | description |
| --- | --- |
| Autocuration | Curated against extractor target assignment |
| Expert | Curated against ChEMBL target assignment from original publication |
| Intermediate | Curated against ChEMBL target assignment from assay description |

## Table: source
Row count: 67
Columns:
- src_id INTEGER
- src_description VARCHAR(500)
- src_short_name VARCHAR(20)
- src_comment VARCHAR(1200)
- src_url VARCHAR(200)
- ddid_pattern VARCHAR(2000)

Full contents:
| src_id | src_description | src_short_name | src_comment | src_url | ddid_pattern |
| --- | --- | --- | --- | --- | --- |
| 0 | Undefined | UNDEFINED | NULL | NULL | NULL |
| 1 | Scientific Literature | LITERATURE | The medicinal chemistry literature provides a valuable source of bioactivity data for drug like compounds. Bioactivity data is routinely extracted from our seven core MedChem journals (Bioorg Med Chem Lett, J Med Chem, Bioorg Med Chem, J Nat Prod, Eur J Med Chem, ACS Med Chem Lett, MedChemComm) but also includes selected publications from additional journals. | NULL | NULL |
| 2 | GSK Malaria Screening | GSK_TCMDC | Bioactivity data for a published subset of GlaxoSmithKlines compound library (the Tres Cantos antimalarial compound set (TCAMS)) screened against P. falciparum. | NULL | NULL |
| 3 | Novartis Malaria Screening | NOVARTIS | Bioactivity data for a published subset of the Novartis GNF library that was screened against P. falciparum. | NULL | NULL |
| 4 | St. Jude Children’s Research Hospital Malaria Screening | ST_JUDE | Bioactivity data for a published subset of compounds from a multi-organisation antimalarial study (including St. Jude Children’s Research Hospital) screened against P. falciparum. | NULL | NULL |
| 5 | Sanger Institute Genomics of Drug Sensitivity in Cancer | SANGER | The Sanger Institute, Genomics of Drug Sensitivity in Cancer project aims to identify molecular features of cancers that predict response to anti-cancer drugs. | https://www.cancerrxgene.org | NULL |
| 6 | PDBe Ligands (DEPRECATED) | PDBE | DEPRECATED | https://www.ebi.ac.uk/pdbe/ | NULL |
| 7 | PubChem BioAssays | PUBCHEM_BIOASSAY | PubChem is a chemistry database at the National Institutes of Health (NIH). A subset of PubChem assays were included in ChEMBL (confirmatory and panel assays with dose–response endpoints) as well as a number of assays, chosen individually, on the basis that they have been specifically requested to be included by ChEMBL users | https://pubchem.ncbi.nlm.nih.gov | NULL |
| 8 | Clinical Candidate Compounds | CANDIDATES | Drugs that are progressing through the phases of clinical development - clinical candidate drugs. Data are predominantly extracted from ClinicalTrials.gov via our Clinical Trials Pipeline, with a small number of manually curated clinical candidates.  | https://www.clinicaltrials.gov/ | NULL |
| 9 | FDA Orange Book Drugs | FDA_ORANGE_BOOK | FDA Orange Book database of Approved Drug Products with Therapeutic Equivalence Evaluations. | https://www.fda.gov/drugs/drug-approvals-and-databases/approved-drug-products-therapeutic-equivalence-evaluations-orange-book | NULL |
| 10 | Guide to Receptors and Channels (DEPRECATED) | GRAC | DEPRECATED | NULL | NULL |
| 11 | Open TG-GATEs | TG_GATES | Open Toxicogenomics Project-Genomics Assisted Toxicity Evaluation Systems (TG-GATEs) is a toxicogenomics database (http://togodb.dbcls.jp/open_tggates_main). A subset of the biochemistry, in vivo and pathology measurements have been included in ChEMBL. For more information see http://toxico.nibio.go.jp/open-tggates/search.html and Mol. Nutr. Food. Res. (2010), 54(2), 218-27. | http://togodb.dbcls.jp/open_tggates_main | NULL |
| 12 | FDA Novel Drugs and Biotherapeutics | FDA_NEW_DRUGS | FDA Novel Drug Therapy Approvals and FDA Biological License Application Approvals | https://www.fda.gov/drugs/development-approval-process-drugs/novel-drug-approvals-fda;  https://www.fda.gov/vaccines-blood-biologics/development-approval-process-cber/biological-approvals-year | NULL |
| 13 | United States Adopted Names (USAN) | USAN | The United States Adopted Names (USAN) Council selects simple, informative and unique nonproprietary (generic) drug names. The USAN Council establishes logical nomenclature classifications based on pharmacological and/or chemical relationships. In addition to one member-at-large and a Food and Drug Administration (FDA) liaison, the council consists of one representative from each of the following: The American Medical Association (AMA), United States Pharmacopeia (USP) and the American Pharmacists Association (APhA). | https://www.ama-assn.org/about/united-states-adopted-names | NULL |
| 14 | Drugs for Neglected Diseases Initiative (DNDi) | DNDI | Drugs for Neglected Diseases Initiative (DNDi) is a research organization developing new treatments for neglected patients. Deposited datasets from this initiative were provided. | https://dndi.org | NULL |
| 15 | DrugMatrix | DRUGMATRIX | The DrugMatrix in vitro pharmacology assays data set comprises approximately 870 therapeutic, industrial, and environmental chemicals screened against protein targets, cellular and in vivo assays at non-toxic and/or toxic doses. The DrugMatrix molecular toxicology reference database and informatics system, freely available from the US National Toxicology Program, is populated with the comprehensive results of thousands of highly controlled and standardized toxicological experiments. Following administration of these compounds in vivo, comprehensive studies of the effects of these compounds were carried out at multiple time points and in multiple target organs. The data is associated with document CHEMBL_IDs: CHEMBL2924216 (Biochemistry), CHEMBL2924217 (Hematology) and CHEMBL2924218 (Pathology). | https://cebs.niehs.nih.gov/cebs/paper/15670 | NULL |
| 16 | GSK Published Kinase Inhibitor Set | GSK_PKIS | Bioactivity data associated with GSK Published Kinase Inhibitor Sets (GSK PKI). | NULL | NULL |
| 17 | Medicines for Malaria Venture (MMV) Malaria Box | MMV_MBOX | Bioactivity data associated with Screening of the MMV malaria box, a free library of 400 diverse compounds with antimalarial activity (http://www.mmv.org/malariabox). | http://www.mmv.org/malariabox | NULL |
| 18 | TP-search Transporter Database | TP_TRANSPORTER | Transporter-specific information contained in the TP-search database. | NULL | NULL |
| 19 | Harvard University Malaria Screening | HARVARD | Harvard Malaria Screening Data for liver-stage malaria from Proc. Natl. Acad. Sci. (2012), 109(22), 8511. | NULL | NULL |
| 20 | WHO Tropical Disease Research (TDR) Malaria Screening | WHO_TDR | WHO-TDR Malaria Screening Data. Supplementary malaria screening information for PLoS Negl. Trop. Dis. (2011), 5(12), e1412. | NULL | NULL |
| 21 | Deposited Supplementary Bioactivity Data | SUPPLEMENTARY | Deposited supplementary data for publications | NULL | NULL |
| 22 | GSK Tuberculosis Screening | GSK_TB | Large scale anti-TB screening campaigns from GSK, including a GSK Tres Cantos TB TCAMS dataset.   | NULL | NULL |
| 23 | Open Source Malaria Screening | OSM | Screening of compounds synthesised and sourced by the OSDD Malaria consortium against Plasmodium falciparum, and measurements of cytotoxicity. | https://malaria.ourexperiment.org | NULL |
| 24 | Millipore Kinase Screening (DEPRECATED - MERGED WITH SRC_ID = 1) | MILLIPORE | DEPRECATED - MERGED WITH SRC_ID = 1 | NULL | NULL |
| 25 | External Project Compounds | EXT. PROJECT CPDS | NULL | NULL | NULL |
| 26 | Gene Expression Atlas Compounds (EMBL-EBI) | ATLAS | NULL | https://www.ebi.ac.uk/gxa/home | NULL |
| 27 | AstraZeneca DMPK/physicochemical | ASTRAZENECA | Experimental in vitro DMPK and physicochemical data determined at AstraZeneca on a set of publicly disclosed compounds in the following assays: pKa, lipophilicity (LogD7.4), aqueous solubility, plasma protein binding (human, rat, dog , mouse and guinea pig), intrinsic clearance (human liver microsomes, human and rat hepatocytes). | NULL | NULL |
| 28 | FDA approval pharmacokinetics/metabolism  | FDA_APPROVAL | Selected drug metabolism and pharmacokinetic data from FDA Drug Approval Packages, manually extracted from Drug Approval Reviews available from Drugs@FDA | https://www.accessdata.fda.gov/scripts/cder/daf/index.cfm | NULL |
| 29 | GSK Kinetoplastid Screening | GSK_TCAKS | GSK Tres Cantos Anti-Kinetoplastid Screening (TCAKS) Data. Using whole-cell phenotypic assays, the GSK screening collection of 1.8 million compounds was screened against the three kinetoplastids most relevant to human disease, i.e. Leishmania donovani, Trypanosoma cruzi and Trypanosoma brucei. Secondary confirmatory and orthogonal intracellular parasiticidal assays were conducted, and the potential for non-specific cytotoxicity determined with HepG2 assay. Hit compounds were chemically clustered and triaged for desirable physicochemical properties. Consequently, three anti-kinetoplastid chemical boxes of 222 compounds for Chagas-Box, 192 compounds for Leish-Box and 192 compounds for HAT-Box were assembled. The compound sets are provided as an open resource for future lead discovery programs, as well as to address important research questions. [10.1038/srep08771]. | NULL | NULL |
| 30 | Kinetics for Drug Discovery (K4DD) | K4DD | The K4DD (Kinetics for Drug Discovery) project (started in 2012) is supported by the Innovative Medicines Initiative Joint Undertaking (IMI JU), resources of which are composed of a financial contribution from the European Unions Seventh Framework Programme (FP7/2007-2013) and EFPIA companies in kind contribution. Its goal is to enable the adoption of drug-target binding kinetics analysis in the drug discovery decision-making process, and thereby contribute to the development of a new generation of improved medicinal products. This data set contains drug-target binding kinetics measured for several hundred compounds using different methods such as SPR, radioligand binding and KPCA and is is provided as an open resource for future research. | https://www.ihi.europa.eu/projects-results/project-factsheets/k4dd | NULL |
| 31 | Curated Drug Metabolism Pathways | METABOLISM | Manually curated Drug Metabolism Pathways from a variety of literature/reference sources. | NULL | NULL |
| 32 | St. Jude Children’s Research Hospital Leishmania Screening | ST_JUDE_LEISH | The data deposited were derived from a screen of the TCAMS and Malaria Box libraries for compounds that selectively inhibit the Plasmodium falciparum hexose transporter, PfHT, versus the human glucose transporter GLUT1. Both PfHT and GLUT1 were expressed heterologously in a glucose transporter null mutant of the protozoan Leishmania mexicana (Δlmxgt1-3 null mutant). When grown in the appropriate medium, these transgenic Leishmania reporter strains depend upon uptake of glucose for growth, and thus compounds that inhibit the heterologously expressed hexose transporters will prevent growth of the reporter strain. One set of data reports the growth inhibition effect of each compound in the TCAMS library (13,243 compounds), at 2 uM concentration, against Δlmxgt1-3 parasites expressing PfHT, GLUT1, or the L. mexicana glucose transporter LmxGT2. The second set of data report the dose-response data for 392 selected TCAMS compounds against strains expressing each of the 3 heterologously expressed hexose transporters. The third set of data reports dose-response data for all 400 compounds of the Malaria Box library against the same 3 reporter strains. | NULL | NULL |
| 33 | Gates Foundation Compound Collection | GATES_LIBRARY | The Gates Foundation have funded the development of a screening collection of approximately 70,000 novel natural product fragments for neglected disease drug discovery at the University of Dundee. | NULL | NULL |
| 34 | Medicines for Malaria Venture (MMV) Pathogen Box | MMV_PBOX | Bioactivity data associated with Screening of the MMV pathogen box, a free library of 400 diverse, drug-like molecules active against neglected diseases of interest. Upon request, researchers around the world will receive a Pathogen Box of molecules to help catalyse neglected disease drug discovery. In return, researchers are asked to share any data generated in the public domain within 2 years, creating an open and collaborative forum for neglected diseases drug research. | https://www.mmv.org/mmv-open/pathogen-box/about-pathogen-box | NULL |
| 35 | Hepatic and Cardiac Toxicity Systems modelling (HeCaToS) Compounds | HECATOS | Initial list of compounds used in the HeCaToS EU FP7 project, which were classified as hepatotoxic, cardiotoxic or non-toxic. Parent compounds, respective salts and radiolabelled versions of the compounds are included. | https://cordis.europa.eu/project/id/602156/reporting; https://doi.org/10.1038/s41597-022-01825-1 | NULL |
| 36 | Withdrawn Drugs | WITHDRAWN | Withdrawn drugs are manually curated from information provided by national regulatory bodies and the scientific literature.  | NULL | NULL |
| 37 | BindingDB Patent Bioactivity Data | BINDINGDB | We have worked with the BindingDB team to integrate the bioactivity data that they have extracted from more than 1000 granted US patents published from 2013 onwards (https://www.bindingdb.org/bind/ByPatent.jsp) into ChEMBL. | https://www.bindingdb.org/rwd/bind/index.jsp | NULL |
| 38 | SureChEMBL Patent Bioactivity Data | PATENT | We have extracted bioactivity data from patents in SureChEMBL for a number of targets that are of interest to the NIH-funded Illuminating the Druggable Genome project. These are mainly targets that had little/no literature bioactivity data previously in ChEMBL but are members of druggable protein families. | NULL | NULL |
| 39 | Curated Drug Pharmacokinetic Data | DRUG_PK | Curated Drug Pharmacokinetic Data. Manually extracted pharmacokinetic parameters for approved drugs from DailyMed drug labels. | NULL | NULL |
| 40 | CO-ADD Antimicrobial Screening | COADD | CO-ADD, The Community for Open Antimicrobial Drug Discovery (http://www.co-add.org), is a global open-access screening initiative launched in February 2015 to uncover significant and rich chemical diversity held outside of corporate screening collections. CO-ADD provides unencumbered free antimicrobial screening for any interested academic researcher. CO-ADD has been recognised as a novel approach in the fight against superbugs by the Wellcome Trust, who have provided funding through their Strategic Awards initiative. | http://www.co-add.org | NULL |
| 41 | WHO Anatomical Therapeutic Chemical (ATC) Classification of Drugs | ATC | The World Health Organisation (WHO) endorsed the Anatomical Therapeutic Chemical Classification (ATC) and Defined Daily Dose (DDD) methodology for global use in 1996 as the gold standard for drug utilisation monitoring and research. The ATC classification has been adopted in various countries as a national standard for classification of medicinal products. The ATC classification system groups the active ingredients according to the organ or system on which they act and according to their therapeutic, pharmacologic and chemical properties.  | https://atcddd.fhi.no/atc_ddd_index; https://www.who.int/tools/atc-ddd-toolkit | NULL |
| 42 | British National Formulary (BNF) | BNF | The British National Formulary (BNF) contains information on the selection, prescribing, dispensing and administration of UK medicines. BNF data for medicine names and chemical structures (usually shown as the parent drug form) was extracted between 2017 (ChEMBL 23) and 2019 (ChEMBL 26). | https://bnf.nice.org.uk/ | NULL |
| 43 | GSK Published Kinase Inhibitor Set 2 | PKIS2 | The GKS PKIS2 collection of 490 compounds were tested against Onchocerca lienalis microfilariae in a 96-well format. The assay is described in Townson et al. (2007) Challenges in drug discovery for novel antifilarials, Expert Opinion on Drug Discovery, 2, S63-S73 | NULL | NULL |
| 48 | Kuster Lab Chemical Proteomics Drug Profiling | TUM_PROTEOMIC_KUSTER | Data have been included from the publication: The target landscape of clinical kinase drugs. Klaeger S, Heinzlmeir S and Wilhelm M et al (2017), Science, 358-6367 (DOI: 10.1126/science.aan4368) | NULL | NULL |
| 49 | HESI Cardiac Safety Committee Myocyte Subteam dataset | HESI | Health and Environmental Sciences Institute (HESI) Cardiac Safety Committee Myocyte Subteam dataset with stem cell-derived cardiomyocytes (PSC-CMs) to evaluate use in an in vitro proarrhythmia model. Data includes electrophysiologic responses to 28 drugs linked to low, intermediate, and high torsades de pointes (TdP) risk categories using multiple cell lines and standardized protocols. | NULL | NULL |
| 51 | Winzeler Lab Plasmodium Screening | WINZ_PLASMO | A Neglected Tropical Didease initiative from the Winzeler lab at the University of California, San Diego, and the Medicines for Malaria Venture. | NULL | NULL |
| 52 | SARS-CoV-2 Screening Data | SARS_COV_2 | After the onset of the SARS-COV-2 pandemic in 2020, screening datasets against the viral target became available. Data was incorporated into ChEMBL from eight drug repurposing papers, testing the efficacy of approved drugs, clinical candidates and other selected compounds against SARS-CoV-2 infection/replication in cell-based assays. Many of these data sets had not been peer-reviewed at the time of submission, and may therefore be subject to change in future releases. | NULL | NULL |
| 53 | Active Ingredient of a Prodrug | PRODRUG_ACTIVE | The pharmacologically active ingredient of a prodrug is manually curated from approved drug labels and the scientific literature. | NULL | NULL |
| 54 | SGC Frankfurt - Donated Chemical Probes | DONATED_PROBES | The Structural Genomics Consortium supports open-access research in drug discovery. The SGC Donated Chemical Probes project is a collaboration between pharmaceutical companies and academics with the goal to make chemical probes readily available through the SGC. Chemical probes are validated small molecules acting specifically at their targets; they are associated with high quality data and meet defined criteria. Control compounds are also provided and profiled.  | https://www.sgc-ffm.uni-frankfurt.de/#!donateview | NULL |
| 55 | EUbOPEN Chemogenomic Library | EUBOPEN_CGL | The EUbOPEN consortium is an Innovative Medicines Initiative (IMI) funded project to enable and unlock biology in the open. The aims of the project are to assemble an open access chemogenomic library comprising about 5,000 well annotated compounds covering roughly 1,000 different proteins, to synthesize at least 100 high-quality, open-access chemical probes and to develop infrastructure, technologies and platforms. Screening data generated during this 5 year project will be deposited in ChEMBL. | https://www.eubopen.org | NULL |
| 56 | London School of Hygiene and Tropical Medicine and Salvensis Schistosomiasis screening | SALVENSIS_LSHTM | High-throughput screening of compounds against both juvenile and adult S. mansoni worms in a mouse model of infection, in collaboration between Salvensis and the London School of Hygiene and Tropical Medicine. | NULL | NULL |
| 57 | IMI-CARE SARS-CoV-2 Data | CARE | Corona Accelerated R&D in Europe) is the largest European research initiative addressing the challenges of COVID-19. With a coalition of Europe’s best scientific minds from 37 globally-renowned research institutions and pharmaceutical companies, together with partners from the USA and China it provides a multi-disciplinary team with proven expertise and capabilities in anti-viral drug development. | https://www.imi-care.eu | NULL |
| 58 | Research Empowerment on Solute Carriers (RESOLUTE) | RESOLUTE | RESOLUTE  (Research Empowerment on Solute Carriers; https://re-solute.eu/) is an eu finded consortium woking on the solute carrier (SLC) gene family in a public privcate partnership. The consortium also develops new transport assays for selected SLCs. | https://re-solute.eu/ | NULL |
| 59 | Fraunhofer Institute HDAC6 screening | HDAC6 | Fraunhofer HDAC6 target Alzheimer's dataset | https://doi.org/10.1016/j.patter.2021.100433 | NULL |
| 60 | MMV Malaria Hit Generation Library | MMV_MALARIA_HGL | Screening and hit evaluation of the MMV Libraries against asexual blood stage Plasmodium falciparum, using a nano luciferase reporter read-out | https://doi.org/10.1016/j.slasd.2022.07.002 | NULL |
| 61 | Karolinska Institute dNTPase SAMHD1 screening | KI_EUBOPEN | Primary screening data was provided for approximately 17K compounds against dNTPase SAMHD1. | NULL | NULL |
| 63 | International Nonproprietary Names (INN) for Pharmaceutical Substances | INN | The WHO selects a globally recognised, unique name for each active substance that is to be marketed as a pharmaceutical. These are published bi-annually via the International Nonproprietary Names (INN) programme. | https://www.who.int/teams/health-product-and-policy-standards/inn/inn-lists | NULL |
| 64 | Cardiff University Schistosomiasis | CSD23 | A library of 80 compounds were tested in vitro on different life cycle stages of the parasite Schistosoma mansoni. The dataset is also available from the ChEMBL - Neglected Tropical Disease archive. | https://chembl.gitbook.io/chembl-ntd/#deposited-set-26-3rd-march-2023-dataset-using-chembl-to-complement-schistosome-drug-discovery | NULL |
| 65 | EUbOPEN Chemogenomic Library Literature Data | LIT_EUBOPEN_CGL | Literature data from EUbOPEN Chemogenomic Library: bioactivity measurements have been extracted from primary literature by the SGC consortium to complement their Chemogenomic library. References to primary literature are indicated in the ACTIVITY_PROPERTIES table (TEXT_VALUE and STANDARD_TEXT_VALUE fields). | NULL | NULL |
| 66 | European Medicines Agency (EMA) | EMA | Medicinal product drug approvals for human and veterinary medicines from the European Medicines Agency, the drug regulatory body for the European Union (EU). | https://www.ema.europa.eu/en/medicines | NULL |
| 67 | University of Dundee T. Cruzi | DUNDEE_T_CRUZI | An NTD initiative from Dundee University using RapidFire-Mass Spectrometry for screening potential LAPTc inhibitors for antichagasic activity. | NULL | NULL |
| 68 | EU-OPENSCREEN | EU-OPENSCREEN | EU-OPENSCREEN is a not-for-profit European Research Infrastructure Consortium (ERIC) for chemical biology and early drug discovery. The EU-OPENSCREEN drug discovery platform holds a unique compound collection (>100,000 compounds), works with advanced screening facilities  and providing an open-access database.  | https://www.eu-openscreen.eu/ | NULL |
| 69 | EMBL Heidelberg Gut Microbiome–host Interactions | ZIMM_BT_12_23 | The Zimmermann group, based at EMBL Heidelberg, investigates how members of microbial communities alter their chemical environment and how this shapes metabolic interactions within the microbiome and between the microbiome and its host.  This 2023 dataset explores the gut microbiome and drug biotransformation. | NULL | NULL |
| 70 | Aberystwyth University Schistosomiasis | ABER_NTD | An NTD initiative from Abersywyth University using the Merck KGaA Open Global health library for anti-schistosome activity. | NULL | NULL |
| 71 | AI-driven Structure-enabled Antiviral Platform (ASAP) | ASAP | The AI-driven Structure-enabled Antiviral Platform (ASAP, asapdiscovery.org), funded by National Institute of Allergy and Infectious Diseases is dedicated to the development of novel chemical assets that have antiviral activity against viral families with future pandemic potential. ASAP adopts a state-of-the-art structure-enabled paradigm capable of leveraging recent advances in AI/ML and computational chemistry in identifying, enabling, and prosecuting discovery campaigns for novel antivirals. | https://asapdiscovery.org | NULL |
| 72 | Chemical Probe data from Scientific Literature | LIT_CHEM_PROBES | Bioactivity data extracted from scientific articles - identified by Natural Language Processing - which contain information about associations of chemical probes, targets, and diseases.  | NULL | NULL |

## Table: chembl_release
Row count: 36
Columns:
- chembl_release_id INTEGER
- chembl_release VARCHAR(20)
- creation_date DATETIME

Full contents:
| chembl_release_id | chembl_release | creation_date |
| --- | --- | --- |
| 1 | CHEMBL_1 | 2009-09-03 00:00:00.000000 |
| 2 | CHEMBL_2 | 2009-11-30 00:00:00.000000 |
| 3 | CHEMBL_3 | 2010-04-16 00:00:00.000000 |
| 4 | CHEMBL_4 | 2010-05-18 00:00:00.000000 |
| 5 | CHEMBL_5 | 2010-06-24 00:00:00.000000 |
| 6 | CHEMBL_6 | 2010-08-27 00:00:00.000000 |
| 7 | CHEMBL_7 | 2010-09-29 00:00:00.000000 |
| 8 | CHEMBL_8 | 2010-10-26 00:00:00.000000 |
| 9 | CHEMBL_9 | 2011-01-20 00:00:00.000000 |
| 10 | CHEMBL_10 | 2011-05-26 00:00:00.000000 |
| 11 | CHEMBL_11 | 2011-08-01 00:00:00.000000 |
| 12 | CHEMBL_12 | 2011-11-18 00:00:00.000000 |
| 13 | CHEMBL_13 | 2012-02-21 00:00:00.000000 |
| 14 | CHEMBL_14 | 2012-06-27 00:00:00.000000 |
| 15 | CHEMBL_15 | 2013-01-23 00:00:00.000000 |
| 16 | CHEMBL_16 | 2013-05-07 00:00:00.000000 |
| 17 | CHEMBL_17 | 2013-08-29 00:00:00.000000 |
| 18 | CHEMBL_18 | 2014-03-12 00:00:00.000000 |
| 19 | CHEMBL_19 | 2014-07-03 00:00:00.000000 |
| 20 | CHEMBL_20 | 2015-01-14 00:00:00.000000 |
| 21 | CHEMBL_21 | 2016-02-01 00:00:00.000000 |
| 22 | CHEMBL_22 | 2016-11-08 00:00:00.000000 |
| 23 | CHEMBL_23 | 2017-05-01 00:00:00.000000 |
| 24 | CHEMBL_24 | 2018-04-23 00:00:00.000000 |
| 25 | CHEMBL_25 | 2018-12-10 00:00:00.000000 |
| 26 | CHEMBL_26 | 2020-01-10 00:00:00.000000 |
| 27 | CHEMBL_27 | 2020-05-18 00:00:00.000000 |
| 28 | CHEMBL_28 | 2021-01-15 00:00:00.000000 |
| 29 | CHEMBL_29 | 2021-07-01 00:00:00.000000 |
| 30 | CHEMBL_30 | 2022-02-22 00:00:00.000000 |
| 31 | CHEMBL_31 | 2022-07-12 00:00:00.000000 |
| 32 | CHEMBL_32 | 2023-01-26 00:00:00.000000 |
| 33 | CHEMBL_33 | 2023-05-31 00:00:00.000000 |
| 34 | CHEMBL_34 | 2024-03-28 00:00:00.000000 |
| 35 | CHEMBL_35 | 2024-12-01 00:00:00.000000 |
| 36 | CHEMBL_36 | 2025-07-28 00:00:00.000000 |

## Table: version
Row count: 11
Columns:
- name VARCHAR(50)
- creation_date DATETIME
- comments VARCHAR(2000)

Full contents:
| name | creation_date | comments |
| --- | --- | --- |
| Bioassay Ontology 2.0 | NULL | BAO version used for assays (http://bioassayontology.org/) |
| COCONUT 2025-07 | NULL | COCONUT version used for natural product flagging (https://coconut.naturalproducts.net/) |
| ChEMBL_36 | 2025-07-28 00:00:00.000000 | ChEMBL Release 36 (https://www.ebi.ac.uk/chembl) |
| ChEMBL_Structure_Pipeline 1.2.0 | NULL | ChEMBL_Structure_Pipeline version used for chemical structure curation (https://github.com/chembl/ChEMBL_Structure_Pipeline) |
| EFO 3.74.0 | NULL | EFO version used for indication and warning data (https://www.ebi.ac.uk/efo/) |
| Gene Ontology 2024-02-22 | NULL | GO version used for genes (https://www.ebi.ac.uk/QuickGO/) |
| InChI v1.06 | NULL | InChI version used for compound registration (https://github.com/IUPAC-InChI/InChI) |
| MeSH 2025 | NULL | MeSH version used for indication data (https://www.nlm.nih.gov/mesh/meshhome.html) |
| RDKit 2022.09.4 | NULL | RDKit version used for standardisation and salt stripping of chemical structures (https://www.rdkit.org/) |
| Swiss-Prot 2025_03 | NULL | UniProtKB version used for component_sequences data (https://www.expasy.org/resources/uniprotkb) |
| UBERON 2024-03-22 | NULL | UBERON version used for tissues (http://obophenotype.github.io/uberon/) |

