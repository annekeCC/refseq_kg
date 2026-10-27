# RefSeq Knowledge Graph — Schema Documentation (v1.2)

## Overview

A BioLink-conformant Neo4j property graph built from NCBI RefSeq data for 22 model organisms, designed as a training dataset for KG embeddings, GNNs, and LLM/RAG applications.

**Scale**: 6,533,622 nodes | 17,482,363 relationships | 94,314,398 properties

## Organisms (22)

| Organism | Tax ID | Gene Tax ID | Assembly | Genes |
|---|---|---|---|---|
| Homo sapiens | 9606 | 9606 | GCF_000001405.40 (GRCh38.p14) | 187,978 |
| Mus musculus | 10090 | 10090 | GCF_000001635.27 (GRCm39) | 90,960 |
| Rattus norvegicus | 10116 | 10116 | GCF_036323735.1 (GRCr8) | 47,338 |
| Danio rerio | 7955 | 7955 | GCF_052040795.1 (GRCz12ab) | 53,622 |
| Drosophila melanogaster | 7227 | 7227 | GCF_000001215.4 (Release 6) | 17,872 |
| Caenorhabditis elegans | 6239 | 6239 | GCF_000002985.6 (WBcel235) | 46,926 |
| Saccharomyces cerevisiae S288C | 4932 | 559292 | GCF_000146045.2 (R64) | 6,477 |
| Arabidopsis thaliana | 3702 | 3702 | GCF_000001735.4 (TAIR10.1) | 38,312 |
| Zea mays | 4577 | 4577 | GCF_902167145.1 (Zm-B73-REFERENCE-NAM-5.0) | 49,674 |
| Triticum aestivum | 4565 | 4565 | GCF_018294505.1 (IWGSC CS RefSeq v2.1) | 155,467 |
| Oryza sativa Japonica | 4530 | 39947 | GCF_034140825.1 (AGIS1.0) | 39,384 |
| Glycine max | 3847 | 3847 | GCF_000004515.6 (Glycine_max_v4.0) | 59,048 |
| Solanum lycopersicum | 4081 | 4081 | GCF_036512215.1 (SLM_r2.1) | 41,476 |
| Solanum tuberosum | 4113 | 4113 | GCF_000226075.1 (SolTub_3.0) | 32,832 |
| Bos taurus | 9913 | 9913 | GCF_002263795.3 (ARS-UCD2.0) | 37,053 |
| Sus scrofa | 9823 | 9823 | GCF_054392235.1 (Sscrofa_HxYL_v2.0) | 39,095 |
| Gallus gallus | 9031 | 9031 | GCF_016699485.2 (GRCg7b) | 25,628 |
| Salmo salar | 8030 | 8030 | GCF_965601325.1 (fSalSal1) | 86,215 |
| Oncorhynchus mykiss | 8022 | 8022 | GCF_013265735.2 (USDA_OmykKC_1.0) | 72,796 |
| Ovis aries | 9940 | 9940 | GCF_016772045.2 (ARS-UI_Ramb_v3.0) | 35,051 |
| Capra hircus | 9925 | 9925 | GCF_001704415.1 (ARS1.1) | 28,887 |
| Vitis vinifera | 29760 | 29760 | GCF_030704535.1 (ASM3070453v1) | 29,591 |
| **Total** | | | | **1,221,682** |

Note: Gene counts include all gene types (protein-coding, ncRNA, pseudogene, biological region, etc.) on the specified assembly, per the "all NCBI RefSeq data" scope.

## Build Statistics

### Nodes (6,533,622 total)

| Label | Count | BioLink Category |
|---|---|---|
| Transcript | 1,926,824 | biolink:Transcript |
| ProteinSite | 1,871,503 | biolink:ProteinSite |
| Protein | 1,453,477 | biolink:Protein |
| Gene | 1,221,682 | biolink:Gene |
| Domain | 26,229 | biolink:ProteinDomain |
| GOTerm | 24,749 | biolink:GeneOntologyClass |
| Chromosome | 7,437 | biolink:Chromosome |
| ProteinRegion | 1,474 | biolink:ProteinRegion |
| OrganismTaxon | 225 | biolink:OrganismTaxon |
| Genome | 22 | biolink:Genome |

### Relationships (17,482,363 total)

