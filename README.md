# 🐻 Goldilocks  
### Pipeline Intelligence Platform

> *Love your CURLs.*

Goldilocks is a pipeline intelligence platform for **SnapLogic** integration environments. It parses, maps and monitors data pipelines — transforming raw JSON exports into a living **Neo4j graph database** that reveals how your data actually flows.

---

## ✨ What it does

- **Parses** SnapLogic pipeline exports (`.slp` / JSON) into structured graph data  
- **Maps** pipeline relationships — snaps, dependencies, connections — into **Neo4j**  
- **Generates** visual diagrams of pipeline architecture (Mermaid `.mmd`)  
- **Monitors** pipeline health and complexity patterns  
- **Anonymises** sensitive environment data for safe sharing and auditing  
- *(Coming soon)* **AI agent layer** for natural language pipeline querying  

---

## 🔄 How it works

```
SnapLogic URL → API → JSON → Mermaid Diagram
```

---

## 🚀 Usage

### Fetch a pipeline

```bash
python pie.py fetch
```

### Generate diagrams

```bash
python pie.py visualise --input pipeline_exports/<project>/export.json
```

---

## 🎨 Example Output

![Goldilocks Diagram](docs/example-diagram.png)

---

## 💡 Why

Integration pipelines are often opaque and difficult to understand.  

Goldilocks makes them **visible**, **readable**, and **explainable**.

---

## 🏗️ Architecture

```
SnapLogic Export (JSON)
        │
        ▼
  json_parser.py          ← Parses raw pipeline structure
        │
        ▼
  file_processor.py       ← Cleans, validates, prepares data
        │
        ▼
  goldilocks_seed.py      ← Seeds Neo4j graph database
        │
        ▼
  database_connector.py   ← Neo4j Aura connection layer
        │
        ▼
  diagram_generator.py    ← Generates Mermaid architecture diagrams
        │
        ▼
    Neo4j Aura 🌐         ← Live graph database
```

---

## 🛠️ Tech stack

| Tool           | Purpose            |
|----------------|-------------------|
| Python         | Core processing   |
| Neo4j Aura     | Graph database    |
| Cypher         | Graph queries     |
| Mermaid        | Pipeline diagrams |
| Google Colab   | Development       |

---

## 🗺️ Roadmap

- [x] JSON pipeline parser  
- [x] Neo4j graph seeding  
- [x] Mermaid diagram generation  
- [x] Pipeline anonymiser  
- [x] PyPI package (`pip install goldilocks`)  
- [ ] AI agent layer — natural language pipeline queries  

---

## 💡 Background

Goldilocks grew out of a real operational need: when you manage dozens of integration pipelines, understanding how data flows across a complex estate becomes genuinely hard.  

Existing tools show you individual pipelines — Goldilocks shows you the **whole map**.

Built as part of an independent R&D practice exploring the intersection of:

- **graph databases**  
- **data integration**  
- **AI-assisted operations**

---

## 👩‍💻 Author

**Hélène Martin** — Application & BI Engineer  
Folkestone, UK 🇫🇷🇬🇧  
https://github.com/Helene-Garance-Martin
