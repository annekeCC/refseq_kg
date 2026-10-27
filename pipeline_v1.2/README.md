# RefSeq Knowledge Graph Pipeline v1.2

A BioLink-conformant Neo4j property graph built from NCBI RefSeq data for 22 model organisms, designed as a training dataset for KG embeddings, GNNs, and LLM/RAG applications.

**Scale**: 6,533,622 nodes | 17,482,363 relationships | 94,314,398 properties

---

## What's New in v1.2

- **Protein features from NCBI GenPept records**: domains, functional sites, and curated regions are now parsed directly from NCBI's pre-computed GenPept annotations (fetched via EUtils efetch), replacing the local RPS-BLAST stage
- **RPS-BLAST retired**: no BLAST+ install, no 36GB CDD PSSM database, no 12-15h search step. NCBI's rpsbproc pipeline applies curated bit-score thresholds — more stringent than our previous e-value 1e-3 cutoff
- **New node types**: `ProteinSite` (1,871,503 — CDD functional sites + RefSeq-curated PTM sites) and `ProteinRegion` (1,474 — RefSeq-curated regions such as repeats, transmembrane regions, zinc fingers)
- **New edges**: `HAS_DOMAIN` (4,502,740), `HAS_SITE` (1,873,433), `HAS_REGION` (1,474) — all with `biolink:` predicates
- **UniProtKB-propagated features excluded** (324,826 features skipped): only NCBI-curated (CDD + RefSeq) annotations are included
- **HAS_DOMAIN edges no longer carry `evalue`** — NCBI's pre-computed annotations don't publish e-values; edge properties are `begin` and `end` only

---

## Pipeline Stages

```
download  ->  taxonomy  ->  build  ->  fetch-genpept  ->  parse-genpept  ->  import (+ dump)
```

| Stage | Script | What it does |
|---|---|---|
| `download` | `download.py` | Download gene, genome, and protein data from NCBI (datasets CLI) |
| `taxonomy` | `taxonomy.py` | Fetch taxonomy lineages from EUtils |
| `build` | `build_graph.py` | Build base graph CSVs: Gene, Transcript, Protein, GOTerm, orthologs, taxonomy |
| `fetch-genpept` | `fetch_genpept.py` | Fetch all 1,453,477 GenPept records via EUtils efetch (10 parallel workers, 500 accessions/request, ~2,907 batches) |
| `parse-genpept` | `parse_genpept.py` | Parse GenPept FEATURES tables into Domain, ProteinSite, ProteinRegion nodes + HAS_DOMAIN/HAS_SITE/HAS_REGION edges |
| `import` | `neo4j_import.sh` | `neo4j-admin database import full` with all 30 CSVs, apply `schema.cypher`, verify, dump |

Run everything:

```bash
export NCBI_API_KEY=<your key>   # 10 req/sec with key vs 3 without
python run.py all
```

Or stage by stage:

```bash
python run.py download
python run.py taxonomy
python run.py build
python run.py fetch-genpept
python run.py parse-genpept
python run.py import
```

---

## Feature Extraction Logic (parse_genpept.py)

Each GenPept Region/Site feature is classified:

| Feature | CDD db_xref? | UniProtKB-propagated? | Result |
|---|---|---|---|
| Region | yes | — | `Domain` node (id=`CDD:<PSSM_ID>`, name/sourceDb from cddid.tbl) + `HAS_DOMAIN` edge |
| Region | no | no | `ProteinRegion` node (source=RefSeq) + `HAS_REGION` edge |
| Site | yes | — | `ProteinSite` node (source=CDD) + `HAS_SITE` edge |
| Site | no | no | `ProteinSite` node (source=RefSeq) + `HAS_SITE` edge |
| any | — | yes | **skipped** (UniProtKB-curated, out of scope) |

Domain names and sourceDb (Pfam, SMART, COG, PRK, TIGR, CHL, KOG, CDD) are resolved via `cddid.tbl` (PSSM_ID → accession/name mapping, downloaded by `setup.sh`).

Location parsing handles `80..283`, `<224..313`, `order(...)`, `join(...)`, `complement(...)`, and single positions; `<`/`>` are stripped and min/max coordinates extracted.

---

## Requirements

- Python 3.10+
- NCBI datasets CLI
- JDK (17 or 21 recommended; v1.2 was built with conda Java 23 — Neo4j 5.26 works despite the "unsupported runtime" warning)
- Neo4j Community Edition 5.26.0
- NCBI API key (set `NCBI_API_KEY`; without it EUtils limits you to 3 req/sec instead of 10)

Install:

```bash
bash setup.sh   # datasets CLI, JDK, Neo4j, cddid.tbl — no BLAST+ needed
```

---

## Outputs

- `import/` — 30 CSVs (10 node files, 20 edge files) for `neo4j-admin import`
- `results/refseq_proteins.faa`, `results/refseq_transcripts.fna` — companion FASTA files
- `neo4j.dump` — restorable database dump (`neo4j-admin database load`)

## Verification

After import, `neo4j_import.sh` runs automated checks: node/edge counts per label/type, TP53 traversal (domains + sites), missing-category/missing-predicate counts, and species count. See `verify.cypher` for the full query set.

## Legacy Versions

- `pipeline_v1.0/`, `pipeline_v1.1/` — earlier pipelines (v1.1 used local RPS-BLAST against CDD; kept for reference only)
