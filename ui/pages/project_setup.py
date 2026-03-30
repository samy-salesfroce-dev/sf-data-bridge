import streamlit as st
import time
from database.db_handler import create_project, get_projects
from auth.salesforce_auth import authenticate

def render_page():
    st.header("1. Initialize Your Migration Project")
    st.markdown("Create a new mapping project and connect to your Source and Target Salesforce Orgs.")

    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("Manage Projects")
        projects = get_projects()
        
        project_names = ["-- Create New Project --"] + [p['name'] for p in projects]
        selected_project = st.selectbox("Select Project", project_names)
        
        if selected_project == "-- Create New Project --":
            with st.form("new_project_form"):
                proj_name = st.text_input("Project Name (e.g., 'CPQ_Sandy_to_Prod')")
                submitted = st.form_submit_button("Start Project")
                if submitted and proj_name:
                    pid = create_project(proj_name, "", "", "", "")
                    if pid:
                        st.success(f"Project '{proj_name}' created!")
                        st.session_state.current_project_id = pid
                        st.session_state.current_project_name = proj_name
                        time.sleep(1)
                        st.rerun()
                    else:
                        st.error("Project name already exists.")
        else:
            # Active Project
            proj = next(p for p in projects if p['name'] == selected_project)
            st.session_state.current_project_id = proj['id']
            st.session_state.current_project_name = proj['name']
            
            st.info(f"Active Project: **{proj['name']}**")

    with col2:
        st.subheader("Authentications")
        if getattr(st.session_state, 'current_project_id', None):
            with st.expander("Source Org Credentials", expanded=not st.session_state.source_sf):
                src_usr = st.text_input("Source Username", key="src_usr")
                src_pwd = st.text_input("Source Password", type="password", key="src_pwd")
                src_tok = st.text_input("Source Security Token", type="password", key="src_tok")
                src_dom = st.selectbox("Source Env", ["login", "test"], key="src_dom")
                
                if st.button("Connect Source", key="btn_src"):
                    with st.spinner("Authenticating Source..."):
                        sf, err = authenticate(src_usr, src_pwd, src_tok, src_dom)
                        if sf:
                            st.session_state.source_sf = sf
                            st.success("Successfully logged into Source Org!")
                        else:
                            st.error(f"Auth Failed: {err}")

            with st.expander("Target Org Credentials", expanded=not st.session_state.target_sf):
                tgt_usr = st.text_input("Target Username", key="tgt_usr")
                tgt_pwd = st.text_input("Target Password", type="password", key="tgt_pwd")
                tgt_tok = st.text_input("Target Security Token", type="password", key="tgt_tok")
                tgt_dom = st.selectbox("Target Env", ["login", "test"], key="tgt_dom")
                
                if st.button("Connect Target", key="btn_tgt"):
                    with st.spinner("Authenticating Target..."):
                        sf, err = authenticate(tgt_usr, tgt_pwd, tgt_tok, tgt_dom)
                        if sf:
                            st.session_state.target_sf = sf
                            st.success("Successfully logged into Target Org!")
                        else:
                            st.error(f"Auth Failed: {err}")
                            
            if st.session_state.source_sf and st.session_state.target_sf:
                st.balloons()
                st.success("Ready for Metadata Diff!")
        else:
            st.warning("Please select or create a project first.")
