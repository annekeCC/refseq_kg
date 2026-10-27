# RefSeq Knowledge Graph Pipeline v1.0

A BioLink-conformant Neo4j property graph built from NCBI RefSeq data for 8 model organisms, designed as a training dataset for KG embeddings, GNNs, and LLM/RAG applications.

**Scale**: 1,649,359 nodes | 4,304,520 relationships | 27.6M properties

---

## Quick Start

```bash
# 1. Install dependencies (NCBI datasets CLI, BLAST+, JDK 21, Neo4j 5.26)
bash setup.sh

# 2. Set up environment
export PATH=./deps/bin:$PATH
export JAVA_HOME=./deps/jdk-21.0.5+11
export NEO4J_HOME=./deps/neo4j-community-5.26.0

# 3. Run the full pipeline (downloads data, builds graph, imports to Neo4j, creates dump)
python run.py all
```

The full pipeline takes approximately 2-3 hours on an 8-core/32GB machine.

---

## Organisms

| Organism | Tax ID | Assembly | Genes |
|---|---|---|---|
| *Homo sapiens* | 9606 | GRCh38.p14 | 187,978 |
| *Mus musculus* | 10090 | GRCm39 | 90,960 |
| *Rattus norvegicus* | 10116 | GRCr8 | 47,338 |
| *Danio rerio* | 7955 | GRCz12ab | 53,622 |
| *Drosophila melanogaster* | 7227 | Release 6 | 17,872 |
| *Caenorhabditis elegans* | 6239 | WBcel235 | 46,926 |
| *Saccharomyces cerevisiae* S288C | 559292 | R64 | 6,477 |
| *Arabidopsis thaliana* | 3702 | TAIR10.1 | 38,312 |

Gene counts include all gene types (protein-coding, ncRNA, pseudogene, biological region, etc.) on the representative assembly.

---

## Pipeline Stages

Each stage can be run independently or as part of the full pipeline.

### `python run.py setup`
Installs all external dependencies into `./deps/`:
- NCBI Datasets CLI v18.36.0
- BLAST+ 2.16.0+ (rpsblast, blastdbcmd, makeprofiledb)
- Temurin JDK 21
- Neo4j Community Edition 5.26.0
- CDD PSSM database (downloaded and formatted for RPS-BLAST)

### `python run.py download`
Downloads gene metadata (product-report) and genome sequences (protein, rna, seq-report) for all organisms via the NCBI Datasets CLI. Handles both reference genomes (`--reference` flag) and representative genomes (downloaded by assembly accession — required for rat GRCr8 and zebrafish GRCz12ab).

### `python run.py taxonomy`
Fetches NCBI taxonomy lineages for all organism gene_taxids via the EUtils API. Builds the full lineage chain from root to each organism.

### `python run.py build`
Parses NCBI Datasets gene + product reports, hashes sequences, and emits neo4j-admin-import-compatible node/edge CSVs plus companion FASTA files. This is the core graph builder.

### `python run.py domains`
Runs RPS-BLAST of all RefSeq proteins against the CDD PSSM database, parses hits into Domain nodes + HAS_DOMAIN edges. Domain names are extracted via `blastdbcmd` (not .smp file parsing).

### `python run.py import`
Imports all node/edge CSVs into Neo4j using `neo4j-admin database import full`, applies schema (constraints + indexes), runs verification queries, and creates a database dump.

### `python run.py all`
Runs all stages in sequence: download → taxonomy → build → domains → import. Use `--skip-domains` to skip the RPS-BLAST stage.

---

## CLI Options

```
python run.py [stage] [options]

Stages:
  all         Run all stages in sequence
  setup       Install dependencies
  download    Download gene + genome data from NCBI
  taxonomy    Fetch taxonomy lineages
  build       Build graph CSVs + companion FASTA
  domains     Run RPS-BLAST domain annotation
  import      Import into Neo4j + apply schema + dump
  dump        Create Neo4j database dump (alias for import)

Global options:
  --src-dir DIR        Source data directory (default: ./refseq_src)
  --import-dir DIR     Import CSV directory (default: ./import)
  --results-dir DIR    Results directory (default: ./results)
  --threads N          CPU threads for RPS-BLAST (default: 8)
  --neo4j-home DIR     Neo4j installation (default: ./deps/neo4j)
  --java-home DIR      JDK installation (default: auto-detect)
  --datasets PATH      NCBI datasets CLI path (default: auto-detect)
  --cdd-db PATH        CDD RPS-BLAST database (default: <src-dir>/cdd/cdd_db)
  --manifest PATH      manifest.json path (default: <src-dir>/manifest.json)
  --skip-domains       Skip RPS-BLAST (for 'all' stage)
  --skip-dump          Skip dump creation (for 'import' stage)
  --version            Print version
```

---

## Output Files

