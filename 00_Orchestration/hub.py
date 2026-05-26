"""
Dataplex Master Orchestrator (Hub).
- Uses Resource Manager & Discovery APIs for optimized resource discovery.
- Implements multithreaded verification logic.
- Intelligent proxy detection and auto-authentication.
"""

import os
import json
import subprocess
from datetime import datetime
import streamlit as st
import pandas as pd
import yaml
import requests
from googleapiclient.discovery import build
from google.auth import default
from concurrent.futures import ThreadPoolExecutor, as_completed
from streamlit.runtime.scriptrunner import add_script_run_ctx

# --- Dynamic Pathing ---
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUTPUTS_BASE = os.path.join(BASE_DIR, "outputs")
LOGS_DIR = os.path.join(BASE_DIR, "logs")
PHASE_0_DIR = os.path.join(BASE_DIR, "01_Phase_0_Rule_Building")
SHARED_DIR = os.path.join(BASE_DIR, "Shared_Resources")

for directory in [OUTPUTS_BASE, LOGS_DIR]:
    if not os.path.exists(directory):
        os.makedirs(directory)

# --- Helper Functions ---

def get_table_dir(proj, ds, tbl):
    """Creates table-specific output directory."""
    path = os.path.join(OUTPUTS_BASE, f"{proj}_{ds}_{tbl}")
    os.makedirs(path, exist_ok=True)
    return path

def log_step(phase, table_name, message, details=None):
    """Logs timestamped execution steps."""
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = os.path.join(LOGS_DIR, f"{ts}_{phase}_{table_name}.log")
    
    time_str = datetime.now().strftime("%H:%M:%S")
    log_msg = f"[{time_str}] [{phase}] {message}"
    
    with open(log_file, "a", encoding="utf-8") as f:
        f.write(f"{log_msg}\n")
        if details:
            f.write(f"Details: {json.dumps(details, indent=2)}\n")
            
    try:
        from streamlit import session_state
        if 'system_logs' in session_state:
            session_state.system_logs.append(log_msg)
    except:
        pass

@st.cache_resource
def get_bq_service():
    return build('bigquery', 'v2', cache_discovery=False)

@st.cache_resource
def get_rm_service():
    return build('cloudresourcemanager', 'v1', cache_discovery=False)

def check_connectivity(proxy=None):
    """Checks connectivity to Google APIs with an optional proxy."""
    url = "https://www.googleapis.com/discovery/v1/apis"
    proxies = {"http": proxy, "https": proxy} if proxy else {"http": "", "https": ""}
    try:
        response = requests.get(url, proxies=proxies, timeout=5)
        return response.status_code == 200
    except:
        return False

def setup_environment():
    """Intelligent proxy detection and setup."""
    default_proxy = "http://proxy1234_akkuadhi:3128"
    
    if 'env_ready' not in st.session_state:
        # Try Direct first
        for var in ['HTTP_PROXY', 'HTTPS_PROXY', 'http_proxy', 'https_proxy']:
            os.environ.pop(var, None)
        
        if check_connectivity(None):
            st.session_state.proxy_mode = "Direct"
        elif check_connectivity(default_proxy):
            os.environ['HTTP_PROXY'] = os.environ['HTTPS_PROXY'] = default_proxy
            st.session_state.proxy_mode = "Default Proxy"
        else:
            st.session_state.proxy_mode = "Manual Required"
            
        try:
            creds, project = default()
            st.session_state.env_ready = True
            st.session_state.auth_status = "✅ Authenticated"
        except:
            st.session_state.env_ready = False
            st.session_state.auth_status = "❌ Auth Failed"

def build_catalog():
    """Discovery using Resource Manager API (Sequential for robustness in Hub)."""
    rm_service = get_rm_service()
    bq_service = get_bq_service()
    
    try:
        res = rm_service.projects().list().execute()
        projects = [p['projectId'] for p in res.get('projects', []) if p['lifecycleState'] == 'ACTIVE']
    except:
        return {}

    catalog = {}
    for pid in projects:
        try:
            ds_res = bq_service.datasets().list(projectId=pid).execute()
            datasets = [d['datasetReference']['datasetId'] for d in ds_res.get('datasets', [])]
            p_data = {}
            for ds in datasets:
                t_res = bq_service.tables().list(projectId=pid, datasetId=ds).execute()
                tables = [t['tableReference']['tableId'] for t in t_res.get('tables', [])]
                if tables: p_data[ds] = tables
            if p_data: catalog[pid] = p_data
        except:
            continue
    return catalog

