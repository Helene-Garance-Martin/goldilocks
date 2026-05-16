# Goldilocks
### Semantic Topology for Integration Pipelines

> *Love your CURLs.*

Goldilocks is a graph-native exploration toolkit for integration environments.

It transforms orchestration exports into **semantic execution topology** using **Neo4j traversal**, producing readable DAG views, Mermaid diagrams, and operational graph context from otherwise fragmented pipeline structures.

---

## ✨ Current capabilities

- Parse SnapLogic pipeline exports
- Sanitise and anonymise exports
- Seed orchestration graphs into Neo4j
- Traverse `CONNECTS_TO` relationships
- Generate semantic DAG models
- Render readable ASCII execution trees
- Generate Mermaid topology diagrams
- Detect branching and merge behaviour
- Explore parent/child pipeline relationships

---

## 🔄 Conceptual flow

```text
Json export
    ↓
sanitise
    ↓
anonymise
    ↓
Neo4j graph
    ↓
traversal
    ↓
semantic DAG
    ↓
renderers
```

---

## 🌿 Semantic topology

Raw orchestration exports are often noisy and structurally fragmented.

Goldilocks distinguishes between:

- **export topology**  
  how orchestration tools serialise pipelines

and:

- **semantic execution topology**  
  how work actually flows through the system

This enables more readable execution views, branch-aware traversal, and graph-native operational understanding.

---

## 🎨 Example outputs

### Mermaid topology (raw export view)

![Goldilocks Mermaid Diagram](/docs/INT-70_Dayforce.png)

🫧 Goldilocks Pipeline Graph
├── 📊 Dayforce Job Titles to DynamoDB (6 snaps · 0 parents · 0 children)
│   ├── ✅ ⚙️ JSON Splitter 
│   ├── 🔥 🌐 Get Job Update Reports 
│   ├── 🔥 🌐 Get Bearer Token 
│   ├── ✅ 🔀 Get Last Run Time 
│   ├── ✅ ⚙️ Mapper 
│   └── ✅ ⚙️ DynamoDB Bulk Write 
└── 📊 Dayforce to DIESE Job Titles (24 snaps · 0 parents · 0 children) ⚡ Complex
    ├── ✅ 🔀 Get Last Run Time 
    ├── ✅ ⚙️ UDF Populated 
    ├── ✅ ⚙️ Map to DIESE Create Job 
    ├── 🔥 🌐 #DIESE Create Job 
    ├── ✅ ⚙️ Map to Department Link 
    ├── 🔥 🌐 #DIESE Link Department 
    ├── ✅ ⚙️ Map to Dayforce PATCH Job 
    ├── ✅ ⚙️ Copy 
    ├── 🔥 🌐 Dayforce Update Job 
    ├── ✅ ⚙️ Route by Error Msg 
    ├── ✅ ⚙️ Map to Dayforce PATCH Job 
    ├── ✅ ⚙️ Union Update Dayforce 
    ├── ✅ 🔀 Send Error Alert 
    ├── ✅ ⚙️ Map to DIESE Update Job 
    ├── 🔥 🌐 #DIESE Update Job 
    ├── ✅ ⚙️ Union Errors 
    ├── ✅ ⚙️ DynamoDB Scan 
    ├── 🔥 🌐 Get Dayforce Bearer Token 
    ├── 🔥 🌐 #DIESE Auth 
    ├── ✅ ⚙️ Map Auth 
    ├── ✅ ⚙️ Map to Record ID 
    ├── ✅ ⚙️ Map to Record ID 
    ├── ✅ ⚙️ DynamoDB Delete Table Item 
    └── ✅ ⚙️ Union Delete RecordIds  

### ASCII DAG traversal (semantic execution view)



![Goldilocks ASCII DAG](docs/ascii.traversal.png)

---

### Neo4j Graph (traversal execution view)



![Goldilocks ASCII DAG](docs/ascii.traversal.png)

---

## 🧭 Current status

Goldilocks is currently experimental and focused on:

- traversal modelling
- renderer architecture
- orchestration visibility
- semantic graph exploration

SnapLogic is the current ingestion target, but the architecture is designed to support additional orchestration platforms.

---

## *From RAGs to DAGs to Riches* 💅

---

## 🎨 About the author

**Hélène Martin**  
Artist-filmmaker and Application & BI Engineer  
Folkestone, UK 🇫🇷🇬🇧

Goldilocks emerged from a desire to make orchestration systems more legible, navigable, and explainable.

> *"Poetical science"* — Ada Lovelace

GitHub: https://github.com/Helene-Garance-Martin