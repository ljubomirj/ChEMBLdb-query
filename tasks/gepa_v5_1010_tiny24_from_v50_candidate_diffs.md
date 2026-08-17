# GEPA Tiny24 Candidate Diffs vs v5.0

Base prompt pack:
- `/data1/data/ChEMBLdb-query/experiments/prompt_pack_v5.0.yaml`

Mutated candidates compared:
- `/data1/data/ChEMBLdb-query/experiments/evals/v5_forward_eval/gepa_v5_1010_tiny24_from_v50_20260426_232232/candidate_cache/candidate_118f2aead635f0a0.yaml`
- `/data1/data/ChEMBLdb-query/experiments/evals/v5_forward_eval/gepa_v5_1010_tiny24_from_v50_20260426_232232/candidate_cache/candidate_60010841f8c68b9c.yaml`
- `/data1/data/ChEMBLdb-query/experiments/evals/v5_forward_eval/gepa_v5_1010_tiny24_from_v50_20260426_232232/candidate_cache/candidate_d3f6064ebaa1a447.yaml`
- `/data1/data/ChEMBLdb-query/experiments/evals/v5_forward_eval/gepa_v5_1010_tiny24_from_v50_20260426_232232/candidate_cache/candidate_e622365aeaa6efb5.yaml`

## candidate_118f2aead635f0a0.yaml

```diff
--- /data1/data/ChEMBLdb-query/experiments/prompt_pack_v5.0.yaml	2026-03-22 06:16:41.371869497 +0000
+++ /data1/data/ChEMBLdb-query/experiments/evals/v5_forward_eval/gepa_v5_1010_tiny24_from_v50_20260426_232232/candidate_cache/candidate_118f2aead635f0a0.yaml	2026-04-26 23:24:05.706148572 +0100
@@ -41,6 +41,12 @@
     <TASK>
     Convert the execution-oriented User Prompt into a single executable SQLite SELECT query for ChEMBL.
     Preserve requested output schema exactly when specified.
+    
+    CRITICAL SCHEMA RULES:
+    - ONLY use columns and tables explicitly defined in the ChEMBL database schema.
+    - NEVER hallucinate columns or abbreviations that do not exist in the schema (e.g., do NOT use 'tid' as a column name; use 'target_chembl_id' or 'target_id' as appropriate for the table).
+    - If a column name seems implicit or ambiguous, map it to the correct full schema column name (e.g., 'target id' -> 'target_chembl_id').
+    
     Output JSON only with key "sql".
     </TASK>
   judge: |
@@ -77,4 +83,4 @@
 scoring:
   judge_threshold: 0.9
   uq_up_echo_penalty_threshold: 0.95
-  uq_up_echo_penalty_weight: 0.15
+  uq_up_echo_penalty_weight: 0.15
\ No newline at end of file
```

## candidate_60010841f8c68b9c.yaml

```diff
--- /data1/data/ChEMBLdb-query/experiments/prompt_pack_v5.0.yaml	2026-03-22 06:16:41.371869497 +0000
+++ /data1/data/ChEMBLdb-query/experiments/evals/v5_forward_eval/gepa_v5_1010_tiny24_from_v50_20260426_232232/candidate_cache/candidate_60010841f8c68b9c.yaml	2026-04-26 23:24:57.249719725 +0100
@@ -1,4 +1,4 @@
-version: v5.0
+version: v5.1
 system:
   about_block: |
     You will be used in forward and backward roles inside a ChEMBL text-to-SQL system.
@@ -33,14 +33,21 @@
       Return ...
       Sort ...
       Limit ...
-    - Preserve requested output columns and aliases exactly when the case requires them.
+    - Column Fidelity: Explicitly specify the columns required in the final output.
+    - Join Clarity: When multiple tables are involved, specify the join keys or relationships (e.g., "Join assays to activities on assay ID").
+    - Filter Semantics: Be explicit about filter values, negation (NOT), ranges (>, <, BETWEEN), and boolean logic (AND/OR).
     - Mention deduplication only when the task truly requires DISTINCT or explicitly forbids deduplication.
     Output JSON only with key "up".
     </TASK>
   sql: |
     <TASK>
     Convert the execution-oriented User Prompt into a single executable SQLite SELECT query for ChEMBL.
-    Preserve requested output schema exactly when specified.
+    Rules:
+    - Preserve requested output schema exactly when specified.
+    - For ChEMBL: Use 'activities' as the central fact table. Join to 'assays' (via assay_id) and 'molecule_dictionary' (via mol_id) as needed.
+    - Columns: 'standard_value' is numeric. 'pchembl_value' is the negative log of potency.
+    - Nulls: Handle potential NULLs in numeric columns (e.g., pchembl_value) if filtering or sorting.
+    - DISTINCT: Only use if the UP explicitly requests deduplication or the UQ implies unique entities.
     Output JSON only with key "sql".
     </TASK>
   judge: |
@@ -77,4 +84,4 @@
 scoring:
   judge_threshold: 0.9
   uq_up_echo_penalty_threshold: 0.95
-  uq_up_echo_penalty_weight: 0.15
+  uq_up_echo_penalty_weight: 0.15
\ No newline at end of file
```

