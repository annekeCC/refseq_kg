# RefSeq Knowledge Graph v1.3 — Share Package

A BioLink-conformant Neo4j property graph built from NCBI RefSeq data for 22 model organisms, designed as a training dataset for KG embeddings, GNNs, and LLM/RAG applications.

This project was developed using Biomni.

**Scale**: 6,533,622 nodes | 17,482,363 relationships | 94,314,398 properties | 22 organisms

---

## Contents

| Path | What it is |
|---|---|
| `neo4j.dump` | Restorable Neo4j database dump (975 MB) — fastest way to get the graph |
| `import/` | 30 CSVs (10 node files, 20 edge files) for `neo4j-admin database import full` — rebuild path |
| `refseq_proteins.faa` | 1,526,107 RefSeq protein sequences (938 MB) |
| `refseq_transcripts.fna` | 2,033,819 RefSeq transcript sequences (6.0 GB) |
| `SCHEMA.md` | Full node/edge model documentation with all properties |
| `refseq_kg_schema.png` | Schema diagram (current, v1.3) |
| `refseq_kg_schema_v1.2.png` | Schema diagram (previous release, archived) |
| `example_cypher_queries.md` | Curated Cypher query collection |
| `use_cases.md` | Downstream use cases (KG embeddings, function prediction, RAG, ...) |
| `annotation_coverage_report.md` | Per-organism annotation coverage metrics |
| `build_stats.json` | Machine-readable node/edge/property counts |
| `pipeline_v1.3/` | Current pipeline source (see its README.md) |
| `pipeline_v1.0/` – `pipeline_v1.2/` | Legacy pipeline versions, kept for reference |

### Data files not in this repository

`neo4j.dump`, `refseq_proteins.faa`, `refseq_transcripts.fna`, and the large `import/*.csv` files (about 10.7 GB in total) exceed GitHub's file-size limits and are excluded via `.gitignore`. They are distributed separately from the full share package; to regenerate them locally, follow "Rebuild from NCBI" below.

## Quick Start: Load the Graph

Requires Neo4j Community Edition 5.26.x (JDK 17 or 21).

```bash
# From the dump (recommended):
neo4j-admin database load neo4j --from-dump=neo4j.dump
neo4j start

# Or rebuild from the CSVs (see pipeline_v1.3/neo4j_import.sh):
neo4j-admin database import full neo4j --overwrite-destination=true \
  --nodes=import/nodes_*.csv --relationships=import/edges_*.csv
```

The dump was created with auth disabled (`dbms.security.auth_enabled=false`). Add auth before exposing the database to any network.

## Quick Start: Rebuild from NCBI (optional)

```bash
cd pipeline_v1.3
bash setup.sh                      # datasets CLI, JDK, Neo4j, cddid.tbl
export NCBI_API_KEY=<your key>     # 10 req/sec vs 3 without
python run.py all                  # download -> taxonomy -> build -> fetch-genpept -> parse-genpept -> import
```

See `pipeline_v1.3/README.md` for stage details.

## Version History

- **v1.3** — taxonomy lineages via NCBI Datasets CLI (verified identical output to v1.2's EUtils feed; graph content unchanged)
- **v1.2** — protein domains, sites, and regions from NCBI's pre-computed GenPept annotations (ProteinSite, ProteinRegion nodes); local RPS-BLAST retired; UniProtKB-propagated features excluded
- **v1.1** — 22 organisms; direct `IN_TAXON` edges; updated assemblies
- **v1.0** — initial 8-organism build

## Data Sources

NCBI Datasets CLI v18.36.0 (gene metadata, GO, orthologs, sequences, taxonomy) | NCBI GenPept via EUtils efetch (domains, sites, regions) | CDD v3.21 (cddid.tbl). Only NCBI-curated annotations are included; UniProtKB-propagated features are excluded by design.
