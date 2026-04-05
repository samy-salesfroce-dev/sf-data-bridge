import streamlit as st
import pandas as pd
from core.metadata_engine import compare_schemas, deploy_external_id_field, deploy_selected_metadata, get_external_id_candidates
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
                            results = deploy_selected_metadata(
                                st.session_state.source_sf, 
                                st.session_state.target_sf, 
                                selected_rows
                            )
                            st.session_state.deployment_results = results
                            
                            # Calculate stats
                            successes = len([r for r in results if r['Status'] == 'Success'])
                            errors = len([r for r in results if r['Status'] == 'Error'])
                            
                            if successes > 0:
                                st.success(f"Deployment complete: {successes} Success, {errors} Errors")
                                # Clear the diff state to force a re-run
                                if 'diff_df' in st.session_state:
                                    del st.session_state.diff_df
                                st.info("NOTE: Salesforce's API Cache can take 30-60 seconds to reflect new fields.")
                            else:
                                st.error(f"Deployment failed with {errors} errors.")

                # Display Detailed Results
                if 'deployment_results' in st.session_state:
                    st.markdown("### 📊 Detailed Deployment Report")
                    res_df = pd.DataFrame(st.session_state.deployment_results)
                    
                    # Highlight status
                    def color_status(val):
                        color = '#2ecc71' if val == 'Success' else '#e74c3c'
                        return f'color: {color}; font-weight: bold'
                    
                    st.dataframe(res_df.style.applymap(color_status, subset=['Status']), width='stretch')
                    
                    if st.button("Clear Report"):
                        del st.session_state.deployment_results
                        st.rerun()

        st.markdown("---")
        st.subheader("🛠️ External ID Strategy")
        st.markdown("""
        We require a unique **External ID** field to perform relationship mapping and avoid duplicates during data migration. 
        Choose an existing External ID or let us create a new one for you.
        """)
        
        if 'obj_strategies' not in st.session_state:
            st.session_state.obj_strategies = {}

        for obj in st.session_state.selected_objects:
            with st.expander(f"Strategy for `{obj}`", expanded=True):
                candidates = get_external_id_candidates(st.session_state.target_sf, obj)
                options = candidates + ["Create New: Migration_External_ID__c"]
                
                # Determine default index
                default_idx = 0
                if "Migration_External_ID__c" in candidates:
                    default_idx = candidates.index("Migration_External_ID__c")
                elif not candidates:
                    default_idx = len(options) - 1
                
                selected_field = st.radio(
                    f"Select System Key for {obj}",
                    options=options,
                    index=default_idx,
                    key=f"strat_{obj}",
                    horizontal=True
                )
                
                st.session_state.obj_strategies[obj] = selected_field
                
                if selected_field == "Create New: Migration_External_ID__c":
                    if st.button(f"Deploy to {obj}", key=f"btn_{obj}"):
                        with st.spinner(f"Deploying to {obj}..."):
                            success, err = deploy_external_id_field(st.session_state.target_sf, obj)
                            if success:
                                st.success(f"Successfully configured `{obj}`!")
                                st.rerun()
                            else:
                                st.error(f"Error on {obj}: {err}")
                else:
                    st.info(f"Targeting existing field: `{selected_field}`")

        if st.session_state.obj_strategies:
            st.success("✅ External ID Strategy configurations saved for all objects.")
