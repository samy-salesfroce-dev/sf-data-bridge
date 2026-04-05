import pandas as pd
import zipfile
import tempfile
import time
import base64
import os

def get_object_fields(sf_instance, object_name):
    """
    Fetches the field describe for an object and returns a dictionary of field definitions.
    """
    try:
        describe_res = getattr(sf_instance, object_name).describe()
        return {f['name']: f for f in describe_res['fields']}
    except Exception as e:
        print(f"Error describing {object_name}: {e}")
        return {}

def compare_schemas(source_sf, target_sf, object_list):
    """
    Compares the schema between Source and Target for a list of objects.
    Returns a Pandas DataFrame representing missing fields on the Target.
    """
    diff_data = []
    
    for obj in object_list:
        src_fields = get_object_fields(source_sf, obj)
        tgt_fields = get_object_fields(target_sf, obj)
        
        for field_name, src_attr in src_fields.items():
            if field_name not in tgt_fields:
                diff_data.append({
                    "Deploy": False,
                    "Object": obj,
                    "Field Name": field_name,
                    "Label": src_attr['label'],
                    "Type": src_attr['type'],
                    "Length": src_attr.get('length', ''),
                    "Status": "Missing on Target",
                    "Is_Custom": field_name.endswith('__c')
                })
            else:
                # Optionally check if length/type mismatches
                tgt_attr = tgt_fields[field_name]
                if src_attr['type'] != tgt_attr['type']:
                    diff_data.append({
                        "Deploy": False,
                        "Object": obj,
                        "Field Name": field_name,
                        "Label": src_attr['label'],
                        "Type": f"{src_attr['type']} -> {tgt_attr['type']}",
                        "Status": "Type Mismatch",
                        "Is_Custom": False # Can't deploy standard type mismatches via tooling
                    })
    
    return pd.DataFrame(diff_data)

def deploy_external_id_field(target_sf, object_name):
    """
    Deploys the Migration_External_ID__c field to the specified Object on the Target Org
    using the simple-salesforce mdapi wrapper.
    """
    field_xml = f"""<?xml version="1.0" encoding="UTF-8"?>
<CustomObject xmlns="http://soap.sforce.com/2006/04/metadata">
    <fields>
        <fullName>Migration_External_ID__c</fullName>
        <externalId>true</externalId>
        <label>Migration External ID</label>
        <length>255</length>
        <required>false</required>
        <trackTrending>false</trackTrending>
        <type>Text</type>
        <unique>true</unique>
        <caseSensitive>false</caseSensitive>
    </fields>
</CustomObject>
"""

    package_xml = """<?xml version="1.0" encoding="UTF-8"?>
<Package xmlns="http://soap.sforce.com/2006/04/metadata">
    <types>
        <members>*</members>
        <name>CustomObject</name>
    </types>
    <version>58.0</version>
</Package>
"""

    with tempfile.TemporaryDirectory() as temp_dir:
        # Create package struct
        os.makedirs(os.path.join(temp_dir, 'objects'), exist_ok=True)
        
        # Write files
        with open(os.path.join(temp_dir, 'package.xml'), 'w', encoding='utf-8') as f:
            f.write(package_xml)
        
        with open(os.path.join(temp_dir, 'objects', f'{object_name}.object'), 'w', encoding='utf-8') as f:
            f.write(field_xml)
            
        # Create zip
        zip_path = os.path.join(temp_dir, 'package.zip')
        with zipfile.ZipFile(zip_path, 'w') as zipf:
            zipf.write(os.path.join(temp_dir, 'package.xml'), 'package.xml')
            zipf.write(os.path.join(temp_dir, 'objects', f'{object_name}.object'), f'objects/{object_name}.object')

        # Deploy
        # Determine if sandbox
        is_sandbox = target_sf.query("SELECT IsSandbox FROM Organization LIMIT 1")['records'][0]['IsSandbox']
        
        # Note: mdapi.deploy returns an async ID. We need to wait for it.
        deploy_result = target_sf.mdapi.deploy(zip_path, sandbox=is_sandbox, singlePackage=True, ignoreWarnings=True)
        
        if isinstance(deploy_result, tuple):
            job_id = deploy_result[0]
        elif isinstance(deploy_result, dict):
            job_id = deploy_result.get('id')
        else:
            job_id = str(deploy_result)
        
        if job_id:
            while True:
                status_raw = target_sf.mdapi.check_deploy_status(job_id)
                status = status_raw[0] if isinstance(status_raw, tuple) else status_raw
                
                # Handle dictionary semantics vs object semantics
                done = status.get('done') if isinstance(status, dict) else getattr(status, 'done', False)
                if done:
                    success = status.get('success') if isinstance(status, dict) else getattr(status, 'success', False)
                    err_msg = status.get('errorMessage') if isinstance(status, dict) else getattr(status, 'errorMessage', '')
                    return success, err_msg
                time.sleep(2)
        return False, "Deployment job failed to start."

def deploy_selected_metadata(source_sf, target_sf, selected_rows):
    """
    Deploys selected custom fields from Source to Target using Tooling API.
    """
    success_count = 0
    errors = []
    
    for row in selected_rows:
        if not row.get('Deploy') or not row.get('Is_Custom'):
            continue
            
        obj = row['Object']
        field = row['Field Name']
        
        try:
            # 1. Fetch Metadata from Source
            dev_name = field.replace('__c', '')
            # Tooling API query needs to be URL encoded or handled by tooling_execute logic
            # simple-salesforce toolingexecute doesn't automatically urlencode the 'action' string if it's a query
            query = f"SELECT Metadata FROM CustomField WHERE DeveloperName='{dev_name}' AND TableEnumOrId='{obj}'"
            encoded_query = query.replace(' ', '+').replace("'", "%27")
            res = source_sf.toolingexecute(f"query?q={encoded_query}")
            
            if not res.get('records'):
                errors.append(f"Field {field} on {obj}: Not found in Source Tooling metadata.")
                continue
                
            metadata = res['records'][0]['Metadata']
            
            # 2. Deploy to Target
            full_name = f"{obj}.{field}"
            # Tooling API POST for CustomField
            payload = {
                "FullName": full_name,
                "Metadata": metadata
            }
            
            target_sf.toolingexecute('sobjects/CustomField/', method='POST', json=payload)
            success_count += 1
            
        except Exception as e:
            err_str = str(e)
            if "DUPLICATE_DEVELOPER_NAME" in err_str:
                # Treat as success if the field already exists as intended
                success_count += 1
            else:
                errors.append(f"Field {field} on {obj}: {err_str}")
            
    return success_count, errors