| Type | Count | Predicate |
|---|---|---|
| HAS_DOMAIN | 4,502,740 | biolink:has_part |
| TRANSCRIBED_TO | 1,926,665 | biolink:transcribed_to |
| HAS_SITE | 1,873,433 | biolink:has_part |
| TRANSLATES_TO | 1,453,477 | biolink:translates_to |
| HAS_GENE_PRODUCT | 1,453,431 | biolink:has_gene_product |
| HAS_SEQUENCE_LOCATION | 1,221,682 | biolink:has_sequence_location |
| IN_TAXON | 1,221,682 | biolink:in_taxon |
| ACTIVELY_INVOLVED_IN | 1,077,231 | biolink:actively_involved_in |
| ENABLES | 1,002,944 | biolink:enables |
| LOCATED_IN | 691,586 | biolink:located_in |
| ORTHOLOGOUS_TO | 626,204 | biolink:orthologous_to |
| IS_ACTIVE_IN | 138,384 | biolink:is_active_in |
| ACTS_UPSTREAM_OF_OR_WITHIN | 135,545 | biolink:acts_upstream_of_or_within |
| GO_PART_OF | 134,968 | biolink:part_of |
| HAS_PART | 7,459 | biolink:has_part |
| CONTRIBUTES_TO | 6,302 | biolink:contributes_to |
| COLOCALIZES_WITH | 3,578 | biolink:colocalizes_with |
| ACTS_UPSTREAM_OF | 3,354 | biolink:acts_upstream_of |
| HAS_REGION | 1,474 | biolink:has_part |
| PART_OF | 224 | biolink:part_of |

## Node Types

### OrganismTaxon (biolink:OrganismTaxon)
- `id`: NCBITaxon:<taxid>
- `name`: scientific name
- `rank`: taxonomic rank (species, genus, family, etc.)
- `commonName`: common name (leaf taxa only)
- `category`: biolink:OrganismTaxon

### Genome (biolink:Genome)
- `id`: RefSeqAssembly:<accession>
- `assemblyName`: e.g., GRCh38.p14
- `annotationName`: RefSeq annotation name
- `releaseDate`: annotation release date
- `category`: biolink:Genome

### Chromosome (biolink:Chromosome)
- `id`: RefSeq:<accession> (e.g., RefSeq:NC_000001.11)
- `sequenceName`: chromosome name (e.g., 1, X, MT)
- `length`: sequence length (bp)
- `category`: biolink:Chromosome

### Gene (biolink:Gene)
- `id`: NCBIGene:<gene_id>
- `symbol`: gene symbol (e.g., TP53)
- `description`: full gene name
- `geneType`: protein-coding, ncRNA, pseudogene, biological region, etc.
- `orientation`: plus/minus
- `synonyms`: array of alternative symbols
- `ensemblGeneId`: Ensembl gene ID (if available)
- `omimIds`: array of OMIM IDs (human only)
- `swissprotAccessions`: array of UniProt/Swiss-Prot accessions
- `summary`: gene summary text
- `category`: biolink:Gene

### Transcript (biolink:Transcript)
- `id`: RefSeq:<accession> (e.g., RefSeq:NM_001126112.2)
- `name`: transcript name
- `length`: sequence length (nt)
- `md5`: MD5 hash of sequence
- `gc`: GC content (%)
- `transcriptType`: mRNA, ncRNA, etc.
- `selectCategory`: RefSeq select category
- `ensemblTranscript`: Ensembl transcript ID
- `category`: biolink:Transcript

### Protein (biolink:Protein)
- `id`: RefSeq:<accession> (e.g., RefSeq:NP_001119584.1)
- `name`: protein name
- `length`: sequence length (aa)
- `md5`: MD5 hash of sequence
- `aaComposition`: JSON string with per-residue counts
- `isoformName`: isoform name (if applicable)
- `ensemblProtein`: Ensembl protein ID
- `uniprotAccession`: UniProt/Swiss-Prot accession (gene-level, propagated)
- `category`: biolink:Protein

### GOTerm (biolink:GeneOntologyClass)
- `id`: GO:<go_id> (e.g., GO:0003700)
- `name`: GO term name
- `aspect`: molecular_function, biological_process, or cellular_component
- `category`: biolink:MolecularFunction | biolink:BiologicalProcess | biolink:CellularComponent

### Domain (biolink:ProteinDomain)
- `id`: CDD:<PSSM_ID> (e.g., CDD:239227)
- `name`: domain name from CDD
- `sourceDb`: CDD, Pfam, SMART, COG, PRK, TIGR, CHL
- `category`: biolink:ProteinDomain

### ProteinSite (biolink:ProteinSite) — New in v1.2
- `id`: ProteinSite:<accession>:<site_type>:<location>
- `siteType`: active, binding, DNA binding, other
- `name`: site description (e.g., "zinc binding site [ion binding]")
- `source`: CDD or RefSeq
- `dbXref`: CDD:<PSSM_ID> (if CDD-sourced)
- `location`: full GenPept location string (e.g., "order(225..226,238,248..252,286,288)")
- `category`: biolink:ProteinSite

### ProteinRegion (biolink:ProteinRegion) — New in v1.2
- `id`: ProteinRegion:<accession>:<region_name>:<begin>:<end>
- `name`: region name (e.g., "extracellular domain", "transmembrane domain")
- `source`: RefSeq
- `category`: biolink:ProteinRegion

## Edge Types

