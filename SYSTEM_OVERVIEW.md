# Dataplex Master Pipeline

This is the centralized hub for the **Dataplex End-to-End Scan Creation System**. 

## **End-to-End Workflow Diagram**

```mermaid
flowchart LR
    subgraph P0 ["Phase 0: Build"]
        direction TB
        P0S["UI / CLI"] --> P0P["Select Projects"] --> P0F["Fetch BQ Schema"] --> P0B["Build Rules"] --> P0C["Rules CSV"]
    end

    subgraph P1 ["Phase 1: Discover"]
        direction TB
        P1A["Schema Agent"] --> P1S["Scan Projects"] --> P1V{"Verify Location"} --> P1M["Official Metadata"]
    end

    subgraph P2 ["Phase 2: Verify"]
        direction TB
        P2A["@data-verifier"] --> P2M["Match Headers"] --> P2V{"Verify Mismatches"} --> P2R["Verified Rules"]
    end

    subgraph P3 ["Phase 3: Generate"]
        direction TB
        P3A["@rule-creator"] --> P3T["Translate Logic"] --> P3L{"Verify Logic"} --> P3G["Generate SQL"] --> P3S{"Verify SQL"} --> P3F["Generate Files"]
    end

    P0 --> P1 --> P2 --> P3
    P3 --> DONE["Scans Ready"]

    style P1V fill:#f9f,stroke:#333,stroke-width:2px
    style P2V fill:#f9f,stroke:#333,stroke-width:2px
    style P3L fill:#f9f,stroke:#333,stroke-width:2px
    style P3S fill:#f9f,stroke:#333,stroke-width:2px
```

## **The Master Orchestrator**
**Tool:** `master_hub_ui.py` (Streamlit)
- **Purpose:** A single entry point to run all 4 phases of the pipeline.
- **Features:** Centralized proxy management, interactive verification, and automated file generation.

## **The Four-Phase Pipeline**
...

### **Phase 0: Rule Building (UI)**
**Tool:** `Rule creator/rule_builder_ui.py` (Streamlit)
- **Purpose:** Create your rules file from scratch using a dynamic UI.
- **Verification Step:** The UI fetches live schemas from BigQuery. You review every rule in a dynamic table before saving.

### **Phase 1: Discovery (Schema Alignment)**
...

### **Phase 2: Verification (Rule Cleansing)**
**Agent:** `@data-verifier`
- **Purpose:** Cross-reference your Rules File against your actual Data Files.
- **Verification Step:** 
    - The agent will list every mismatch found (casing, spaces, missing columns).
    - It will propose a correction plan and **must wait for your explicit approval** before modifying any file.

### **Phase 3: Generation (Config Creation)**
**Agent:** `@rule-creator`
- **Purpose:** Translate natural language business logic into Dataplex YAML and Batch files.
- **Verification Step:**
    - The agent will translate your "Rule_Logic" into BigQuery SQL.
    - **MANDATORY:** It will display the proposed SQL and parameter mappings.
    - **Confirmation Required:** You must review and approve the SQL logic before the `.yaml` and `.bat` files are generated.

---

## **Directory Structure**
- `/Schema`: BigQuery discovery tools.
- `/Verification`: Rule-to-Data matching agents.
- `/Rule creator`: Logic-to-YAML/Batch translation agents.
- `/outputs`: (Automated) Structured, table-specific artifacts (YAML, Batch, Schemas).
- `/logs`: (Automated) Timestamped audit logs for every execution step.