### Graph CSVs (in `--import-dir`)
| File | Description |
|---|---|
| `nodes_OrganismTaxon.csv` | 131 taxonomy nodes |
| `nodes_Genome.csv` | 8 genome nodes |
| `nodes_Chromosome.csv` | 425 chromosome nodes |
| `nodes_Gene.csv` | 489,485 gene nodes |
| `nodes_Transcript.csv` | 644,412 transcript nodes |
| `nodes_Protein.csv` | 468,628 protein nodes |
| `nodes_GOTerm.csv` | 24,663 GO term nodes |
| `nodes_Domain.csv` | 21,607 protein domain nodes |
| `edges_PART_OF.csv` | 130 taxonomy tree edges |
| `edges_HAS_PART.csv` | 433 genome→chromosome edges |
| `edges_HAS_PART_domain.csv` | 267,449 protein→domain edges |
| `edges_HAS_SEQUENCE_LOCATION.csv` | 489,485 gene→chromosome edges |
| `edges_TRANSCRIBED_TO.csv` | 644,256 gene→transcript edges |
| `edges_TRANSLATES_TO.csv` | 468,628 transcript→protein edges |
| `edges_HAS_GENE_PRODUCT.csv` | 468,585 gene→protein edges |
| `edges_ORTHOLOGOUS_TO.csv` | 83,019 gene→gene ortholog edges |
| `edges_GO_*.csv` | 9 GO predicate files (~2.28M edges total) |
| `build_stats.json` | Build statistics |
| `domain_hits.tsv` | Raw RPS-BLAST hits |
| `cdd_titles.tsv` | CDD PSSM-ID-to-title mapping |

### Companion FASTA (in `--results-dir`)
| File | Size | Description |
|---|---|---|
| `refseq_proteins.faa` | ~348 MB | All 468,628 protein sequences |
| `refseq_transcripts.fna` | ~2.3 GB | All 644,412 transcript sequences |

### Neo4j Dump (in `--results-dir`)
| File | Size | Description |
|---|---|---|
| `neo4j.dump` | ~303 MB | Restorable Neo4j 5.26 database dump |

---

## Neo4j Restore

```bash
# Stop Neo4j
$NEO4J_HOME/bin/neo4j stop

# Load the dump into the default database
$NEO4J_HOME/bin/neo4j-admin database load neo4j \
  --from-path=<path-to-folder-containing-neo4j.dump> \
  --overwrite-destination=true

# Start Neo4j
$NEO4J_HOME/bin/neo4j start

# Connect at http://localhost:7474 (auth disabled)
```

### Test Queries

```cypher
// TP53 traversal
MATCH (g:Gene {symbol:'TP53'})-[:TRANSCRIBED_TO]->(t)-[:TRANSLATES_TO]->(p)
RETURN g.symbol, t.id, p.id, p.uniprotAccession LIMIT 5;

// Node counts by label
MATCH (n) RETURN labels(n)[0] AS label, count(*) AS count ORDER BY count DESC;

// GO annotations for a gene
MATCH (g:Gene {symbol:'TP53'})-[r]->(go:GOTerm)
RETURN type(r), go.name, go.aspect, r.evidenceCode LIMIT 20;

// Orthologs
MATCH (g:Gene {symbol:'TP53'})-[:ORTHOLOGOUS_TO]->(o:Gene)
RETURN o.symbol, o.id, r.groupId LIMIT 10;
```

---

## Schema Reference

### Node Types

| Label | BioLink Category | Count | Key Properties |
|---|---|---|---|
| OrganismTaxon | biolink:OrganismTaxon | 131 | id, name, rank, commonName |
| Genome | biolink:Genome | 8 | id, assemblyName, annotationName, releaseDate |
| Chromosome | biolink:Chromosome | 425 | id, sequenceName, length |
| Gene | biolink:Gene | 489,485 | id, symbol, description, geneType, orientation, synonyms, summary |
| Transcript | biolink:Transcript | 644,412 | id, name, length, md5, gc, transcriptType |
| Protein | biolink:Protein | 468,628 | id, name, length, md5, aaComposition, uniprotAccession |
| GOTerm | biolink:GeneOntologyClass | 24,663 | id, name, aspect |
| Domain | biolink:ProteinDomain | 21,607 | id, name, sourceDb |

### Edge Types

