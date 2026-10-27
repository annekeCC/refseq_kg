# RefSeq Knowledge Graph Pipeline v1.1

A BioLink-conformant Neo4j property graph built from NCBI RefSeq data for 22 model organisms, designed as a training dataset for KG embeddings, GNNs, and LLM/RAG applications.

**Scale**: ~3.9M nodes | ~10.5M relationships | ~70M properties

---

## What's New in v1.1

- **22 organisms** (up from 8): added 6 plants (maize, wheat, rice, soybean, tomato, potato), 6 livestock (cattle, pig, chicken, sheep, goat, grape), and 2 fish (Atlantic salmon, rainbow trout)
- **IN_TAXON edges**: direct `Gene → OrganismTaxon` edges using `biolink:in_taxon` predicate (1.22M edges)
- **Updated assemblies**: rat GRCr8, zebrafish GRCz12ab, rice AGIS1.0, tomato SLM_r2.1, pig Sscrofa_HxYL_maternal_Yorkshire_Landrace_v2.0, goat ARS1.1, grape ASM3070453v1
- **Parallel RPS-BLAST**: 4-process parallel search for faster domain annotation
- **626K ortholog edges** (up from 83K) due to expanded organism set
- **Fixed domain annotation**: CDD node IDs use saccver directly (no double `CDD:` prefix); sourceDb detected from accession prefix

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

The full pipeline takes approximately 12-15 hours on an 8-core/32GB machine (RPS-BLAST is the bottleneck).

---

## Organisms

| Organism | Tax ID | Gene Tax ID | Assembly | Genes |
|---|---|---|---|---|
| *Homo sapiens* | 9606 | 9606 | GRCh38.p14 | 187,978 |
| *Mus musculus* | 10090 | 10090 | GRCm39 | 90,960 |
| *Rattus norvegicus* | 10116 | 10116 | GRCr8 | 47,338 |
| *Danio rerio* | 7955 | 7955 | GRCz12ab | 53,622 |
| *Drosophila melanogaster* | 7227 | 7227 | Release 6 plus ISO1 MT | 17,872 |
| *Caenorhabditis elegans* | 6239 | 6239 | WBcel235 | 46,926 |
| *Saccharomyces cerevisiae* S288C | 4932 | 559292 | R64 | 6,477 |
| *Arabidopsis thaliana* | 3702 | 3702 | TAIR10.1 | 38,312 |
| *Zea mays* | 4577 | 4577 | Zm-B73-REFERENCE-NAM-5.0 | 49,674 |
| *Triticum aestivum* | 4565 | 4565 | IWGSC CS RefSeq v2.1 | 155,467 |
| *Oryza sativa* Japonica | 4530 | 39947 | AGIS1.0 | 39,384 |
| *Glycine max* | 3847 | 3847 | Glycine_max_v4.0 | 59,048 |
| *Solanum lycopersicum* | 4081 | 4081 | SLM_r2.1 | 41,476 |
| *Solanum tuberosum* | 4113 | 4113 | SolTub_3.0 | 32,832 |
| *Bos taurus* | 9913 | 9913 | ARS-UCD2.0 | 37,053 |
| *Sus scrofa* | 9823 | 9823 | Sscrofa_HxYL_maternal_Yorkshire_Landrace_v2.0 | 39,095 |
| *Gallus gallus* | 9031 | 9031 | bGalGal1.mat.broiler.GRCg7b | 25,628 |
| *Salmo salar* | 8030 | 8030 | fSalSal1 | 86,215 |
| *Oncorhynchus mykiss* | 8022 | 8022 | USDA_OmykKC_1.0 | 72,796 |
| *Ovis aries* | 9940 | 9940 | ARS-UI_Ramb_v3.0 | 35,051 |
| *Capra hircus* | 9925 | 9925 | ARS1.1 | 28,887 |
| *Vitis vinifera* | 29760 | 29760 | ASM3070453v1 | 29,591 |

**Total**: 1,221,682 genes | 1,453,477 proteins | 1,926,824 transcripts

Gene counts include all gene types (protein-coding, ncRNA, pseudogene, biological region, etc.) on the specified assembly.

---

## Pipeline Stages

Each stage can be run independently or as part of the full pipeline.

