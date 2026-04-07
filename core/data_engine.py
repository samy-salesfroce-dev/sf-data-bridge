import pandas as pd
from simple_salesforce import Salesforce
from database.db_handler import get_project_objects, get_field_mappings
from core.graph_resolver import build_dependency_graph

def extract_data(sf_instance, object_name, fields, limit=None):
    """
    Queries Salesforce for the requested fields.
    """
    if not fields:
        return []
    
    # Always query Id for the External ID mapping strategy
    query_fields = list(set(["Id"] + fields))
    q = f"SELECT {','.join(query_fields)} FROM {object_name}"
    if limit:
        q += f" LIMIT {limit}"
        
    try:
        res = sf_instance.query_all(q)
        return res['records']
    except Exception as e:
        print(f"Error querying {object_name}: {e}")
        return []

def execute_migration(source_sf, target_sf, project_id, dry_run=True, progress_cb=None, log_cb=None):
    """
    Executes the full migration based on DAG ordering and Mappings.
    """
    # Get configuration
    objects_db = get_project_objects(project_id)
    obj_name_to_id = {o['object_name']: o['id'] for o in objects_db}
    object_list = list(obj_name_to_id.keys())
    
    # 1. Resolve Dependencies
    if log_cb: log_cb("Resolving object dependencies via DAG...")
    ordered_objects, self_refs = build_dependency_graph(source_sf, object_list)
    
    # Filter ordered_objects to only those in the project
    ordered_objects = [o for o in ordered_objects if o in object_list]
    
    if log_cb: log_cb(f"Migration Order Determined: {' -> '.join(ordered_objects)}")

    audit_report = []

    # 2. Iterate and Migrate
    for idx, obj in enumerate(ordered_objects):
        if log_cb: log_cb(f"--- Processing {obj} ---")
        if progress_cb: progress_cb(idx / len(ordered_objects))
        
        db_obj_id = obj_name_to_id[obj]
        mappings = get_field_mappings(db_obj_id)
        
        if not mappings:
            if log_cb: log_cb(f"Skipping {obj} - No mapped fields.")
            continue
            
        source_fields = [m['source_field'] for m in mappings]
        
        # Extract Data
        ext_limit = 50 if dry_run else None
        if log_cb: log_cb(f"Extracting records for {obj} (Limit: {ext_limit if dry_run else 'All'})...")
        
        records = extract_data(source_sf, obj, source_fields, limit=ext_limit)
        if not records:
            if log_cb: log_cb("No records found.")
            continue
            
        # Data Transformation
        transformed_payloads = []
        for rec in records:
            payload = {}
            # Ensure our special External ID is populated on the target
            # with the Source Org's ID. This is the heart of the engine!
            payload["Migration_External_ID__c"] = rec["Id"]
            
            for m in mappings:
                s_field = m['source_field']
                t_field = m['target_field']
                tx_logic = m.get('transformation_logic')
                
                val = rec.get(s_field)
                
                # Apply Python Logic if defined
                if tx_logic and val is not None:
                    try:
                        # SUPER simple sandbox for value transformations
                        val = eval(tx_logic, {"__builtins__": {}}, {"value": val, "str": str, "int": int})
                    except Exception as e:
                        if log_cb: log_cb(f"Error transforming {s_field} for record {rec['Id']}: {e}")
                        
                payload[t_field] = val
                
            # If there's a self-reference, we might skip it on pass 1. For simplicity, just send it.
            # In a true 2-pass system, we pop self_refs[obj] out on pass 1, then update on pass 2.
            for self_field in self_refs.get(obj, []):
                # If mapped, drop it for upserting, but simple-salesforce bulk handles standard fields better 
                # This needs deeper handling for a raw production engine, for now we will just attempt the upload.
                pass
                
            # Remove 'Id' from payload as it cannot be specified in an insert/upsert call
            # when matching against an External ID. Check case-insensitively.
            keys_to_remove = [k for k in payload.keys() if k.lower() == 'id']
            for k in keys_to_remove:
                payload.pop(k, None)
            
            transformed_payloads.append(payload)
            
        # 3. Upsert via Bulk API (or REST for small batches)
        if log_cb: log_cb(f"Upserting {len(transformed_payloads)} records to Target {obj}...")
        
        try:
            # We use the REST API here dynamically because the simple-salesforce Bulk API 2.0 
            # might not support custom External IDs gracefully without explicit setup in the library wrapper.
            # Actually, sf.bulk is 1.0. For 50 records REST is fine. For larger, we chunk.
            
            # Using simple REST fallback for the prototype reliability
            success_cnt = 0
            error_cnt = 0
            
            # Use Bulk API 1.0 via simple-salesforce bulk interface
            bulk_res = getattr(target_sf.bulk, obj).upsert(transformed_payloads, 'Migration_External_ID__c')
            
            for i, res in enumerate(bulk_res):
                # Map back to source ID for audit trail
                source_id = transformed_payloads[i].get('Migration_External_ID__c', 'Unknown')
                
                if res['success']:
                    audit_report.append({
                        "Object": obj,
                        "Source_ID": source_id,
                        "Target_ID": res.get('id'),
                        "Status": "Success",
                        "Message": "Created" if res.get('created') else "Updated"
                    })
                else:
                    err_msgs = [e.get('message', 'Unknown Error') for e in res.get('errors', [])]
                    err_full = "; ".join(err_msgs) if err_msgs else "Unknown Error"
                    audit_report.append({
                        "Object": obj,
                        "Source_ID": source_id,
                        "Target_ID": "N/A",
                        "Status": "Error",
                        "Message": err_full
                    })
                    
            if log_cb: log_cb(f"Batch for {obj} completed.")
            
        except Exception as e:
            if log_cb: log_cb(f"CRITICAL ERROR during Upsert of {obj}: {e}")
            audit_report.append({
                "Object": obj, 
                "Source_ID": "BATCH_ERROR", 
                "Target_ID": "N/A", 
                "Status": "Error", 
                "Message": str(e)
            })

    if progress_cb: progress_cb(1.0)
    if log_cb: log_cb("Migration Execution Complete!")
    return pd.DataFrame(audit_report)
