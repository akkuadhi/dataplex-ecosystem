"""
Standalone Dataplex Rule Builder CLI.

Provides an interactive terminal interface for building Dataplex Data Quality rules.
Fetches live schemas from BigQuery and exports results to a user-agnostic CSV.
"""

import os
import pandas as pd
from google.cloud import bigquery

def setup_proxy():
    """Interactively configures environment proxies."""
    print("\n--- Proxy Configuration ---")
    proxy_url = input("Enter proxy URL (e.g., proxy.co.com:8080) or press Enter to skip: ").strip()
    if proxy_url:
        use_creds = input("Use custom proxy credentials? (y/n): ").lower() == 'y'
        if use_creds:
            user = input("Proxy Username: ").strip()
            password = input("Proxy Password: ").strip()
            proxy = f"http={user}:{password}@{proxy_url}"
        else:
            proxy = f"http://{proxy_url}"
        
        os.environ['HTTP_PROXY'] = proxy
        os.environ['HTTPS_PROXY'] = proxy
        os.environ['http_proxy'] = proxy
        os.environ['https_proxy'] = proxy
        print("Proxy configured.")
    else:
        print("No proxy configured.")

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
    col_name = select_from_list(["(Table Level)"] + src_columns, "Target Column")
    dimensions = ["COMPLETENESS", "UNIQUENESS", "VALIDITY", "TIMELINESS", "ACCURACY", "VOLUME", "CONSISTENCY"]
    dimension = select_from_list(dimensions, "Dimension")
    types = ["NonNull", "Uniqueness", "Range", "Set", "Regex", "SqlAssertion"]
    rule_type = select_from_list(types, "Rule Type")
    
    logic = input("Enter Rule Logic (Plain English): ").strip()
    threshold = float(input("Enter Threshold (0.0 - 1.0, default 1.0): ") or "1.0")
    ignore_null = input("Ignore Nulls? (y/n, default n): ").lower() == 'y'
    
    scan_id = input(f"Enter Scan ID (default {src_table}-dq-scan): ").strip() or f"{src_table}-dq-scan"
    disp_name = input(f"Enter Display Name (default {src_table.capitalize()} Quality Scan): ").strip() or f"{src_table.capitalize()} Quality Scan"
    inc_field = select_from_list(["None"] + src_columns, "Incremental Field")
    email = input("Enter Notification Email: ").strip()
    location = input("Enter Location (default us-central1): ").strip() or "us-central1"
    cron = input("Enter Schedule (Cron, default '0 0 * * *'): ").strip() or "0 0 * * *"
    labels = input("Enter Labels (k=v, default 'env=prod'): ").strip() or "env=prod"

    return {
        "Source_Project": src_project, "Source_Dataset": src_dataset, "Source_Table": src_table,
        "Historic_Project": hist_project, "Historic_Dataset": hist_dataset, "Historic_Table": hist_table,
        "Location": location, "Scan_ID": scan_id, "Display_Name": disp_name,
        "Scan_Description": f"DQ Scan for {src_table}", "Schedule_Cron": cron,
        "Incremental_Field": inc_field if inc_field != "None" else "", "Labels": labels,
        "Sampling_Percent": 100, "Row_Filter": "",
        "Column_Name": col_name if col_name != "(Table Level)" else "",
        "Dimension": dimension, "Rule_Type": rule_type, "Rule_Logic": logic,
        "Threshold": threshold, "Ignore_Null": str(ignore_null).upper(), "Notification_Email": email
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
