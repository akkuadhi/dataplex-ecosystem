"""
High-Performance Dataplex Rule Builder UI.
- Uses Resource Manager & Discovery APIs for optimized resource discovery.
- Implements project-level and table-level IAM filtering (Read/Write).
- Parallelized discovery with real-time logging.
"""

import os
import streamlit as st
import pandas as pd
from googleapiclient.discovery import build
from google.auth import default
from concurrent.futures import ThreadPoolExecutor, as_completed
from streamlit.runtime.scriptrunner import add_script_run_ctx

# --- Page Configuration ---
st.set_page_config(page_title="Dataplex Rule Builder", layout="wide", page_icon="🛠️")

def setup_environment():
    """Ensures environment is ready for discovery."""
    if 'env_ready' not in st.session_state:
        # Purge all proxy env vars to ensure Direct connection
        for var in ['HTTP_PROXY', 'HTTPS_PROXY', 'http_proxy', 'https_proxy']:
            os.environ.pop(var, None)
        
        try:
            creds, project = default()
            st.session_state.env_ready = True
            st.session_state.auth_status = "✅ Authenticated"
        except Exception as e:
            st.session_state.env_ready = False
            st.session_state.auth_status = f"❌ Auth Failed: {str(e)[:50]}"

def manual_proxy_ui():
    """Optional manual proxy override."""
    with st.sidebar.expander("🌐 Manual Network Settings"):
        url = st.text_input("Proxy URL (e.g. http://host:port)")
        if st.button("Apply Proxy"):
            if url:
                os.environ['HTTP_PROXY'] = os.environ['HTTPS_PROXY'] = url
            else:
                for var in ['HTTP_PROXY', 'HTTPS_PROXY', 'http_proxy', 'https_proxy']:
                    os.environ.pop(var, None)
            
            if 'catalog' in st.session_state: del st.session_state.catalog
            st.rerun()

@st.cache_resource
def get_bq_service():
    return build('bigquery', 'v2', cache_discovery=False)

@st.cache_resource
def get_rm_service():
    return build('cloudresourcemanager', 'v1', cache_discovery=False)

def check_table_access(project_id, dataset_id, table_id, bq_service):
    """Checks for Read/Write/Update permissions on a specific table."""
    perms = ["bigquery.tables.getData", "bigquery.tables.update", "bigquery.tables.updateData"]
    try:
        res = bq_service.tables().testIamPermissions(
            projectId=project_id, datasetId=dataset_id, tableId=table_id,
            body={"permissions": perms}
        ).execute()
        return all(p in res.get('permissions', []) for p in perms)
    except:
        return False

def build_full_catalog():
    """Discovery with project-level fast path and table-level precision."""
    if 'debug_log' not in st.session_state: st.session_state.debug_log = []
    
    with st.sidebar.expander("🐞 Live Discovery Log", expanded=False):
        log_placeholder = st.empty()
    
    def log_ui(msg):
        st.session_state.debug_log.append(msg)
        # Keep only the last 20 lines to prevent UI lag during intense scanning
        log_placeholder.code("\n".join(st.session_state.debug_log[-20:]))
        print(msg)

    log_ui("🚀 Starting parallel discovery...")
    
    try:
        rm_service = get_rm_service()
        res = rm_service.projects().list().execute()
        projects = [p['projectId'] for p in res.get('projects', []) if p['lifecycleState'] == 'ACTIVE']
    except Exception as e:
        log_ui("📡 RM API failed, trying BQ fallback...")
        try:
            bq_service = get_bq_service()
            res = bq_service.projects().list().execute()
            projects = [p['projectReference']['projectId'] for p in res.get('projects', [])]
        except:
            log_ui(f"❌ Project discovery failed: {e}")
            return {}

    if not projects:
        return {}

    full_catalog = {}
    bq_service = get_bq_service()
    rm_service = get_rm_service()
    
    # Permissions required
    rw_perms = ["bigquery.tables.getData", "bigquery.tables.update", "bigquery.tables.updateData"]

    for pid in projects:
        log_ui(f"🔭 Checking {pid}...")
        
        # 1. Project-level fast path
        try:
            p_iam = rm_service.projects().testIamPermissions(resource=pid, body={"permissions": rw_perms}).execute()
            has_project_rw = all(p in p_iam.get('permissions', []) for p in rw_perms)
        except:
            has_project_rw = False
        
        if has_project_rw:
            log_ui(f"  ✅ {pid}: Full project access detected.")
        
        # 2. List datasets
        try:
            ds_res = bq_service.datasets().list(projectId=pid).execute()
            datasets = [d['datasetReference']['datasetId'] for d in ds_res.get('datasets', [])]
            
            p_catalog = {}
            for ds in datasets:
                # 3. List tables
                t_res = bq_service.tables().list(projectId=pid, datasetId=ds).execute()
                all_tables = [t['tableReference']['tableId'] for t in t_res.get('tables', [])]
                
                if not all_tables:
                    continue
                
                if has_project_rw:
                    p_catalog[ds] = all_tables
                    log_ui(f"    ✅ {ds}: {len(all_tables)} tables added.")
                else:
                    # 4. Granular table check (Parallelized per dataset)
                    valid_tables = []
                    with ThreadPoolExecutor(max_workers=10) as executor:
                        futures = {executor.submit(check_table_access, pid, ds, tid, bq_service): tid for tid in all_tables}
                        for future in as_completed(futures):
                            tid = futures[future]
                            if future.result():
                                valid_tables.append(tid)
                    
                    if valid_tables:
                        p_catalog[ds] = valid_tables
                        log_ui(f"    ✅ {ds}: {len(valid_tables)} tables (fine-grained R/W)")
                    else:
                        log_ui(f"    ⚠️ {ds}: 0 tables with R/W access.")
            
            if p_catalog:
                full_catalog[pid] = p_catalog
                
        except Exception as e:
            log_ui(f"  ❌ Error scanning {pid}: {e}")
            
    return full_catalog