| Type | Predicate | From → To | Properties |
|---|---|---|---|
| HAS_PART | biolink:has_part | OrganismTaxon → Genome | — |
| HAS_PART | biolink:has_part | Genome → Chromosome | — |
| HAS_DOMAIN | biolink:has_part | Protein → Domain | begin, end, evalue |
| PART_OF | biolink:part_of | OrganismTaxon → OrganismTaxon | — |
| HAS_SEQUENCE_LOCATION | biolink:has_sequence_location | Gene → Chromosome | begin, end, orientation |
| TRANSCRIBED_TO | biolink:transcribed_to | Gene → Transcript | — |
| TRANSLATES_TO | biolink:translates_to | Transcript → Protein | cdsBegin, cdsEnd |
| HAS_GENE_PRODUCT | biolink:has_gene_product | Gene → Protein | — |
| ORTHOLOGOUS_TO | biolink:orthologous_to | Gene → Gene | groupId, method |
| ENABLES | biolink:enables | Gene → GOTerm | evidenceCode, qualifier, assignedBy, pmids, negated |
| ACTIVELY_INVOLVED_IN | biolink:actively_involved_in | Gene → GOTerm | evidenceCode, qualifier, assignedBy, pmids, negated |
| LOCATED_IN | biolink:located_in | Gene → GOTerm | evidenceCode, qualifier, assignedBy, pmids, negated |
| IS_ACTIVE_IN | biolink:is_active_in | Gene → GOTerm | evidenceCode, qualifier, assignedBy, pmids, negated |
| GO_PART_OF | biolink:part_of | Gene → GOTerm | evidenceCode, qualifier, assignedBy, pmids, negated |
| CONTRIBUTES_TO | biolink:contributes_to | Gene → GOTerm | evidenceCode, qualifier, assignedBy, pmids, negated |
| COLOCALIZES_WITH | biolink:colocalizes_with | Gene → GOTerm | evidenceCode, qualifier, assignedBy, pmids, negated |
| ACTS_UPSTREAM_OF | biolink:acts_upstream_of | Gene → GOTerm | evidenceCode, qualifier, assignedBy, pmids, negated |
| ACTS_UPSTREAM_OF_OR_WITHIN | biolink:acts_upstream_of_or_within | Gene → GOTerm | evidenceCode, qualifier, assignedBy, pmids, negated |

### CURIE Namespaces
- `NCBITaxon:` — NCBI Taxonomy IDs
- `NCBIGene:` — NCBI Gene IDs
- `RefSeq:` — RefSeq sequence accessions (NM_, NP_, XR_, XP_, NC_)
- `RefSeqAssembly:` — RefSeq assembly accessions (GCF_)
- `GO:` — Gene Ontology term IDs
- `CDD:` — Conserved Domain Database PSSM IDs

---

## Data Sources

- **Gene metadata, GO annotations, orthologs, genomic locations**: NCBI Datasets CLI v18.36.0 (`datasets download gene taxon <tx> --include product-report`)
- **Sequences (protein, transcript) + chromosome lengths**: NCBI Datasets CLI (`datasets download genome taxon <tx> --include protein,rna,seq-report`)
- **Protein domains**: CDD v3.21 (Conserved Domain Database) via local RPS-BLAST (e-value 1e-3, 62,456 PSSM profiles)
- **Taxonomy**: NCBI EUtils efetch (full lineage chains for all 8 organisms)

---

## Customizing the Organism Set

Edit `manifest.json` to add or remove organisms. Each entry requires:

```json
{
    "taxid": 9606,
    "scientific_name": "Homo sapiens",
    "common_name": "human",
    "assembly_accession": "GCF_000001405.40",
    "assembly_name": "GRCh38.p14",
    "refseq_category": "reference genome",
    "annotation_name": "GCF_000001405.40-RS_2025_08",
    "annotation_release_date": "2025-08-01",
    "gene_taxid": 9606,
    "gene_taxname": "Homo sapiens"
}
```

- `taxid`: NCBI taxonomy ID for the organism
- `gene_taxid`: Tax ID used for gene download (may differ from taxid for strains — e.g., yeast uses 559292 for S288C)
- `assembly_accession`: RefSeq assembly accession (GCF_ format)
- `refseq_category`: Set to `"reference genome"` to use `--reference` flag; any other value downloads by accession

---

## Known Limitations

1. **Yeast taxid**: *S. cerevisiae* genes are under taxid 559292 (S288C strain), not 4932. The manifest uses `gene_taxid` for downloads. The taxonomy tree includes both the species node (4932) and the strain node (559292).

2. **Representative vs reference assemblies**: Rat (GRCr8) and zebrafish (GRCz12ab) are "representative" not "reference" assemblies. The `--reference` flag fails for these; the pipeline downloads by assembly accession instead.

3. **Neo4j Community Edition**: Only supports a single database (`neo4j`). The pipeline imports into the default `neo4j` database. For multiple databases, use Neo4j Enterprise Edition.

4. **Gene counts**: Human and mouse gene counts in the graph exceed the manifest's `gene_counts.total` because the manifest counts don't include BIOLOGICAL_REGION genes (128K for human). The graph includes all gene types per the "all NCBI RefSeq data" scope.

5. **Bad relationships**: ~361 genes appear in product reports but are not annotated on the representative assembly. These are skipped during Neo4j import via `--skip-bad-relationships=true`.

6. **UniProt accessions**: UniProt/Swiss-Prot accessions are gene-level (from `swissProtAccessions` in the gene report), propagated to all proteins of that gene. They are not isoform-specific.

7. **CDD database**: The CDD PSSM database is ~3GB to download. The setup script handles this, but it requires sufficient disk space and time.

---

## Prerequisites

- **OS**: Linux x86_64 (Ubuntu 20.04+ recommended)
- **Python**: 3.8+ (stdlib only — no pip packages required)
- **Disk**: ~10GB free (CDD database ~3GB, genome downloads ~3GB, graph CSVs ~2GB, Neo4j ~2GB)
- **RAM**: 16GB minimum, 32GB recommended (for RPS-BLAST and Neo4j import)
- **CPU**: 4 cores minimum, 8 recommended

The `setup.sh` script installs all other dependencies automatically.
