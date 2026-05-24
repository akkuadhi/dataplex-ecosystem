"""
BigQuery Schema Retrieval Agent.

This script allows users to interactively discover projects, datasets, and tables
within Google Cloud BigQuery and extract their official schemas.
Supports corporate proxies and adheres to default gcloud authentication.
"""

import os
import sys
from google.cloud import bigquery

def setup_environment():
    """Configures proxy and environment settings based on user input."""
    print("\n" + "="*40)
    print("   BIGQUERY SCHEMA RETRIEVAL AGENT")
    print("="*40)
    
    print("\n[1/5] Proxy Setup")
    proxy_url = input("Enter proxy URL (e.g., proxy.company.com:port) or press Enter to skip: ").strip()
    if proxy_url:
        use_creds = input("Use custom proxy credentials? (y/n): ").lower() == 'y'
        if use_creds:
            user = input("Proxy Username: ").strip()
            password = input("Proxy Password: ").strip()
            proxy = f"http://{user}:{password}@{proxy_url}"
        else:
            proxy = f"http://{proxy_url}"
        
        os.environ['HTTP_PROXY'] = proxy
        os.environ['HTTPS_PROXY'] = proxy
        os.environ['http_proxy'] = proxy
        os.environ['https_proxy'] = proxy
        print("  -> Proxy configured.")
    else:
        print("  -> No proxy configured.")

    print("  -> Using default Python environment and gcloud authentication.")

def get_target_tables():
    """Prompts user for target table IDs."""
    print("\n[2/5] Table Input")
    tables_input = input("Enter table IDs (comma-separated, e.g., 'users, orders'): ").strip()
    return set(t.strip() for t in tables_input.split(",") if t.strip())

def discover_table_locations(client, target_tables):
    """Scans all accessible projects to find the datasets containing target tables."""
    print("\n[3/5] Searching for tables across your projects...")
    found_locations = []
    
    projects = list(client.list_projects())
    if not projects:
        print("  [!] No projects found. Ensure you are authenticated.")
        return None

    for project in projects:
        project_id = project.project_id
        print(f"  Scanning project: {project_id}...", end="\r")
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
        except Exception: # pylint: disable=broad-except
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
