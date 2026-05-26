# Dataplex Master Pipeline

This is the centralized hub for the **Dataplex End-to-End Scan Creation System**. 

## **End-to-End Workflow Diagram**

```mermaid
flowchart LR
    subgraph P0 ["Phase 0: Build"]
        direction TB
        P0S["UI Builder"] --> P0P["High-Speed Discovery"] --> P0B["Build Rules (Range/Derived)"] --> P0C["Rules CSV"]
    end

    subgraph P1 ["Phase 1: Discover"]
        direction TB
        P1A["Resource Manager API"] --> P1S["Multithreaded Scan"] --> P1M["Consolidated Meta (PK/FK)"]
    end

    subgraph P2 ["Phase 2: Verify"]
        direction TB
        P2A["Multithreaded Verifier"] --> P2M["Live BQ Check"] --> P2V{"Verify R/W"} --> P2R["Verified Rules"]
    end

    subgraph P3 ["Phase 3: Generate"]
        direction TB
        P3A["Artifact Generator"] --> P3T["Parse Thresholds"] --> P3G["Generate YAML"] --> P3F["Create Batch CLI"]
    end

    P0 --> P1 --> P2 --> P3
    P3 --> DONE["Scans Ready"]

    style P1M fill:#f9f,stroke:#333,stroke-width:2px
    style P2V fill:#f9f,stroke:#333,stroke-width:2px
    style P3G fill:#f9f,stroke:#333,stroke-width:2px
```

## **The Master Orchestrator**
**Tool:** `hub.py` (Streamlit)
- **Purpose:** A single entry point to run all 5 phases of the pipeline.
- **Features:** Intelligent **"Direct-First, Proxy-Fallback"** networking using the `Shared_Resources/networking.py` utility. Automatically handles corporate proxy settings (`http://googleapis-dev.dev.gcp.cloud.in.hsbc:3128`) and enforces remote DNS resolution to ensure stable connectivity. Unified execution logs are displayed via `Shared_Resources/ui_helpers.py`.


## **The Four-Phase Pipeline**

### **Phase 0: Rule Building (UI)**
**Tool:** `01_Phase_0_Rule_Building/ui_builder.py` (Streamlit)
- **Purpose:** Create your rules file from scratch using a reactive UI. Supports Single pass-rates, Range Thresholds (Lower/Upper), and Derived Attributes.
- **Verification Step:** Live validation using Google APIs. Logs are minimized by default to ensure maximum speed.

### **Phase 1: Discovery (Schema Alignment)**
**Tool:** Built into `hub.py`
- **Purpose:** Perform bulk extractions at the table, dataset, or project level.
- **Features:** Uses Resource Manager APIs for lightning-fast project scans. Identifies Primary Keys, Foreign Keys, Partitioning, and Clustering columns.

### **Phase 2: Verification (Rule Cleansing)**
**Tool:** Built into `hub.py`
- **Purpose:** Cross-reference your Rules File against actual live Data schemas in bulk.
- **Features:** Multithreaded concurrent verification (`ThreadPoolExecutor`). Accurately validates derived attributes and physical columns.

### **Phase 3: Generation (Config Creation)**
**Tool:** Built into `hub.py`
- **Purpose:** Translate verified rules into Dataplex YAML and executable shell scripts (`create_scan.sh`).
- **Features:** Handles range thresholds and automatically skips schema constraints for derived attributes.

---

## **Directory Structure**
- `/00_Orchestration`: Master Hub and unified workflows.
- `/01_Phase_0_Rule_Building`: UI and CLI for rule creation.
- `/02_Phase_1_Schema_Discovery`: Legacy individual discovery agents.
- `/03_Phase_2_Metadata_Verification`: Legacy verification agents.
- `/04_Phase_3_Config_Generation`: Legacy config translation agents.
- `/outputs`: (Automated) Structured artifacts (YAML, Bash, Schemas).
- `/logs`: (Automated) Timestamped audit logs for every execution step.
- `/Shared_Resources`: Master templates and architecture diagrams.