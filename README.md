# 🐻 Goldilocks  
### Pipeline Intelligence Platform

> *Love your CURLs.*

Goldilocks is a pipeline intelligence CLI for **SnapLogic** integration environments. It fetches, parses and visualises data pipelines — transforming raw JSON exports into a **Neo4j graph** and elegant **Mermaid diagrams**.

🌐 https://goldilocks-cli.org · 📦 `pip install goldilocks-pipeline` · 📄 MIT Licence

---

## ✨ What it does

- **Fetches** pipeline exports directly from the SnapLogic API  
- **Sanitises** raw exports — strips UI noise and rendering metadata  
- **Anonymises** sensitive data — safe to share publicly or commit to GitHub  
- **Visualises** pipeline architecture as Mermaid diagrams (`.mmd`, `.png`, `.svg`)  
- *(Coming soon)* **AI agent layer** for natural language pipeline querying  

---

## 🔄 The flow

```
fetch → sanitise → anonymise → visualise → ask
```

---

## 🚀 Quick start

```bash
python pie.py fetch
python pie.py visualise --input pipeline_exports/<project>/export.json
```

---

## 🎨 Example Output

![Goldilocks Combined Diagram](docs/goldilocks_combined.png)

💡 Tip: open the combined diagram to see the full system flow

---

## 💡 Why Goldilocks?

Integration pipelines are often opaque and difficult to understand.  

Goldilocks makes them **visible**, **readable**, and **explainable** — showing not just individual pipelines, but the **whole map**.

---

## *From RAGs to DAGs to Riches* 💅

---

## 🎨 About the author

**Hélène Martin** — Application & BI Engineer  
Folkestone, UK 🇫🇷🇬🇧  

Goldilocks was built outside working hours, out of frustration with opaque integration tooling — and a belief that infrastructure should be as legible as it is functional.

> *"Poetical science"* — Ada Lovelace  

https://github.com/Helene-Garance-Martin  
https://goldilocks-cli.org