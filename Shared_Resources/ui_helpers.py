
import streamlit as st
import os
import sys
from Shared_Resources.networking import setup_environment_logic

def render_system_sidebar():
    """Renders a consistent system status and proxy override sidebar."""
    with st.sidebar:
        st.header("⚙️ System Status")
        st.write(f"**Connection:** {st.session_state.get('proxy_mode', 'Unknown')}")
        st.write(f"**Auth:** {st.session_state.get('auth_status', 'Unknown')}")
        
        with st.expander("🌐 Manual Proxy Override"):
            url = st.text_input("Proxy URL (e.g. http://host:port)", key="manual_proxy_url")
            if st.button("Apply Settings", key="apply_proxy_btn"):
                if url:
                    os.environ['HTTP_PROXY'] = os.environ['HTTPS_PROXY'] = url
                    st.session_state.manual_proxy_active = True
                else:
                    for var in ['HTTP_PROXY', 'HTTPS_PROXY', 'http_proxy', 'https_proxy']:
                        os.environ.pop(var, None)
                    st.session_state.manual_proxy_active = False
                
                # Force re-verification
                if 'env_ready' in st.session_state: del st.session_state.env_ready
                if 'catalog' in st.session_state: del st.session_state.catalog
                st.cache_resource.clear()
                st.rerun()

def render_execution_logs():
    """Renders a consistent execution log expander at the bottom of the page."""
    st.divider()
    with st.expander("📝 System Execution Logs", expanded=False):
        # Merge system_logs and debug_log if both exist
        logs = st.session_state.get('system_logs', [])
        debug_logs = st.session_state.get('debug_log', [])
        
        all_logs = logs + debug_logs
        if all_logs:
            st.code("\n".join(all_logs))
        else:
            st.text("No execution logs recorded yet.")

def log_message(msg, level="INFO"):
    """Standardized logging to session state."""
    if 'system_logs' not in st.session_state:
        st.session_state.system_logs = []
    
    from datetime import datetime
    ts = datetime.now().strftime("%H:%M:%S")
    formatted_msg = f"[{ts}] [{level}] {msg}"
    st.session_state.system_logs.append(formatted_msg)
    print(formatted_msg)
