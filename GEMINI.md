# Project Instructions: Dataplex Master

You are working in the **Dataplex Master Hub**. This project coordinates three distinct agents into a single data quality pipeline.

## **Mandatory Protocols**

### **1. Zero-Assumption Policy**
You must never assume you understand the user's data logic or file structures. 
- **Before File Edits:** Present the proposed change (diff) and ask for confirmation.
- **Before SQL Generation:** Present the generated SQL in plain text and ask: "Does this SQL accurately represent your business logic?"
- **Before Scan Creation:** Summarize all Batch parameters (Schedule, Incremental Field, etc.) for final sign-off.

### **2. Technical Environment Constraints**
- **Proxy Usage:** All agents MUST support proxy configuration. If Windows credentials are missing, agents MUST ask the user for a username/password for the proxy.
- **Security:** MUST use default CA certificates provided by the environment.
- **Tooling:** Use ONLY the default Python environment and default `gcloud` authentication details. No service account keys or virtual environments should be created.

### **3. Pipeline Execution Sequence**
When the user asks to "start the process" or "create scans," guide them through this specific order:
1. **Discovery:** Run `Schema/bq_schema_agent.py` to pull metadata.
2. **Verify:** Invoke `@data-verifier` to clean the rules file.
3. **Generate:** Invoke `@rule-creator` to build the final artifacts.

### **3. File & Artifact Management**
- **Structured Storage:** ALL generated artifacts (schemas, YAMLs, batch scripts) MUST be organized into table-specific subdirectories within the `outputs/` folder (e.g., `outputs/project_dataset_table/`).
- **Audit Logging:** EVERY execution step of every agent MUST be logged in a timestamped file within the `logs/` directory. Logs must include:
    - Inputs provided by the user.
    - Agent's interpretation/logic explanations.
    - Final technical commands or configuration content.
- **Rule Source:** Store all rules in `Rule creator/rules_template.csv`.
