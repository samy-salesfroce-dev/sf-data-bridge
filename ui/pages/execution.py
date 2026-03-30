import streamlit as st
import pandas as pd
from core.data_engine import execute_migration

def render_page():
    st.header("4. Execution & Audit")
    st.markdown("Run the migration and view the audit report.")

    if not st.session_state.source_sf or not st.session_state.target_sf:
        st.warning("Please connect to both Source and Target Orgs first.")
        return

    st.subheader("Migration Settings")
    dry_run = st.toggle("Dry Run (Limit 50 records per object)", value=True, help="Limits queries to 50 records and maintains hierarchy for testing before full scale deployment.")
    
    st.markdown("---")
    
    log_container = st.empty()
    progress_bar = st.progress(0)
    
    if st.button("Start Migration Engine", type="primary"):
        st.session_state.logs = []
        
        def log_cb(msg):
            st.session_state.logs.append(msg)
            log_container.code("\n".join(st.session_state.logs))
            
        def prog_cb(pct):
            progress_bar.progress(pct)

        with st.spinner("Executing Universal Data Engine..."):
            audit_df = execute_migration(
                st.session_state.source_sf,
                st.session_state.target_sf,
                st.session_state.current_project_id,
                dry_run=dry_run,
                progress_cb=prog_cb,
                log_cb=log_cb
            )
            
        st.success("Migration Process Concluded!")
        
        st.markdown("### Migration Audit Report")
        if not audit_df.empty:
            st.dataframe(audit_df, use_container_width=True)
            
            # Interactive HTML rendering or CSV download
            csv = audit_df.to_csv(index=False).encode('utf-8')
            st.download_button(
                "Download Audit Report (CSV)",
                csv,
                "migration_audit_report.csv",
                "text/csv",
                key='download-csv'
            )
        else:
            st.info("No audit data generated. Check logs above.")
