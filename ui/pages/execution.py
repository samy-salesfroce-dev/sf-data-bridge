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
        
        if not audit_df.empty:
            st.markdown("### 📊 Migration Summary")
            col1, col2, col3 = st.columns(3)
            total = len(audit_df)
            successes = len(audit_df[audit_df['Status'] == 'Success'])
            errors = len(audit_df[audit_df['Status'] == 'Error'])
            
            col1.metric("Total Records", total)
            col2.metric("Success ✅", successes)
            col3.metric("Errors ❌", errors, delta=-errors if errors > 0 else 0, delta_color="inverse")
            
            st.markdown("---")
            st.markdown("### 🔍 Detailed Audit Log")
            
            # Filter options
            view_mode = st.radio("View records:", ["All", "Errors Only", "Success Only"], horizontal=True)
            if view_mode == "Errors Only":
                display_df = audit_df[audit_df['Status'] == 'Error']
            elif view_mode == "Success Only":
                display_df = audit_df[audit_df['Status'] == 'Success']
            else:
                display_df = audit_df
                
            st.dataframe(display_df, use_container_width=True)
            
            # CSV download
            csv = audit_df.to_csv(index=False).encode('utf-8')
            st.download_button(
                "📥 Download Full Audit Report (CSV)",
                csv,
                "migration_audit_report.csv",
                "text/csv",
                key='download-csv'
            )
        else:
            st.info("No audit data generated. Check logs above.")