def get_table_schema(project_id, dataset_id, table_id):
    """Fetches table schema details using the Discovery API."""
    service = get_bq_service()
    try:
        res = service.tables().get(projectId=project_id, datasetId=dataset_id, tableId=table_id).execute()
        return [f['name'] for f in res.get('schema', {}).get('fields', [])]
    except Exception as e:
        st.error(f"Error fetching schema: {e}")
        return []

def main():
    st.title("🛠️ Dataplex Rule Builder")
    setup_environment()
    manual_proxy_ui()

    st.sidebar.write(f"**Auth Status:** {st.session_state.get('auth_status', 'Unknown')}")
    
    if not st.session_state.get('env_ready', False):
        st.error("Authentication failed. Please run 'gcloud auth application-default login' in your terminal.")
        return

    # --- Initial Discovery ---
    if 'catalog' not in st.session_state:
        st.session_state.debug_log = []
        with st.spinner("🔍 Discovering BigQuery Resources..."):
            cat = build_full_catalog()
            if not cat:
                st.warning("No accessible resources found with R/W permissions.")
                if st.button("🔄 Retry Scan"):
                    st.rerun()
                return
            st.session_state.catalog = cat
    
    catalog = st.session_state.catalog
    
    with st.sidebar.expander("📝 Full Discovery History", expanded=False):
        for log in st.session_state.get('debug_log', []):
            st.text(log)

    if 'rules' not in st.session_state: st.session_state.rules = []

    # --- Rule Management ---
    st.header("📂 Rule Management")
    uploaded_file = st.file_uploader("Import existing Rules CSV", type="csv")
    if uploaded_file:
        df_imported = pd.read_csv(uploaded_file)
        if st.button("Append Imported Rules"):
            st.session_state.rules.extend(df_imported.to_dict('records'))
            st.success(f"Imported {len(df_imported)} rules.")

    st.header("1. Build New Rule")
    c1, c2 = st.columns(2)
    
    with c1:
        st.subheader("Source Data")
        sp = st.selectbox("Project", list(catalog.keys()), key="src_p")
        sd = st.selectbox("Dataset", list(catalog[sp].keys()) if sp else [], key="src_d")
        stbl = st.selectbox("Table", catalog[sp][sd] if sp and sd else [], key="src_t")
        cols = get_table_schema(sp, sd, stbl) if stbl else []
    
    with c2:
        st.subheader("Historic Data (Optional)")
        use_hist = st.checkbox("Enable historic comparison?")
        hp = hd = ht = ""
        if use_hist:
            hp = st.selectbox("Historic Project", list(catalog.keys()), key="hist_p")
            hd = st.selectbox("Historic Dataset", list(catalog[hp].keys()) if hp else [], key="hist_d")
            ht = st.selectbox("Historic Table", catalog[hp][hd] if hp and hd else [], key="hist_t")

    # Use a container instead of a form for real-time reactivity
    with st.container(border=True):
        f1, f2, f3 = st.columns(3)
        with f1:
            tc_options = ["(Table Level)", "Derived Attributes"] + cols
            tc = st.selectbox("Target Column", tc_options)
            
            # Handle Derived Attributes input
            final_col_name = ""
            if tc == "(Table Level)":
                final_col_name = ""
            elif tc == "Derived Attributes":
                final_col_name = st.text_input("Attribute Name", value="Columns with _d or _d_(case insenstive) in their names")
            else:
                final_col_name = tc

            dim = st.selectbox("Dimension", ["COMPLETENESS", "UNIQUENESS", "VALIDITY", "TIMELINESS", "ACCURACY", "VOLUME", "CONSISTENCY"])
            rtype = st.selectbox("Rule Type", ["NonNull", "Uniqueness", "Range", "Set", "Regex", "SqlAssertion"])
        with f2:
            logic = st.text_area("Rule Logic (English description)")
            email = st.text_input("Notification Email")
        with f3:
            t_type = st.radio("Threshold Type", ["Single", "Range"], horizontal=True)
            if t_type == "Single":
                thresh = st.number_input("Threshold (0.0 - 1.0)", 0.0, 1.0, 1.0)
                l_thresh = u_thresh = ""
            else:
                thresh = ""
                l_thresh = st.number_input("Lower Threshold", value=0.0)
                u_thresh = st.number_input("Upper Threshold", value=1.0)
            inull = st.checkbox("Ignore Nulls", value=False)
        
        if st.button("➕ Add Rule to List", type="primary"):
            if not logic:
                st.error("Please provide a description of the rule logic.")
            elif tc == "Derived Attributes" and not final_col_name:
                st.error("Please provide a name for the Derived Attribute.")
            else:
                st.session_state.rules.append({
                    "Source_Project": sp, "Source_Dataset": sd, "Source_Table": stbl,
                    "Historic_Project": hp, "Historic_Dataset": hd, "Historic_Table": ht,
                    "Location": "us-central1", "Scan_ID": f"{stbl}-dq", "Display_Name": f"{stbl.capitalize()} Quality Scan", 
                    "Scan_Description": f"DQ Scan for {stbl}", "Schedule_Cron": "0 0 * * *", 
                    "Incremental_Field": "", "Labels": "env=prod", "Sampling_Percent": 100, "Row_Filter": "",
                    "Column_Name": final_col_name,
                    "Dimension": dim, "Rule_Type": rtype, "Rule_Logic": logic,
                    "Threshold": thresh, "Lower_Threshold": l_thresh, "Upper_Threshold": u_thresh,
                    "Ignore_Null": str(inull).upper(), "Notification_Email": email
                })
                st.success(f"Rule added for {final_col_name if final_col_name else stbl}!")
                st.rerun()

    # --- 2. Review & Live Verification ---
    if st.session_state.rules:
        st.header("2. Review & Live Verification")
        df = pd.DataFrame(st.session_state.rules)
        
        if st.button("🔍 Verify Rules Against BigQuery"):
            service = get_bq_service()
            results = [None] * len(df)
            
            def verify_rule(idx, row):
                try:
                    p, d, t, c = row['Source_Project'], row['Source_Dataset'], row['Source_Table'], row['Column_Name']
                    res = service.tables().get(projectId=p, datasetId=d, tableId=t).execute()
                    bq_cols = [f['name'] for f in res.get('schema', {}).get('fields', [])]
                    if pd.isna(c) or not c or str(c).startswith("Columns with _d"):
                        status = "✅ Column/Table Valid"
                    elif c in bq_cols:
                        status = "✅ Column Valid"
                    else:
                        status = f"❌ Missing Column: {c}"
                    return idx, status
                except Exception as e:
                    return idx, f"⚠️ API Error: {str(e)}"
                    
            with ThreadPoolExecutor(max_workers=10) as executor:
                futures = []
                for idx, row in df.iterrows():
                    f = executor.submit(verify_rule, idx, row)
                    add_script_run_ctx(f)
                    futures.append(f)
                    
                for future in as_completed(futures):
                    try:
                        i, status = future.result()
                        results[i] = status
                    except Exception as e:
                        pass
                        
            df['Verification_Status'] = results
            st.session_state.rules = df.to_dict('records')

        
        st.dataframe(df)
        
        b1, b2 = st.columns(2)
        with b1:
            if st.button("🗑️ Clear All Rules"):
                st.session_state.rules = []
                st.rerun()
        with b2:
            if st.button("💾 Save Verified Rules to CSV"):
                save_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "Shared_Resources")
                pd.DataFrame(st.session_state.rules).to_csv(os.path.join(save_dir, "final_rules.csv"), index=False)
                st.success(f"Saved to Shared_Resources/final_rules.csv")

if __name__ == "__main__":
    main()
