# Project Instructions: Dataplex Master

You are working in the **Dataplex Master Hub**. This project coordinates three distinct agents into a single data quality pipeline.

## **Mandatory Protocols**

### **1. Zero-Assumption Policy**
You must never assume you understand the user's data logic or file structures. 
- **Before File Edits:** Present the proposed change (diff) and ask for confirmation.
- **Before SQL Generation:** Present the generated SQL in plain text and ask: "Does this SQL accurately represent your business logic?"
- **Before Scan Creation:** Summarize all Batch parameters (Schedule, Incremental Field, etc.) for final sign-off.

### **2. Technical Environment Constraints**
- **Proxy Usage:** All agents support a **"Direct-First, Proxy-Fallback"** strategy. They automatically attempt direct connection and fall back to the corporate proxy (`http://googleapis-dev.dev.gcp.cloud.in.hsbc:3128`) if needed.
- **DNS Resolution:** Remote DNS resolution is enforced via `PySocks` to ensure Google APIs resolve correctly within corporate networks.
- **Security:** MUST use default CA certificates provided by the environment.
- **Tooling:** Use ONLY the default Python environment and default `gcloud` authentication details. No service account keys or virtual environments should be created.

### **3. Pipeline Execution Sequence**
The **Dataplex Master Hub (`hub.py`)** coordinates the entire flow:
1. **Phase 0:** Build Rules via UI/CLI.
2. **Phase 1:** Discover schemas and metadata.
3. **Phase 2:** Verify rules against live BigQuery schemas.
4. **Phase 3:** Generate Dataplex artifacts (YAML/Bash).
5. **Phase 4:** Provision and validate new BigQuery tables.

### **4. File & Artifact Management**
- **Structured Storage:** ALL generated artifacts (schemas, YAMLs, batch scripts) MUST be organized into table-specific subdirectories within the `outputs/` folder.
- **Audit Logging:** Standardized logging is implemented in `Shared_Resources/ui_helpers.py` and displayed in the UI's "System Execution Logs" expander.
- **Rule Source:** Store all rules in `Shared_Resources/final_rules.csv`.
