# Goldilocks

**Introspect SnapLogic pipelines. Build a graph. Ask questions of it.**

Goldilocks is a command-line tool that reads your SnapLogic estate, maps how pipelines connect, and lets you query and visualise that structure locally, on your own machine. It turns a sprawl of pipeline definitions into a traversable graph you can actually reason about.

The value is **extraction, not publication**. Goldilocks pulls the shape of your pipelines out of a system that does not readily give it up and hands it to you in a form you can read, diagram, and interrogate.

Sharing that shape safely is a feature the tool offers, but the point is understanding what you have.

> **v1.0.0 note:** This release is currently built against the EMEA SnapLogic pod. Multi-pod support, deriving the pod from your project URL, is the next milestone. If your organisation is on a different pod, `fetch` may contact the wrong host. See [Requirements](#requirements).

## The journey

Goldilocks moves through five steps, in order:

```text
init  →  fetch  →  sieve  →  seed  →  ask / visualise
```

* **init** sets up a workspace and your credentials.
* **fetch** pulls pipeline definitions from your SnapLogic organisation.
* **sieve** anonymises the fetched pipelines using the sanitiser and anonymiser, so nothing sensitive leaves your machine if you choose to share the output.
* **seed** loads the pipelines into a local Neo4j graph and traverses the DAG.
* **ask / visualise** lets you query the graph in natural language or render it as a Rich tree or Mermaid diagram.

## Install

```bash
pip install goldilocks-curls
```

The command is `goldilocks`:

```bash
goldilocks --help
```

## Quickstart

```bash
# 1. Set up your workspace and credentials
goldilocks init

# 2. Pull your pipelines
goldilocks fetch

# 3. Anonymise them
goldilocks sieve

# 4. Load them into the local graph
goldilocks seed

# 5. Ask a question or draw the picture
goldilocks ask "which pipelines write to SharePoint?"
goldilocks visualise
```

`ask` takes your question as a positional argument.

`visualise` takes an optional pipeline name. Omit it to open an interactive menu. By default, diagrams are written to the `diagrams/` directory.

Use `-f mmd|svg|png` to choose the format and `-o <dir>` to change the output directory.

## Commands

| Command                | What it does                                                                             |
| ---------------------- | ---------------------------------------------------------------------------------------- |
| `goldilocks init`      | Create a workspace and configure credentials.                                            |
| `goldilocks fetch`     | Retrieve pipeline definitions from SnapLogic.                                            |
| `goldilocks sieve`     | Run the sanitiser and anonymiser over fetched pipelines.                                 |
| `goldilocks seed`      | Load anonymised pipelines into Neo4j and build the DAG.                                  |
| `goldilocks ask`       | Query the graph in natural language using the Anthropic SDK.                             |
| `goldilocks visualise` | Render the graph as a Rich tree or Mermaid diagram.                                      |
| `goldilocks status`    | Show what has been fetched, sieved, and seeded, then suggest the next step.              |
| `goldilocks check`     | Scan a file for leaks. Exits with `0` if clean and `1` if anything sensitive is found.   |
| `goldilocks doctor`    | Check prerequisites and credentials, and report what remains unresolved.                 |
| `goldilocks demo`      | Run the full journey in an isolated temporary workspace using real production functions. |

## What the sieve does, and does not do

Honesty matters more than reassurance here, so this is plain.

### The sieve does

* Replace identifiers on word boundaries using a consistent lookup table, so the same name maps to the same replacement every time.
* Run dedicated passes over URLs, email addresses, and GUIDs.
* Run a post-scrub leak scanner that checks the output for anything that slipped through.

### The sieve does not

* Understand meaning. It matches patterns and known identifiers, not semantics. A sensitive name embedded in freeform text, an unusual field, or a value it has no reason to recognise may survive.
* Prove that a file is safe. A clean scan is evidence, not proof.
* Replace human review before sharing.

If you intend to share sieved output, run `goldilocks check` first and read what it flags.

A clean exit means the scanner found nothing it recognises. It does **not** mean that the file is provably safe.

## Trying it without a SnapLogic organisation

```bash
goldilocks demo
```

`demo` runs the entire journey against a fully synthetic estate called the fictional **Marmalade Museum**.

It runs in an isolated temporary workspace and calls the same production functions as the real commands. Nothing is faked. It makes no SnapLogic or external network calls, seeds only a local graph, and cleans up after itself.

It is an honest look at how the tool behaves from end to end, with no credentials required.

## Architecture

Goldilocks follows **one traversal, many outputs**:

```text
seed Neo4j  →  Cypher DAG traversal  →  Pydantic DAGModel  →  Rich tree / Mermaid
```

The graph is the intermediate representation. The Rich tree and Mermaid renderers are views onto it.

Goldilocks is built with:

* [Typer](https://typer.tiangolo.com/) for the command-line interface
* [Rich](https://rich.readthedocs.io/) for terminal output
* [Neo4j](https://neo4j.com/) for the graph
* [Pydantic](https://docs.pydantic.dev/) for the DAG model
* The Anthropic SDK for natural-language querying

## Requirements

* **Python 3.10 or later**
* **Neo4j**, required for `seed`, `ask`, `visualise`, `status`, and `show-graph`
* **An Anthropic API key**, required for `ask`
* **SnapLogic access**, required for `fetch`
* **mmdc**, optional and required only when rendering Mermaid output to PNG or SVG

### Neo4j

You need a running Neo4j instance reachable through `NEO4J_URI`, with `NEO4J_PASSWORD` set.

```env
NEO4J_URI=neo4j+s://your-instance.databases.neo4j.io
NEO4J_PASSWORD=your-password
```

Run the following command to verify the connection:

```bash
goldilocks doctor
```

`fetch` and `sieve` do not require Neo4j.

`demo` uses a local graph when one is available and otherwise continues without it.

### Anthropic

Set your Anthropic API key before using `ask`:

```env
ANTHROPIC_API_KEY=your-api-key
```

### SnapLogic

Set your SnapLogic credentials before using `fetch`:

```env
SNAPLOGIC_USERNAME=your-username
SNAPLOGIC_PASSWORD=your-password
```

SnapLogic credentials are not required for `demo`.

### Mermaid CLI

The Mermaid CLI, `mmdc`, is optional. It is needed only to render `visualise` output directly to PNG or SVG.

Without it, Goldilocks can still write `.mmd` Mermaid source files.

## Documentation

Documentation is available at [goldilocks-cli.org](https://goldilocks-cli.org).

## Licence

Goldilocks is authored and maintained by **Hélène Martin** and released under the MIT Licence. See the [LICENSE](LICENSE) file.
