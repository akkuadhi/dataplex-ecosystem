# Dataplex Master Hub Ecosystem 🚀

A modernized, structured ecosystem to automate Google Cloud Dataplex Data Quality Scan creation.

## 📊 End-to-End Workflow

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

---

## 🏗️ The 4-Phase Pipeline

| Phase | Agent | Folder | Purpose |
| :--- | :--- | :--- | :--- |
| **0** | `@rule-builder` | `01_Phase_0_Rule_Building` | Interactively build rules CSV with live schema fetching. |
| **1** | `@schema-agent` | `02_Phase_1_Schema_Discovery` | Pull ground-truth BigQuery metadata as artifacts. |
| **2** | `@data-verifier` | `03_Phase_2_Metadata_Verification` | Align rules CSV against official BQ metadata. |
| **3** | `@rule-creator` | `04_Phase_3_Config_Generation` | Translate logic to modern 2026 Dataplex YAML/Batch. |

---

## 🛠️ Execution Guide

### **1. Launch the Orchestrator**
The central hub for the entire pipeline:
```powershell
cd 00_Orchestration
streamlit run hub.py
```

### **2. Directory Architecture**
- **`/00_Orchestration`**: Central control hub and orchestrator agent.
- **`/01_Phase_0_Rule_Building`**: Rule building tools and agents.
- **`/02_Phase_1_Schema_Discovery`**: BQ discovery engine.
- **`/03_Phase_2_Metadata_Verification`**: Automated metadata alignment.
- **`/04_Phase_3_Config_Generation`**: Artifact generation.
- **`/Shared_Resources`**: Templates, guides, and shared datasets.
- **`/outputs`**: Table-specific artifacts (Schemas, YAMLs, Batch).
- **`/logs`**: Full execution audit trail.

---

## ✨ System Standards
- **User-Agnostic**: All scripts use dynamic relative pathing.
- **Compliance**: Follows modern 2026 Dataplex `sqlAssertionExpectation` standards.
- **Traceable**: Every action is timestamped and logged.
- **Secure**: Integrated corporate proxy and gcloud auth support.
