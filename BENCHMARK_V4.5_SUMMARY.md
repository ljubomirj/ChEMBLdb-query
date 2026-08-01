# ChEMBL Text-to-SQL Benchmark v4.5 - Expansion Summary

## Overview

Successfully expanded the ChEMBL text-to-SQL benchmark from **95 to 200 cases** (2.1x expansion), achieving the target of 200+ cases.

## Results

### Final Statistics

- **Previous benchmark (v4.4_final)**: 95 cases
- **New benchmark (v4.5)**: 200 cases
- **New cases added**: 105 cases
- **Expansion factor**: 2.1x

### Case Distribution

| Split | Cases | Percentage |
|-------|-------|------------|
| Train | 127   | 63.5%      |
| Val   | 33    | 16.5%      |
| Test  | 40    | 20.0%      |
| **Total** | **200** | **100%** |

## New Cases Created

### Round 18 (15 cases)
- **Type**: Target IC50 queries
- **Focus**: Human single protein targets with high-quality IC50 data
- **Examples**: CHEMBL203, CHEMBL2971, CHEMBL279, etc.

### Round 19 (10 cases)
- **Type**: Target IC50 queries
- **Focus**: Additional human targets
- **Examples**: CHEMBL1865, CHEMBL220, CHEMBL5145, etc.

### Round 20 (15 cases)
- **Type**: Assay queries
- **Focus**: High-throughput assays with many activities
- **Examples**: CHEMBL4888485 (295K activities), CHEMBL4689845 (216K activities)

### Round 21 (10 cases)
- **Type**: Document molecule queries
- **Focus**: Documents with 100 molecules each
- **Examples**: CHEMBL1138844, CHEMBL1139796, etc.

### Round 22 (5 cases)
- **Type**: Document molecule queries
- **Focus**: Additional documents
- **Examples**: CHEMBL3638969, CHEMBL3886467, etc.

### Round 28 (50 cases)
- **Type**: Target IC50 queries
- **Focus**: Diverse human targets not previously covered
- **Examples**: CHEMBL3921, CHEMBL3356, CHEMBL3397, etc.

## Case Types Distribution

The expanded benchmark includes:

1. **Target IC50 queries** (95 cases): Query bioactivity data for specific human protein targets
2. **Assay queries** (15 cases): Query all activities from specific assays
3. **Document molecule queries** (15 cases): Query molecules mentioned in specific documents
4. **Legacy queries** (75 cases): Original diverse query patterns from v4.4

## Quality Controls Applied

All new cases meet these quality standards:

- ✅ SQL executes successfully on ChEMBL 36 SQLite database
- ✅ Results are deterministic (sorted with ORDER BY)
- ✅ CSV properly formatted (no ragged lines)
- ✅ Ground truth materialized and compressed with zstd
- ✅ No duplicate cases (checked by ID+UQ)
- ✅ Metadata complete with source URLs

## Files Created

### Fixtures
- `/tests/fixtures/web_scrape18/` - 15 target cases
- `/tests/fixtures/web_scrape19/` - 10 target cases
- `/tests/fixtures/web_scrape20/` - 15 assay cases
- `/tests/fixtures/web_scrape21/` - 10 document cases
- `/tests/fixtures/web_scrape22/` - 5 document cases
- `/tests/fixtures/web_scrape28/` - 50 target cases

### Case Definitions
- `/tests/cases/web_scrape_hq_cases.json` - 200 cases (updated)
- `/experiments/case_splits_v4.5.json` - Train/val/test splits

### Scripts
- `/scripts/generate_expansion_rounds.py` - Generated rounds 18-22 (55 cases)
- `/scripts/generate_final_50.py` - Generated round 28 (50 cases)
- `/scripts/promote_rounds_18_22.py` - Promotion script for rounds 18-22
- `/scripts/final_promotion_v45.py` - Final v4.5 creation script

## Query Patterns

The benchmark now covers diverse query patterns:

1. **Target-centric queries**:
   ```sql
   SELECT ... FROM target_dictionary
   JOIN assays, activities, molecule_dictionary, compound_structures
   WHERE target_chembl_id = 'CHEMBLXXX'
   ```

2. **Assay-centric queries**:
   ```sql
   SELECT ... FROM assays
   JOIN activities, molecule_dictionary, compound_structures
   WHERE assay_chembl_id = 'CHEMBLXXX'
   ```

3. **Document-centric queries**:
   ```sql
   SELECT ... FROM docs
   JOIN compound_records, molecule_dictionary, compound_structures
   WHERE doc_chembl_id = 'CHEMBLXXX'
   ```

## Database

- **Version**: ChEMBL 36
- **File**: `chembl_36.db` (SQLite)
- **Size**: ~5.6 GB
- **Location**: `/database/latest/chembl_36/chembl_36_sqlite/`

## Next Steps

To use the new v4.5 benchmark:

1. Update evaluation scripts to use `case_splits_v4.5.json`
2. Run baselines on the expanded dataset
3. Compare v4.4 vs v4.5 performance
4. Analyze which new cases are more challenging

## Acknowledgments

Query patterns based on [chembl_downloader](https://github.com/cthoyt/chembl-downloader) by @cthoyt.

---

**Generated**: 2026-03-18
**Total cases**: 200 (expanded from 95)
**Expansion**: +105 cases (+111%)