## candidate_d3f6064ebaa1a447.yaml

```diff
--- /data1/data/ChEMBLdb-query/experiments/prompt_pack_v5.0.yaml	2026-03-22 06:16:41.371869497 +0000
+++ /data1/data/ChEMBLdb-query/experiments/evals/v5_forward_eval/gepa_v5_1010_tiny24_from_v50_20260426_232232/candidate_cache/candidate_d3f6064ebaa1a447.yaml	2026-04-26 23:26:27.964962910 +0100
@@ -11,7 +11,7 @@
     "Top 10 most potent compounds against EGFR by IC50"
 
     Example execution-plan UP:
-    "Return the top 10 compounds ranked by lowest IC50 against human EGFR. Select compound identifiers and potency values only."
+    "Select compound identifiers and potency values. Join molecule_dictionary and activities. Filter where target is EGFR and standard_type is IC50. Sort by standard_value ascending. Limit 10."
 
     Example backward reconstruction target:
     "Recover a realistic user question from the execution-plan artifact without leaking SQL syntax."
@@ -26,21 +26,22 @@
     - Do not repeat the UQ with minor edits.
     - Do not use SQL keywords or write SQL syntax.
     - Normalize the task into operations a SQL writer can follow.
-    - Prefer compact imperative structure such as:
-      Select ...
-      Join ...
-      Filter ...
-      Return ...
-      Sort ...
-      Limit ...
-    - Preserve requested output columns and aliases exactly when the case requires them.
+    - Prefer compact imperative structure specifying:
+      Select: [list exact column names]
+      Join: [tables and keys]
+      Filter: [conditions]
+      Sort: [order]
+      Limit: [count]
+    - Preserve requested output columns and aliases exactly.
+    - Explicitly list output columns required for the result set.
     - Mention deduplication only when the task truly requires DISTINCT or explicitly forbids deduplication.
     Output JSON only with key "up".
     </TASK>
   sql: |
     <TASK>
     Convert the execution-oriented User Prompt into a single executable SQLite SELECT query for ChEMBL.
-    Preserve requested output schema exactly when specified.
+    - Strictly follow the column names and aliases specified in the UP Select clause.
+    - Ensure all filters are translated accurately into the WHERE clause.
     Output JSON only with key "sql".
     </TASK>
   judge: |
@@ -77,4 +78,4 @@
 scoring:
   judge_threshold: 0.9
   uq_up_echo_penalty_threshold: 0.95
-  uq_up_echo_penalty_weight: 0.15
+  uq_up_echo_penalty_weight: 0.15
\ No newline at end of file
```

## candidate_e622365aeaa6efb5.yaml

```diff
--- /data1/data/ChEMBLdb-query/experiments/prompt_pack_v5.0.yaml	2026-03-22 06:16:41.371869497 +0000
+++ /data1/data/ChEMBLdb-query/experiments/evals/v5_forward_eval/gepa_v5_1010_tiny24_from_v50_20260426_232232/candidate_cache/candidate_e622365aeaa6efb5.yaml	2026-04-26 23:27:18.824537588 +0100
@@ -27,12 +27,14 @@
     - Do not use SQL keywords or write SQL syntax.
     - Normalize the task into operations a SQL writer can follow.
     - Prefer compact imperative structure such as:
-      Select ...
-      Join ...
-      Filter ...
-      Return ...
-      Sort ...
+      Select [specific columns] ...
+      From [tables] ...
+      Join [conditions] ...
+      Filter [exact criteria] ...
+      Group By [columns] ...
+      Order By [columns] ...
       Limit ...
+    - Resolve schema ambiguity explicitly. If multiple valid paths exist, state the required linkage.
     - Preserve requested output columns and aliases exactly when the case requires them.
     - Mention deduplication only when the task truly requires DISTINCT or explicitly forbids deduplication.
     Output JSON only with key "up".
@@ -40,6 +42,10 @@
   sql: |
     <TASK>
     Convert the execution-oriented User Prompt into a single executable SQLite SELECT query for ChEMBL.
+    Adhere strictly to the execution plan structure:
+    - Ensure column fidelity: Select ONLY the columns listed in the UP.
+    - Ensure join fidelity: Use ONLY the tables and join conditions implied or stated in the UP.
+    - Ensure filter fidelity: Apply ONLY the explicit filters stated in the UP.
     Preserve requested output schema exactly when specified.
     Output JSON only with key "sql".
     </TASK>
@@ -77,4 +83,4 @@
 scoring:
   judge_threshold: 0.9
   uq_up_echo_penalty_threshold: 0.95
-  uq_up_echo_penalty_weight: 0.15
+  uq_up_echo_penalty_weight: 0.15
\ No newline at end of file
```

