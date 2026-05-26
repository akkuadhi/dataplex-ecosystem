"""
BigQuery Schema Retrieval Agent.

This script allows users to interactively discover projects, datasets, and tables
within Google Cloud BigQuery and extract their official schemas.
Supports corporate proxies and adheres to default gcloud authentication.
"""

import sys
import os
# Add parent and Shared_Resources to path
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.append(BASE_DIR)

from google.cloud import bigquery
from Shared_Resources.networking import setup_environment_logic

def setup_environment():
    """Configures proxy and environment settings based on shared logic."""
    print("\n" + "="*40)
    print("   BIGQUERY SCHEMA RETRIEVAL AGENT")
    print("="*40)
    
    print("\n[1/5] Proxy & Auth Setup")
    success, mode, status = setup_environment_logic()
    print(f"  -> Connection Mode: {mode}")
    print(f"  -> Auth Status: {status}")
    
    if not success:
        print(f"  [!] Setup failed: {status}")
        print("  [!] Please run 'gcloud auth application-default login' and check your network.")
        sys.exit(1)

    print("  -> Using default Python environment and gcloud authentication.")

def get_target_tables():
    """Prompts user for target table IDs."""
    print("\n[2/5] Table Input")
    tables_input = input("Enter table IDs (comma-separated, e.g., 'users, orders'): ").strip()
    return set(t.strip() for t in tables_input.split(",") if t.strip())

import json
def get_allowed_projects():
    """Reads the list of allowed projects from config file."""
    config_path = os.path.join(BASE_DIR, "Shared_Resources", "project_config.json")
    if os.path.exists(config_path):
        try:
            with open(config_path, 'r') as f:
                config = json.load(f)
                return config.get("allowed_projects", [])
        except:
            pass
    return []

def discover_table_locations(client, target_tables):
    """Scans projects (Filtered by project_config.json) to find tables."""
    print("\n[3/5] Searching for tables...")
    found_locations = []
    
    allowed = get_allowed_projects()
    if allowed:
        projects = allowed
        print(f"  -> Scanning {len(allowed)} projects from config.")
    else:
        all_proj = list(client.list_projects())
        projects = [p.project_id for p in all_proj]
        if not projects:
            print("  [!] No projects found. Ensure you are authenticated.")
            return None

    for project_id in projects:
        print(f"  Scanning: {project_id}...", end="\r")
        try:
            datasets = list(client.list_datasets(project=project_id))
            for dataset in datasets:
                dataset_id = dataset.dataset_id
                tables = list(client.list_tables(f"{project_id}.{dataset_id}"))
                existing_table_ids = {t.table_id for t in tables}
                
                matches = target_tables.intersection(existing_table_ids)
                if matches:
                    found_locations.append({
                        "project": project_id,
                        "dataset": dataset_id,
                        "tables": list(matches)
                    })
        except Exception:
            continue
    
    print("  Scanning complete.                                ")
    return found_locations

def main():
    """Main execution loop for schema discovery."""
    setup_environment()

    try:
        client = bigquery.Client()
        target_tables = get_target_tables()
        
        if not target_tables:
            print("  [!] No tables provided. Exiting.")
            return

        found_locations = discover_table_locations(client, target_tables)
        if not found_locations:
            print(f"  [!] No matches found for {target_tables} in any accessible project.")
            return

        print("\n[4/5] Select a location where the tables were found:")
        for i, loc in enumerate(found_locations):
            print(f"    [{i}] Project: {loc['project']} | Dataset: {loc['dataset']}")
            print(f"        Found: {', '.join(loc['tables'])}")
        
        try:
            selection = int(input("\n  Select index to view schemas: "))
            selected_loc = found_locations[selection]
        except (ValueError, IndexError):
            print("  [!] Invalid selection.")
            return

        print(f"\n[5/5] Retrieving Schemas from {selected_loc['project']}.{selected_loc['dataset']}")
        print("-" * 60)
        
        for table_id in selected_loc['tables']:
            try:
                table_ref = f"{selected_loc['project']}.{selected_loc['dataset']}.{table_id}"
                table = client.get_table(table_ref)
                
                print(f"\nTABLE: {table_id}")
                print(f"{'Field Name':<30} | {'Type':<10} | {'Mode':<10}")
                print("." * 60)
                for field in table.schema:
                    print(f"{field.name:<30} | {field.field_type:<10} | {field.mode:<10}")
            except Exception as error: # pylint: disable=broad-except
                print(f"\n[!] Error fetching '{table_id}': {error}")
        
        print("\n" + "="*40 + "\n   Task Completed.\n" + "="*40)

    except Exception as critical_error: # pylint: disable=broad-except
        print(f"\n[CRITICAL ERROR] {critical_error}")

if __name__ == "__main__":
    main()