def main():
    st.set_page_config(page_title="Dataplex Master Hub", layout="wide", page_icon="🚀")
    setup_environment()

    st.title("🚀 Dataplex Master Hub")
    
    with st.sidebar:
        st.header("⚙️ System Status")
        st.write(f"**Connection:** {st.session_state.get('proxy_mode', 'Unknown')}")
        st.write(f"**Auth:** {st.session_state.get('auth_status', 'Unknown')}")
        
        with st.expander("🌐 Manual Proxy Override"):
            url = st.text_input("Proxy URL")
            if st.button("Apply"):
                os.environ['HTTP_PROXY'] = os.environ['HTTPS_PROXY'] = url
                st.rerun()

    if not st.session_state.get('env_ready', False):
        st.error("GCP Environment not ready. Please run 'gcloud auth application-default login'.")
        return

    tabs = st.tabs(["📂 Build", "🔍 Discover", "✅ Verify", "🛠️ Generate"])

    # --- Phase 0: Build ---
    with tabs[0]:
        st.header("Phase 0: Rule Building")
        st.info("Launch the specialized Rule Builder for high-performance discovery and thresholding.")
        if st.button("🚀 Launch Specialized UI Builder"):
            subprocess.Popen(["streamlit", "run", os.path.join(PHASE_0_DIR, "ui_builder.py"), "--server.port", "8502"])
            st.success("Specialized UI launched on port 8502!")

    # --- Phase 1: Discover ---
    with tabs[1]:
        st.header("Phase 1: BigQuery Discovery")
        if 'catalog' not in st.session_state:
            if st.button("🔍 Run Resource Scan"):
                with st.spinner("Mapping projects and datasets..."):
                    st.session_state.catalog = build_catalog()
        
        if 'catalog' in st.session_state:
            cat = st.session_state.catalog
            sp = st.selectbox("Select Project", list(cat.keys()))
            
            c1, c2 = st.columns(2)
            with c1:
                sd = st.selectbox("Select Dataset", list(cat[sp].keys()) if sp else [])
            with c2:
                stbl = st.selectbox("Select Table", cat[sp][sd] if sp and sd else [])

            def extract_table_metadata(p, d, t):
                """Worker to fetch advanced metadata for a single table."""
                try:
                    service = get_bq_service()
                    table_res = service.tables().get(projectId=p, datasetId=d, tableId=t).execute()
                    
                    # 1. Basic Schema & Modes
                    fields = table_res.get('schema', {}).get('fields', [])
                    
                    # 2. Get Partitioning info
                    part_col = ""
                    if 'timePartitioning' in table_res:
                        part_col = table_res['timePartitioning'].get('field', '_PARTITIONTIME')
                    elif 'rangePartitioning' in table_res:
                        part_col = table_res['rangePartitioning'].get('field', '')

                    # 3. Get Clustering info
                    cluster_cols = table_res.get('clustering', {}).get('fields', [])

                    # 4. Get Constraints (PK/FK)
                    pk_cols = []
                    constraints = table_res.get('tableConstraints', {})
                    if 'primaryKey' in constraints:
                        pk_cols = constraints['primaryKey'].get('columns', [])
                    
                    fk_mapping = {} # col -> ref_table
                    for fk in constraints.get('foreignKeys', []):
                        ref = fk.get('referencedTable', {})
                        ref_str = f"{ref.get('datasetId')}.{ref.get('tableId')}"
                        for col in fk.get('columnReferences', []):
                            fk_mapping[col.get('referencingColumn')] = ref_str

                    # 5. Build enriched field list
                    metadata = []
                    for f in fields:
                        name = f['name']
                        metadata.append({
                            "Project": p, "Dataset": d, "Table": t,
                            "Column": name, "Type": f['type'], "Mode": f.get('mode', 'NULLABLE'),
                            "Is_PK": "YES" if name in pk_cols else "NO",
                            "Is_FK_To": fk_mapping.get(name, ""),
                            "Is_Partition_Col": "YES" if name == part_col else "NO",
                            "Is_Clustering_Col": "YES" if name in cluster_cols else "NO",
                            "Description": f.get('description', "")
                        })
                    return metadata
                except:
                    return []

            # Bulk Extraction Actions
            st.divider()
            b1, b2, b3 = st.columns(3)
            
            if 'last_extraction' not in st.session_state: st.session_state.last_extraction = None

            with b1:
                if st.button("📄 Extract Current Table"):
                    with st.spinner(f"Extracting {stbl}..."):
                        data = extract_table_metadata(sp, sd, stbl)
                        df = pd.DataFrame(data)
                        t_dir = get_table_dir(sp, sd, stbl)
                        df.to_csv(os.path.join(t_dir, "schema.csv"), index=False)
                        st.session_state.last_extraction = {"df": df, "msg": f"✅ Saved to {stbl}/schema.csv"}

            with b2:
                if st.button("📂 Extract All in Dataset"):
                    all_tables = cat[sp][sd]
                    with st.spinner(f"Extracting {len(all_tables)} tables..."):
                        all_metadata = []
                        with ThreadPoolExecutor(max_workers=10) as executor:
                            futures = [executor.submit(extract_table_metadata, sp, sd, t) for t in all_tables]
                            for f in as_completed(futures):
                                all_metadata.extend(f.result())
                        
                        df_meta = pd.DataFrame(all_metadata)
                        out_path = os.path.join(OUTPUTS_BASE, f"discovery_{sp}_{sd}.csv")
                        df_meta.to_csv(out_path, index=False)
                        st.session_state.last_extraction = {"df": df_meta, "msg": f"✅ Consolidated schema saved to: {out_path}"}

            with b3:
                if st.button("🏢 Extract All in Project"):
                    all_ds = cat[sp]
                    with st.spinner(f"Extracting entire project {sp}..."):
                        all_metadata = []
                        tasks = []
                        for d_name, t_list in all_ds.items():
                            for t_name in t_list:
                                tasks.append((sp, d_name, t_name))
                        
                        with ThreadPoolExecutor(max_workers=10) as executor:
                            futures = [executor.submit(extract_table_metadata, *t) for t in tasks]
                            for f in as_completed(futures):
                                all_metadata.extend(f.result())
                        
                        df_meta = pd.DataFrame(all_metadata)
                        out_path = os.path.join(OUTPUTS_BASE, f"discovery_{sp}_FULL.csv")
                        df_meta.to_csv(out_path, index=False)
                        st.session_state.last_extraction = {"df": df_meta, "msg": f"✅ Full project schema saved to: {out_path}"}

            # Display result full-width below columns
            if st.session_state.last_extraction:
                ext = st.session_state.last_extraction
                st.success(ext["msg"])
                st.subheader("Extraction Preview")
                st.dataframe(ext["df"], use_container_width=True)

    # --- Phase 2: Verify ---
    with tabs[2]:
        st.header("Phase 2: Metadata Verification")
        rf = st.file_uploader("Upload Rules CSV for Multithreaded Verification", type=["csv"])
        if rf:
            rdf = pd.read_csv(rf)
            st.dataframe(rdf)
            if st.button("🔍 Run Multithreaded Verification"):
                service = get_bq_service()
                results = [None] * len(rdf)
                
                def verify_rule(idx, row):
                    try:
                        p, d, t, c = row['Source_Project'], row['Source_Dataset'], row['Source_Table'], row['Column_Name']
                        res = service.tables().get(projectId=p, datasetId=d, tableId=t).execute()
                        bq_cols = [f['name'] for f in res.get('schema', {}).get('fields', [])]
                        if pd.isna(c) or not c or str(c).startswith("Columns with _d"):
                            return idx, "✅ OK"
                        return idx, ("✅ OK" if c in bq_cols else f"❌ Missing: {c}")
                    except Exception as e:
                        return idx, f"⚠️ Error: {str(e)[:50]}"

                with ThreadPoolExecutor(max_workers=10) as executor:
                    futures = [executor.submit(verify_rule, i, r) for i, r in rdf.iterrows()]
                    for f in as_completed(futures):
                        i, res = f.result()
                        results[i] = res
                
                rdf['Verification_Status'] = results
                st.session_state.rules_df = rdf
                st.table(rdf[['Source_Table', 'Column_Name', 'Verification_Status']])

    # --- Phase 3: Generate ---
    with tabs[3]:
        st.header("Phase 3: Config Generation")
        if st.session_state.get('rules_df') is not None:
            df = st.session_state.rules_df
            for (p, d, t), group in df.groupby(['Source_Project', 'Source_Dataset', 'Source_Table']):
                t_dir = get_table_dir(p, d, t)
                st.write(f"### Artifacts for {p}.{d}.{t}")
                
                # Build DQ YAML Spec
                rules = []
                for _, row in group.iterrows():
                    # Handle Expanded Schema (Range thresholds)
                    threshold_block = {}
                    if not pd.isna(row.get('Threshold')) and row['Threshold'] != "":
                        threshold_block = {"passingThreshold": float(row['Threshold'])}
                    elif not pd.isna(row.get('Lower_Threshold')):
                        threshold_block = {"range": {"min": row['Lower_Threshold'], "max": row['Upper_Threshold']}}

                    rule = {
                        "dimension": row['Dimension'],
                        "column": row['Column_Name'] if not str(row['Column_Name']).startswith("Columns with _d") else None,
                        "ruleType": row['Rule_Type'],
                        **threshold_block
                    }
                    rules.append(rule)
                
                yaml_obj = {"dataQualitySpec": {"rules": rules}}
                
                if st.button(f"Generate Artifacts for {t}", key=f"btn_{t}"):
                    # Save YAML
                    yaml_path = os.path.join(t_dir, "dq_spec.yaml")
                    with open(yaml_path, 'w') as f:
                        yaml.dump(yaml_obj, f, sort_keys=False)
                    
                    # Generate Batch CLI
                    batch_cmd = f"gcloud dataplex datascans create data-quality {row['Scan_ID']} " \
                                f"--location={row['Location']} --data-source-resource=//bigquery.googleapis.com/projects/{p}/datasets/{d}/tables/{t} " \
                                f"--data-quality-spec-file={yaml_path}"
                    with open(os.path.join(t_dir, "create_scan.sh"), 'w') as f:
                        f.write(batch_cmd)
                    
                    st.success(f"Artifacts generated in {t_dir}")
                    log_step("P3", t, "Generated Spec and Batch script")

    # --- System Execution Logs ---
    st.divider()
    with st.expander("📝 System Execution Logs", expanded=False):
        if st.session_state.get('system_logs'):
            st.code("\n".join(st.session_state.system_logs))
        else:
            st.text("No execution logs recorded yet.")

if __name__ == "__main__":
    main()
