# Dataplex Scan Configuration Columns

## 1. Resource & Location (Batch/CLI)
- **Source_Project**: The GCP Project ID for the source data.
- **Source_Dataset**: The BigQuery Dataset ID for the source data.
- **Source_Table**: The BigQuery Table name.
- **Historic_Project**: The GCP Project ID for historical comparison data.
- **Historic_Dataset**: The BigQuery Dataset ID for historical comparison data.
- **Historic_Table**: The BigQuery Table name for historical comparison data.
- **Location**: GCP Region (e.g., `us-central1`).
- **Scan_ID**: Unique ID for the scan (if empty, agent will derive from table name).
- **Display_Name**: Friendly name for the scan.
- **Scan_Description**: Purpose of the scan.

## 2. Execution & Scope (Batch/CLI)
- **Schedule_Cron**: Cron expression for scheduling (e.g., `0 0 * * *`).
- **Incremental_Field**: The DATE/TIMESTAMP column for delta-scans.
- **Labels**: Key-value pairs (e.g., `env=prod,dept=finance`).

## 3. Data Quality Spec (YAML)
- **Sampling_Percent**: 0.0 to 100.0 (percentage of data to scan).
- **Row_Filter**: SQL WHERE clause (e.g., `status = 'ACTIVE'`).

## 4. Individual Rule Settings (YAML)
- **Column_Name**: Specific column for the rule (optional for table-level SQL).
- **Dimension**: COMPLETENESS, UNIQUENESS, VALIDITY, TIMELINESS, ACCURACY, VOLUME, CONSISTENCY.
- **Rule_Type**: NonNull, Uniqueness, Range, Set, Regex, SqlAssertion.
- **Rule_Logic**: Plain English description of the check.
- **Threshold**: 0.0 to 1.0 (pass rate requirement).
- **Ignore_Null**: TRUE/FALSE (whether to skip nulls in the check).
- **Notification_Email**: Destination for alerts.

---
### Optimal CSV Order:
Source_Project,Source_Dataset,Source_Table,Historic_Project,Historic_Dataset,Historic_Table,Location,Scan_ID,Display_Name,Scan_Description,Schedule_Cron,Incremental_Field,Labels,Sampling_Percent,Row_Filter,Column_Name,Dimension,Rule_Type,Rule_Logic,Threshold,Ignore_Null,Notification_Email