### `python run.py setup`
Installs all external dependencies into `./deps/`:
- NCBI Datasets CLI v18.36.0
- BLAST+ 2.16.0+ (rpsblast, blastdbcmd, makeprofiledb)
- Temurin JDK 21
- Neo4j Community Edition 5.26.0
- CDD PSSM database (downloaded and formatted for RPS-BLAST, ~36GB)

### `python run.py download`
Downloads gene metadata (product-report) and genome sequences (protein, rna, seq-report) for all organisms via the NCBI Datasets CLI. Handles both reference genomes (`--reference` flag) and representative genomes (downloaded by assembly accession).

### `python run.py taxonomy`
Fetches NCBI taxonomy lineages for all organism gene_taxids via the EUtils API. Builds the full lineage chain from root to each organism.

### `python run.py build`
Parses NCBI Datasets gene + product reports, hashes sequences, and emits neo4j-admin-import-compatible node/edge CSVs plus companion FASTA files. Emits IN_TAXON edges (Gene → OrganismTaxon) in addition to all v1.0 edge types.

### `python run.py domains`
Runs RPS-BLAST of all RefSeq proteins against the CDD PSSM database, parses hits into Domain nodes + HAS_DOMAIN edges. Domain names are extracted via `blastdbcmd` (not .smp file parsing). For large protein sets, use `run_rpsblast_parallel.sh` for 4-process parallel execution.

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
| `nodes_OrganismTaxon.csv` | 224 taxonomy nodes |
| `nodes_Genome.csv` | 22 genome nodes |
| `nodes_Chromosome.csv` | 7,437 chromosome nodes |
| `nodes_Gene.csv` | 1,221,682 gene nodes |
| `nodes_Transcript.csv` | 1,926,824 transcript nodes |
| `nodes_Protein.csv` | 1,453,477 protein nodes |
| `nodes_GOTerm.csv` | 24,749 GO term nodes |
| `nodes_Domain.csv` | Domain nodes (from RPS-BLAST) |
| `edges_PART_OF.csv` | 223 taxonomy tree edges |
| `edges_HAS_PART.csv` | 7,459 genome→chromosome edges |
| `edges_HAS_PART_domain.csv` | protein→domain edges (from RPS-BLAST) |
| `edges_HAS_SEQUENCE_LOCATION.csv` | 1,221,682 gene→chromosome edges |
| `edges_TRANSCRIBED_TO.csv` | 1,926,828 gene→transcript edges |
| `edges_TRANSLATES_TO.csv` | 1,453,477 transcript→protein edges |
| `edges_HAS_GENE_PRODUCT.csv` | 1,453,477 gene→protein edges |
| `edges_IN_TAXON.csv` | 1,221,682 gene→taxon edges |
| `edges_ORTHOLOGOUS_TO.csv` | 626,204 gene→gene ortholog edges |
| `edges_GO_*.csv` | 9 GO predicate files (~3.19M edges total) |
| `build_stats.json` | Build statistics |
| `domain_hits.tsv` | Raw RPS-BLAST hits |

### Companion FASTA (in `--results-dir`)
| File | Size | Description |
|---|---|---|
| `refseq_proteins.faa` | ~938 MB | All 1,526,107 protein sequences |
| `refseq_transcripts.fna` | ~6.4 GB | All 1,926,824 transcript sequences |

### Neo4j Dump (in `--results-dir`)
| File | Description |
|---|---|
| `neo4j.dump` | Restorable Neo4j 5.26 database dump |

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
RETURN o.symbol, o.id LIMIT 10;

// IN_TAXON: find all genes in a specific organism
MATCH (g:Gene)-[:IN_TAXON]->(t:OrganismTaxon {id: 'NCBITaxon:9606'})
RETURN count(g) AS human_genes;