| Edge Type | Predicate | From → To | Properties |
|---|---|---|---|
| HAS_PART | biolink:has_part | OrganismTaxon → Genome | — |
| HAS_PART | biolink:has_part | Genome → Chromosome | — |
| HAS_DOMAIN | biolink:has_part | Protein → Domain | begin, end |
| HAS_SITE | biolink:has_part | Protein → ProteinSite | location |
| HAS_REGION | biolink:has_part | Protein → ProteinRegion | begin, end |
| PART_OF | biolink:part_of | OrganismTaxon → OrganismTaxon | (taxonomy tree) |
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

GO annotation edges include a `negated` boolean property for NOT-qualified annotations (e.g., "NOT enables").

**New in v1.1**: IN_TAXON edges provide direct Gene → OrganismTaxon links, enabling efficient organism-filtered queries without traversing the full taxonomy tree.

**New in v1.3**: Taxonomy lineage data is now fetched via the NCBI Datasets CLI instead of EUtils efetch. Output is verified identical (22 organisms, 573 chain entries, 0 differences), so graph content is unchanged — no rebuild was required.

**New in v1.2**: Protein domain and site annotations are now sourced from NCBI's pre-computed GenPept records (via EUtils efetch) instead of local RPS-BLAST. This adds:
- ProteinSite nodes (1,871,503) for CDD functional sites (active sites, binding sites) and RefSeq-curated sites
- ProteinRegion nodes (1,474) for RefSeq-curated functional regions (e.g., transmembrane domains, extracellular domains)
- HAS_DOMAIN edges no longer include `evalue` (NCBI's pre-computed annotations use rpsbproc filtering with curated bit-score thresholds instead of e-value cutoffs)
- UniProtKB-propagated features (curated regions, PTM sites) are excluded — only NCBI-curated (CDD + RefSeq) features are included

## Data Sources

- **Gene metadata, GO annotations, orthologs, genomic locations**: NCBI Datasets CLI v18.36.0 (`datasets download gene taxon <tx> --include product-report`)
- **Sequences (protein, transcript) + chromosome lengths**: NCBI Datasets CLI (`datasets download genome taxon <tx> --include protein,rna,seq-report`)
- **Protein domains, sites, and regions**: NCBI GenPept records via EUtils efetch (`efetch.fcgi?db=protein&rettype=gp`). NCBI pre-computes CDD domain annotations using RPS-BLAST + rpsbproc filtering with curated bit-score thresholds. Site and Region features are extracted from the GenPept FEATURES table. UniProtKB-propagated features are excluded.
- **CDD metadata**: `cddid.tbl` from NCBI FTP (`ftp.ncbi.nlm.nih.gov/pub/mmdb/cdd/cddid.tbl.gz`) for PSSM_ID → accession/sourceDb mapping
- **Taxonomy**: NCBI Datasets CLI (full lineage chains for all 22 organisms; v1.3 — previously EUtils efetch, output verified identical)

## Companion Files

- `refseq_proteins.faa`: All 1,526,107 protein sequences (FASTA, ~938 MB)
- `refseq_transcripts.fna`: All 2,033,819 transcript sequences from 22 organisms (FASTA, ~6.0 GB)
- `neo4j.dump`: Neo4j database dump (restorable via `neo4j-admin database load`)
- `import/`: Neo4j-admin import-ready CSVs + schema.cypher + build_stats.json
- `pipeline_v1.3/`: Complete pipeline scripts (setup, download, taxonomy via Datasets, build, genpept fetch, import)
- `pipeline_v1.2/`: Previous pipeline (taxonomy via EUtils; otherwise identical to v1.3)

## CURIE Namespaces

- `NCBITaxon:` — NCBI Taxonomy IDs
- `NCBIGene:` — NCBI Gene IDs
- `RefSeq:` — RefSeq sequence accessions (NM_, NP_, XR_, XP_, NC_)
- `RefSeqAssembly:` — RefSeq assembly accessions (GCF_)
- `GO:` — Gene Ontology term IDs
- `CDD:` — Conserved Domain Database PSSM IDs
- `ProteinSite:` — Protein functional site identifiers (v1.2)
- `ProteinRegion:` — Protein curated region identifiers (v1.2)

## Neo4j Restore Instructions

The dump was created with Neo4j Community Edition 5.26.0, which uses the default `neo4j` database.

```bash
# Stop Neo4j
neo4j stop

# Load the dump into the default database
neo4j-admin database load neo4j --from-path=<path-to-dump-file> --overwrite-destination=true

# Start Neo4j
neo4j start

# Query (auth disabled in this build)
cypher-shell "MATCH (g:Gene {symbol:'TP53'})-[:TRANSCRIBED_TO]->(t)-[:TRANSLATES_TO]->(p) RETURN g.symbol, t.id, p.id, p.uniprotAccession LIMIT 5;"
```

Alternatively, to build from CSVs:

```bash
neo4j-admin database import full neo4j --overwrite-destination=true \
  --skip-bad-relationships=true --skip-duplicate-nodes=true \
  --nodes=import/nodes_Gene.csv --nodes=import/nodes_Transcript.csv \
  ... (all node and edge CSVs)
cypher-shell --file=schema.cypher
```
