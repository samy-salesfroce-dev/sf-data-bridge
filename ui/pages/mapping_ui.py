import streamlit as st
from core.metadata_engine import get_object_fields
from database.db_handler import get_project_objects, save_field_mapping, get_field_mappings

def render_page():
    st.header("3. Transformation & Mapping")
    st.markdown("Map Source fields to Target fields and define optional Python-based transformations.")

    if not st.session_state.source_sf or not st.session_state.target_sf:
        st.warning("Please connect to both Source and Target Orgs first.")
        return

    objects = get_project_objects(st.session_state.current_project_id)
    if not objects:
        st.warning("No objects selected for this project. Go to the Metadata Diff phase to add objects.")
        return

    # Select Object to Map
    object_names = [obj['object_name'] for obj in objects]
    selected_object = st.selectbox("Select Object to Map", object_names)
    
    active_obj = next(o for o in objects if o['object_name'] == selected_object)
    
    st.subheader(f"Field Mapping for {selected_object}")

    with st.spinner("Loading fields..."):
        src_fields = get_object_fields(st.session_state.source_sf, selected_object)
        tgt_fields = get_object_fields(st.session_state.target_sf, selected_object)
        
    src_field_names = sorted(list(src_fields.keys()))
    tgt_field_names = ["-- Ignore --"] + sorted(list(tgt_fields.keys()))
    
    # Load existing mappings
    existing_mappings = {m['source_field']: m for m in get_field_mappings(active_obj['id'])}

    # Render mapping table
    st.markdown("### Match Source Fields to Target Fields")
    st.markdown("Use `-- Ignore --` to skip migrating a specific field. You can inject custom Python logic using the `value` variable in the Transformation box.")

    with st.form(f"mapping_form_{selected_object}"):
        for s_field in src_field_names:
            col1, col2, col3 = st.columns([2, 2, 2])
            
            with col1:
                st.write(f"**{s_field}**")
                # Auto-match logic if not already mapped
                default_target = "-- Ignore --"
                if s_field in existing_mappings:
                    default_target = existing_mappings[s_field]['target_field']
                elif s_field in tgt_field_names:
                    default_target = s_field
                
            with col2:
                # Target field selectbox
                default_idx = tgt_field_names.index(default_target) if default_target in tgt_field_names else 0
                t_field = st.selectbox(
                    f"Target Field for {s_field}", 
                    tgt_field_names, 
                    index=default_idx, 
                    label_visibility="collapsed",
                    key=f"target_{s_field}"
                )
            
            with col3:
                # Transformation logic
                default_tx = existing_mappings.get(s_field, {}).get('transformation_logic', "")
                tx_logic = st.text_input(
                    f"Logic for {s_field}", 
                    value=default_tx or "",
                    placeholder="e.g. value.strip().upper()",
                    label_visibility="collapsed",
                    key=f"tx_{s_field}"
                )
                
            # Submit button
        
        if st.form_submit_button("Save Mappings"):
            st.session_state[f"mapping_saved_{selected_object}"] = True
            count = 0
            for s_field in src_field_names:
                t_val = st.session_state[f"target_{s_field}"]
                tx_val = st.session_state[f"tx_{s_field}"]
                
                if t_val != "-- Ignore --":
                    save_field_mapping(active_obj['id'], s_field, t_val, tx_val)
                    count += 1
            st.success(f"Saved {count} field mappings for {selected_object}!")