// Domain annotation for a protein
MATCH (p:Protein {id: 'RefSeq:NP_000537.3'})-[r:HAS_DOMAIN]->(d:Domain)
RETURN d.name, d.sourceDb, r.begin, r.end, r.evalue;
```

---

## Schema Reference

### Node Types

| Label | BioLink Category | Count | Key Properties |
|---|---|---|---|
| OrganismTaxon | biolink:OrganismTaxon | 224 | id, name, rank, commonName |
| Genome | biolink:Genome | 22 | id, assemblyName, annotationName, releaseDate |
| Chromosome | biolink:Chromosome | 7,437 | id, sequenceName, length |
| Gene | biolink:Gene | 1,221,682 | id, symbol, description, geneType, orientation, synonyms, summary |
| Transcript | biolink:Transcript | 1,926,824 | id, name, length, md5, gc, transcriptType |
| Protein | biolink:Protein | 1,453,477 | id, name, length, md5, aaComposition, uniprotAccession |
| GOTerm | biolink:GeneOntologyClass | 24,749 | id, name, aspect |
| Domain | biolink:ProteinDomain | (from RPS-BLAST) | id, name, sourceDb |

### Edge Types

| Type | Predicate | From → To | Properties |
|---|---|---|---|
| HAS_PART | biolink:has_part | OrganismTaxon → Genome | — |
| HAS_PART | biolink:has_part | Genome → Chromosome | — |
| HAS_DOMAIN | biolink:has_part | Protein → Domain | begin, end, evalue |
| PART_OF | biolink:part_of | OrganismTaxon → OrganismTaxon | — |
| IN_TAXON | biolink:in_taxon | Gene → OrganismTaxon | — |
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
- **Protein domains**: CDD v3.21 (Conserved Domain Database) via local RPS-BLAST (e-value 1e-3, max_target_seqs 5)
- **Taxonomy**: NCBI EUtils efetch (full lineage chains for all 22 organisms)

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
- `gene_taxid`: Tax ID used for gene download (may differ from taxid for strains — e.g., yeast uses 559292 for S288C, rice uses 39947 for Japonica Group)
- `assembly_accession`: RefSeq assembly accession (GCF_ format)
- `refseq_category`: Set to `"reference genome"` to use `--reference` flag; any other value downloads by accession

---

## Known Limitations

1. **`datasets download gene taxon` does NOT search child taxa**: Returns only genes directly registered under the given taxid. Many organisms need subspecies/strain-level taxids for nuclear gene annotations (e.g., yeast 559292, rice 39947).

2. **Assembly filtering**: The build script filters genes by `assemblyAccession` from the gene report. Genes annotated on alternative assemblies or older assembly versions are excluded. This results in slightly fewer genes than the raw data_report count (1,221,682 vs 1,265,840).

3. **Rice gene_taxid**: Taxon 4530 (Oryza sativa) only has 217 organellar genes. Nuclear genes are under taxon 39947 (Oryza sativa Japonica Group).

4. **Goat assembly version**: Genes annotated on GCF_001704415.1 (ARS1.1) but genome downloaded for GCF_001704415.2 (ARS1.2). Chromosome accessions are identical between versions.

5. **Neo4j Community Edition**: Only supports a single database (`neo4j`). The pipeline imports into the default `neo4j` database.

6. **UniProt accessions**: UniProt/Swiss-Prot accessions are gene-level (from `swissProtAccessions` in the gene report), propagated to all proteins of that gene. They are not isoform-specific.

7. **CDD database**: The CDD PSSM database is ~36GB when formatted for RPS-BLAST (25 volumes). The setup script handles download and formatting, but requires ~40GB free disk space.

8. **RPS-BLAST runtime**: Domain annotation of 1.5M proteins against the 36GB CDD database takes ~10-12 hours on an 8-core machine. The `run_rpsblast_parallel.sh` script splits proteins into 4 chunks for parallel processing.

9. **S3 mount limitations**: The transcript FASTA (6.4GB) cannot be copied directly to S3-backed results directories via Python `shutil.copy`. Use shell `cp` or copy in chunks.

---

## Prerequisites

- **OS**: Linux x86_64 (Ubuntu 20.04+ recommended)
- **Python**: 3.8+ (stdlib only — no pip packages required)
- **Disk**: ~50GB free (CDD database ~36GB, genome downloads ~5GB, graph CSVs ~3GB, Neo4j ~2GB, companion FASTA ~7GB)
- **RAM**: 32GB recommended (for RPS-BLAST and Neo4j import)
- **CPU**: 8 cores recommended (for parallel RPS-BLAST)

The `setup.sh` script installs all other dependencies automatically.
