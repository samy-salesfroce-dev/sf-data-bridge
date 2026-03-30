# SF-Data-Bridge

A professional Salesforce-to-Salesforce Migration Tool built in Python.

## Core Features

- **Project Persistence**: Uses an SQLite database to store projects, object configurations, and field mappings.
- **Username/Password Authentication**: Securely connect to your Source and Target Salesforce environments.
- **Metadata Diff**: Automatically compares Object schema, identifies missing fields, and evaluates type mismatches.
- **Universal External ID Strategy**: Effortlessly deploy the required `Migration_External_ID__c` field to Target objects via the Metadata API.
- **DAG Dependency Resolver**: Utilizes `networkx` to calculate the correct order of data migration (Parent before Children), ensuring relationships are preserved via the External ID.
- **Custom Mapping & Logic Evaluation**: Map any Source to Target field. Inject basic Python string transformation logic (e.g. `value.strip().upper()`).
- **Data Engine**: High-performance REST/Bulk Upsert engine featuring Dry Run tests (limit 50 per object) and deep error auditing.

## Local Setup

1. Make sure Python 3.10+ is installed.
2. Initialize and activate the virtual environment:
   ```bash
   .\venv\Scripts\python.exe -m pip install -r requirements.txt
   ```
4. Run the Application (Bypassing Execution Policies):
   ```bash
   .\venv\Scripts\python.exe -m streamlit run app.py
   ```
