"""
Dataplex Master Orchestrator (Hub).

Consolidates the 4-phase pipeline (Build, Discover, Verify, Generate)
into a single interactve interface with unified logging and organization.
"""

import os
import json
import subprocess
from datetime import datetime
import streamlit as st
import pandas as pd
import yaml
from google.cloud import bigquery

# --- Page Config ---
st.set_page_config(page_title="Dataplex Master Hub", layout="wide", page_icon="🚀")

# --- Dynamic Pathing ---
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUTPUTS_BASE = os.path.join(BASE_DIR, "outputs")
LOGS_DIR = os.path.join(BASE_DIR, "logs")
PHASE_0_DIR = os.path.join(BASE_DIR, "01_Phase_0_Rule_Building")

for directory in [OUTPUTS_BASE, LOGS_DIR]:
    if not os.path.exists(directory):
        os.makedirs(directory)

def get_table_dir(proj, ds, tbl):
    """Creates table-specific output directory."""
    path = os.path.join(OUTPUTS_BASE, f"{proj}_{ds}_{tbl}")
    os.makedirs(path, exist_ok=True)
    return path

def log_step(phase, table_name, message, details=None):
    """Logs timestamped execution steps."""
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = os.path.join(LOGS_DIR, f"{ts}_{phase}_{table_name}.log")
    with open(log_file, "a", encoding="utf-8") as f:
        f.write(f"[{datetime.now()}] {message}\n")
        if details:
            f.write(f"Details: {json.dumps(details, indent=2)}\n")

# --- Global Style ---
st.markdown("<style>.stButton>button { width: 100%; height: 3em; background-color: #007bff; color: white; }</style>", unsafe_allow_html=True)

# --- Shared State ---
if 'proxy_configured' not in st.session_state: st.session_state.proxy_configured = False
if 'rules_df' not in st.session_state: st.session_state.rules_df = None

st.title("🚀 Dataplex Master Hub")
st.sidebar.header("⚙️ System Config")

# --- Proxy Sidebar ---
with st.sidebar.expander("🌐 Proxy Settings", expanded=not st.session_state.proxy_configured):
    proxy_url = st.text_input("Proxy Host:Port", placeholder="proxy.co.com:8080")
    if st.checkbox("Custom Proxy Credentials?"):
        p_user, p_pass = st.text_input("User"), st.text_input("Pass", type="password")
        p_str = f"http://{p_user}:{p_pass}@{proxy_url}"
    else:
        p_str = f"http://{proxy_url}"
    
    if st.button("Apply Proxy") and proxy_url:
        os.environ['HTTP_PROXY'] = os.environ['HTTPS_PROXY'] = p_str
        st.session_state.proxy_configured = True
        log_step("Setup", "Global", f"Proxy set: {proxy_url}")
        st.success("Proxy Applied")

# --- Tabs ---
tabs = st.tabs(["📂 Build", "🔍 Discover", "✅ Verify", "🛠️ Generate"])

# Phase 0: Build
with tabs[0]:
    st.header("Phase 0: Rule Building")
    c1, c2 = st.columns(2)
    with c1:
        if st.button("Launch UI Builder"):
            subprocess.Popen(["streamlit", "run", os.path.join(PHASE_0_DIR, "ui_builder.py")])
    with c2:
        st.code(f"python \"{os.path.join(PHASE_0_DIR, 'cli_builder.py')}\"")

# Phase 1: Discover
with tabs[1]:
    st.header("Phase 1: BigQuery Schema Discovery")
    if st.button("Load Projects"):
        try:
            st.session_state.projects = [p.project_id for p in bigquery.Client().list_projects()]
        except Exception as e: st.error(f"BQ Error: {e}")
    if 'projects' in st.session_state:
        tp = st.selectbox("Project", st.session_state.projects)
        td = st.selectbox("Dataset", [d.dataset_id for d in bigquery.Client().list_datasets(project=tp)])
        tt = st.selectbox("Table", [t.table_id for t in bigquery.Client().list_tables(f"{tp}.{td}")])
        if st.button("Extract Schema"):
            schema = [{"Name": f.name, "Type": f.field_type} for f in bigquery.Client().get_table(f"{tp}.{td}.{tt}").schema]
            t_dir = get_table_dir(tp, td, tt)
            with open(os.path.join(t_dir, "schema.json"), 'w') as f: json.dump(schema, f, indent=2)
            st.dataframe(pd.DataFrame(schema))
            log_step("P1", tt, f"Fetched schema {tp}.{td}.{tt}")

# Phase 2: Verify
with tabs[2]:
    st.header("Phase 2: Metadata Verification")
    rf = st.file_uploader("Rules CSV", type=["csv"])
    if rf:
        rdf = pd.read_csv(rf)
        ms = []
        client = bigquery.Client()
        for _, row in rdf[['Source_Project', 'Source_Dataset', 'Source_Table']].drop_duplicates().iterrows():
            ref = f"{row['Source_Project']}.{row['Source_Dataset']}.{row['Source_Table']}"
            bq_cols = [f.name for f in client.get_table(ref).schema]
            t_rules = rdf[(rdf['Source_Table'] == row['Source_Table'])]
            for rc in t_rules['Column_Name'].dropna().unique():
                status = "✅ OK" if rc in bq_cols else "❌ Missing"
                ms.append({"Table": row['Source_Table'], "Rule Column": rc, "Status": status})
        st.table(pd.DataFrame(ms))
        if st.button("Confirm Verification"):
            st.session_state.rules_df = rdf
            st.success("Verification complete.")

# Phase 3: Generate
with tabs[3]:
    st.header("Phase 3: Config Generation")
    if st.session_state.rules_df is not None:
        for tid, group in st.session_state.rules_df.groupby(['Source_Project', 'Source_Dataset', 'Source_Table']):
            p, d, t = tid
            t_dir = get_table_dir(p, d, t)
            st.write(f"### Table: {p}.{d}.{t}")
            yaml_obj = {"description": f"DQ {t}", "dataQualitySpec": {"rules": []}}
            for idx, row in group.iterrows():
                st.info(f"🧠 **Understanding:** {row['Rule_Logic']}")
                rule = {"dimension": row['Dimension'], "column": row['Column_Name']}
                if row['Rule_Type'] == "SqlAssertion":
                    sql = st.text_input(f"SQL for {idx}", value="SELECT ...", key=f"sql_{tid}_{idx}")
                    rule["sqlAssertionExpectation"] = {"sqlStatement": sql}
                yaml_obj["dataQualitySpec"]["rules"].append(rule)
            if st.button(f"Generate {t}", key=f"gen_{t}"):
                with open(os.path.join(t_dir, "dq_spec.yaml"), 'w') as f: yaml.dump(yaml_obj, f)
                log_step("P3", t, "Generated Config")
                st.success(f"Saved to {t_dir}")

if __name__ == "__main__":
    main()
