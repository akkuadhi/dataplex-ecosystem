"""
Interactive Dataplex Rule Builder UI.
Fetches real-time BigQuery schemas and exports rules to a structured CSV.
"""

import os
import streamlit as st
import pandas as pd
from google.cloud import bigquery

st.set_page_config(page_title="Dataplex Rule Builder", layout="wide", page_icon="🛠️")

def setup_proxy():
    """Proxy config Sidebar."""
    if not st.session_state.get('proxy_done', False):
        with st.sidebar.expander("🌐 Proxy Settings", expanded=True):
            url = st.text_input("Proxy URL (host:port)")
            if st.button("Apply"):
                os.environ['HTTP_PROXY'] = os.environ['HTTPS_PROXY'] = f"http://{url}"
                st.session_state.proxy_done = True
                st.success("Proxy Applied")

def main():
    """Main UI Logic."""
    st.title("🛠️ Dataplex Rule Builder")
    setup_proxy()
    
    if not st.session_state.get('proxy_done', False):
        st.warning("Please configure proxy in sidebar.")
        return

    try:
        client = bigquery.Client()
    except Exception as e:
        st.error(f"BQ Client Error: {e}")
        return

    if 'rules' not in st.session_state: st.session_state.rules = []

    st.header("1. Data Sources")
    c1, c2 = st.columns(2)
    with c1:
        sp = st.selectbox("Source Project", [p.project_id for p in client.list_projects()])
        sd = st.selectbox("Source Dataset", [d.dataset_id for d in client.list_datasets(project=sp)])
        stbl = st.selectbox("Source Table", [t.table_id for t in client.list_tables(f"{sp}.{sd}")])
        cols = [f.name for f in client.get_table(f"{sp}.{sd}.{stbl}").schema]

    st.header("2. Rule Definition")
    with st.form("rule_form", clear_on_submit=True):
        f1, f2, f3 = st.columns(3)
        with f1:
            tc = st.selectbox("Target Column", ["(Table)"] + cols)
            dim = st.selectbox("Dimension", ["COMPLETENESS", "UNIQUENESS", "VALIDITY", "TIMELINESS", "ACCURACY", "VOLUME"])
        with f2:
            logic = st.text_area("Rule Logic")
            rtype = st.selectbox("Rule Type", ["NonNull", "Uniqueness", "SqlAssertion"])
        with f3:
            sid = st.text_input("Scan ID", value=f"{stbl}-dq")
            email = st.text_input("Notification Email")
        
        if st.form_submit_button("➕ Add Rule"):
            st.session_state.rules.append({
                "Source_Project": sp, "Source_Dataset": sd, "Source_Table": stbl,
                "Scan_ID": sid, "Column_Name": tc if tc != "(Table)" else "",
                "Dimension": dim, "Rule_Type": rtype, "Rule_Logic": logic,
                "Notification_Email": email, "Sampling_Percent": 100, "Row_Filter": "",
                "Threshold": 1.0, "Ignore_Null": "FALSE", "Location": "us-central1", "Schedule_Cron": "0 0 * * *",
                "Incremental_Field": "", "Historic_Project": "", "Historic_Dataset": "", "Historic_Table": "", "Labels": "env=prod"
            })
            st.success(f"Added rule for {tc}")

    if st.session_state.rules:
        st.header("3. Review & Export")
        df = pd.DataFrame(st.session_state.rules)
        st.dataframe(df)
        if st.button("💾 Save to Shared Resources"):
            save_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "Shared_Resources")
            df.to_csv(os.path.join(save_dir, "final_rules.csv"), index=False)
            st.success("Rules saved to Shared_Resources/final_rules.csv")

if __name__ == "__main__":
    main()
