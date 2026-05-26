"""
Standalone Dataplex Rule Builder CLI.

Provides an interactive terminal interface for building Dataplex Data Quality rules.
Fetches live schemas from BigQuery and exports results to a user-agnostic CSV.
"""

import sys
import os
# Add parent and Shared_Resources to path
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.append(BASE_DIR)

import pandas as pd
from google.cloud import bigquery
from Shared_Resources.networking import setup_environment_logic

def setup_proxy():
    """Interactively configures environment proxies using shared logic."""
    print("\n--- Proxy & Auth Setup ---")
    success, mode, status = setup_environment_logic()
    print(f"Connection Mode: {mode}")
    print(f"Auth Status: {status}")
    
    if not success:
        print(f"\n[!] Setup failed: {status}")
        print("    Please run 'gcloud auth application-default login' and check your network.")
        sys.exit(1)

def select_from_list(items, prompt):
    """Helper to select an item from a list by index."""
    print(f"\nAvailable {prompt}:")
    for i, item in enumerate(items):
        print(f"[{i}] {item}")
    while True:
        try:
            choice = int(input(f"Select {prompt} index: "))
            return items[choice]
        except (ValueError, IndexError):
            print("Invalid selection. Try again.")

def define_new_rule(client, projects):
    """Orchestrates the definition of a single data quality rule."""
    print("\n" + "-"*20 + "\nDefining a New Rule\n" + "-"*20)

    # 1. Source Data Selection
    print("\n[Step 1] Source Data")
    src_project = select_from_list(projects, "Project")
    datasets = [d.dataset_id for d in client.list_datasets(project=src_project)]
    src_dataset = select_from_list(datasets, "Dataset")
    tables = [t.table_id for t in client.list_tables(f"{src_project}.{src_dataset}")]
    src_table = select_from_list(tables, "Table")
    
    table_ref = f"{src_project}.{src_dataset}.{src_table}"
    table_obj = client.get_table(table_ref)
    src_columns = [f.name for f in table_obj.schema]

    # 2. Historic Data Selection
    print("\n[Step 2] Historic Data (Optional)")
    has_hist = input("Use a historic table for comparison? (y/n): ").lower() == 'y'
    hist_project = hist_dataset = hist_table = ""
    if has_hist:
        hist_project = select_from_list(projects, "Historic Project")
        h_datasets = [d.dataset_id for d in client.list_datasets(project=hist_project)]
        hist_dataset = select_from_list(h_datasets, "Historic Dataset")
        h_tables = [t.table_id for t in client.list_tables(f"{hist_project}.{hist_dataset}")]
        hist_table = select_from_list(h_tables, "Historic Table")

    # 3. Rule Details
    print("\n[Step 3] Rule Definition")
    col_name = select_from_list(["(Table Level)", "Derived Attributes"] + src_columns, "Target Column")
    if col_name == "Derived Attributes":
        col_name = input("Enter Attribute Name (default: 'Columns with _d or _d_(case insenstive) in their names'): ").strip() or "Columns with _d or _d_(case insenstive) in their names"
    elif col_name == "(Table Level)":
        col_name = ""

    dimensions = ["COMPLETENESS", "UNIQUENESS", "VALIDITY", "TIMELINESS", "ACCURACY", "VOLUME", "CONSISTENCY"]
    dimension = select_from_list(dimensions, "Dimension")
    types = ["NonNull", "Uniqueness", "Range", "Set", "Regex", "SqlAssertion"]
    rule_type = select_from_list(types, "Rule Type")
    
    logic = input("Enter Rule Logic (Plain English): ").strip()
    
    t_type = select_from_list(["Single", "Range"], "Threshold Type")
    if t_type == "Single":
        threshold = float(input("Enter Threshold (0.0 - 1.0, default 1.0): ") or "1.0")
        lower_threshold = upper_threshold = ""
    else:
        threshold = ""
        lower_threshold = float(input("Enter Lower Threshold (default 0.0): ") or "0.0")
        upper_threshold = float(input("Enter Upper Threshold (default 1.0): ") or "1.0")
        
    ignore_null = input("Ignore Nulls? (y/n, default n): ").lower() == 'y'
    
    scan_id = input(f"Enter Scan ID (default {src_table}-dq-scan): ").strip() or f"{src_table}-dq-scan"
    disp_name = input(f"Enter Display Name (default {src_table.capitalize()} Quality Scan): ").strip() or f"{src_table.capitalize()} Quality Scan"
    scan_desc = input(f"Enter Scan Description (default 'DQ Scan for {src_table}'): ").strip() or f"DQ Scan for {src_table}"
    
    inc_field = select_from_list(["None"] + src_columns, "Incremental Field")
    email = input("Enter Notification Email: ").strip()
    location = input("Enter Location (default us-central1): ").strip() or "us-central1"
    cron = input("Enter Schedule (Cron, default '0 0 * * *'): ").strip() or "0 0 * * *"
    labels = input("Enter Labels (k=v, default 'env=prod'): ").strip() or "env=prod"
    
    sampling = float(input("Enter Sampling Percent (0.0 - 100.0, default 100.0): ") or "100.0")
    row_filter = input("Enter Row Filter (SQL WHERE clause, e.g., status='ACTIVE' or press Enter for None): ").strip()

    return {
        "Source_Project": src_project, "Source_Dataset": src_dataset, "Source_Table": src_table,
        "Historic_Project": hist_project, "Historic_Dataset": hist_dataset, "Historic_Table": hist_table,
        "Location": location, "Scan_ID": scan_id, "Display_Name": disp_name,
        "Scan_Description": scan_desc, "Schedule_Cron": cron,
        "Incremental_Field": inc_field if inc_field != "None" else "", "Labels": labels,
        "Sampling_Percent": sampling, "Row_Filter": row_filter,
        "Column_Name": col_name,
        "Dimension": dimension, "Rule_Type": rule_type, "Rule_Logic": logic,
        "Threshold": threshold, "Lower_Threshold": lower_threshold, "Upper_Threshold": upper_threshold,
        "Ignore_Null": str(ignore_null).upper(), "Notification_Email": email
    }

def main():
    """Main CLI entry point."""
    print("="*40 + "\n   DATAPLEX RULE BUILDER (CLI)\n" + "="*40)
    setup_proxy()

    try:
        client = bigquery.Client()
        projects = [p.project_id for p in client.list_projects()]
    except Exception as error: # pylint: disable=broad-except
        print(f"Initialization Error: {error}")
        return

    rules_list = []
    while True:
        try:
            rules_list.append(define_new_rule(client, projects))
            print("\n[✓] Rule added successfully.")
            if input("\nAdd another rule? (y/n): ").lower() != 'y':
                break
        except Exception as error: # pylint: disable=broad-except
            print(f"Error adding rule: {error}. Restarting rule definition...")

    if rules_list:
        print("\n--- Current Rules Table ---")
        df_rules = pd.DataFrame(rules_list)
        print(df_rules[["Source_Table", "Column_Name", "Dimension", "Rule_Logic"]])

        filename = input("\nEnter filename to save (e.g., rules.csv): ").strip() or "rules.csv"
        save_dir = os.path.dirname(os.path.abspath(__file__))
        save_path = os.path.join(save_dir, filename)
        df_rules.to_csv(save_path, index=False)
        print(f"\n[✓] All rules saved to: {save_path}")

if __name__ == "__main__":
    main()
