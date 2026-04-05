import streamlit as st
import pandas as pd
from core.metadata_engine import compare_schemas, deploy_external_id_field, deploy_selected_metadata
from database.db_handler import add_project_object

def render_page():
    st.header("2. Metadata & Schema Diff")
    st.markdown("Compare Source and Target object schemas to identify missing fields and type mismatches.")

    if not st.session_state.source_sf or not st.session_state.target_sf:
        st.warning("Please connect to both Source and Target Orgs in 'Project Setup & Auth'.")
        return

    # Add objects to Project
    st.subheader("Select Objects for Migration")
    
    with st.spinner("Fetching Global Metadata..."):
        if 'global_objects' not in st.session_state:
            global_describe = st.session_state.source_sf.describe()
            st.session_state.global_objects = sorted([obj['name'] for obj in global_describe['sobjects']])
            
    all_objects = st.session_state.global_objects
    custom_objects = [obj for obj in all_objects if obj.endswith('__c')]
    
    col1, col2 = st.columns(2)
    with col1:
        if st.button("Select All Custom Objects"):
            st.session_state.obj_selection = custom_objects
    with col2:
        if st.button("Clear Selection"):
            st.session_state.obj_selection = []
            
    if 'obj_selection' not in st.session_state:
        st.session_state.obj_selection = []
        
    selected_objects = st.multiselect("Select Objects", options=all_objects, key="obj_selection")
    
    if st.button("Add Checked Objects to Project"):
        if selected_objects:
            for obj in selected_objects:
                add_project_object(st.session_state.current_project_id, obj)
            st.success(f"Added {len(selected_objects)} objects to project!")
            st.session_state.selected_objects = selected_objects
        else:
            st.warning("Please select at least one object.")
    
    # Run Schema Diff
    if hasattr(st.session_state, 'selected_objects'):
        if st.button("Run Schema Diff"):
            with st.spinner("Analyzing Describe Metadata..."):
                diff_df = compare_schemas(st.session_state.source_sf, st.session_state.target_sf, st.session_state.selected_objects)
                st.session_state.diff_df = diff_df
        
        if 'diff_df' in st.session_state:
            if st.session_state.diff_df.empty:
                st.success("Schemas match perfectly! You are Ready to Migrate.")
            else:
                st.warning(f"Found {len(st.session_state.diff_df)} differences. Select components to deploy.")
                
                # Interactive Deployment Table
                edited_df = st.data_editor(
                    st.session_state.diff_df,
                    column_config={
                        "Deploy": st.column_config.CheckboxColumn(
                            "Deploy?",
                            help="Select to deploy this metadata component",
                            default=False,
                        ),
                        "Is_Custom": st.column_config.CheckboxColumn(
                            "Custom?",
                            disabled=True
                        )
                    },
                    disabled=["Object", "Field Name", "Label", "Type", "Length", "Status", "Is_Custom"],
                    hide_index=True,
                    width='stretch',
                    key="metadata_editor"
                )
                
                if st.button("Deploy Selected Metadata"):
                    selected_rows = edited_df[edited_df["Deploy"] == True].to_dict('records')
                    if not selected_rows:
                        st.warning("Please select at least one component to deploy.")
                    else:
                        with st.spinner("Deploying via Tooling API..."):
                            success_count, errors = deploy_selected_metadata(
                                st.session_state.source_sf, 
                                st.session_state.target_sf, 
                                selected_rows
                            )
                            
                            if success_count > 0:
                                st.success(f"Successfully deployed {success_count} components!")
                                # Clear the diff state to force a re-run
                                del st.session_state.diff_df
                                st.info("Deployment successful! NOTE: Salesforce's API Cache can take 30-60 seconds to reflect new fields. If you run 'Schema Diff' immediately and the field still appears 'missing', please wait one minute and try again.")
                                st.rerun()
                            
                            if errors:
                                for err in errors:
                                    st.error(err)

        st.markdown("---")
        st.subheader("Universal Hierarchical Strategy")
        st.markdown("We rely on a custom External ID (`Migration_External_ID__c`) to enforce relationship linking via Bulk API 2.0. Click below to deploy this field to your Target org for the selected objects.")
        
        if st.button("Deploy External ID Fields"):
            with st.spinner("Deploying Metadata..."):
                for obj in st.session_state.selected_objects:
                    success, err = deploy_external_id_field(st.session_state.target_sf, obj)
                    if success:
                        st.success(f"Successfully deployed `Migration_External_ID__c` to {obj}")
                    else:
                        st.error(f"Failed to deploy to {obj}: {err}")
