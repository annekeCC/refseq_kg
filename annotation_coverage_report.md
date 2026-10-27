# RefSeq Knowledge Graph — Annotation Coverage Report

**Generated**: 2026-09-16 (v1.2)
**Graph version 1.2
**Source**: NCBI RefSeq, 22 model organisms
**Query engine**: Neo4j 5.26.0 Community Edition
**Scope**: All NCBI-provided annotation types, including NCBI GenPept protein feature annotations (domains, sites, regions)

---

## 0. Graph Overview

### Node counts

| Label | Count |
|---|---|
| Transcript | 1,926,824 |
| ProteinSite | 1,871,503 |
| Protein | 1,453,477 |
| Gene | 1,221,682 |
| Domain | 26,229 |
| GOTerm | 24,749 |
| Chromosome | 7,437 |
| ProteinRegion | 1,474 |
| OrganismTaxon | 225 |
| Genome | 22 |
| **Total** | **6,533,622** |

### Edge counts

| Type | Count |
|---|---|
| HAS_DOMAIN | 4,502,740 |
| TRANSCRIBED_TO | 1,926,665 |
| HAS_SITE | 1,873,433 |
| TRANSLATES_TO | 1,453,477 |
| HAS_GENE_PRODUCT | 1,453,431 |
| HAS_SEQUENCE_LOCATION | 1,221,682 |
| IN_TAXON | 1,221,682 |
| ACTIVELY_INVOLVED_IN | 1,077,231 |
| ENABLES | 1,002,944 |
| LOCATED_IN | 691,586 |
| ORTHOLOGOUS_TO | 626,204 |
| IS_ACTIVE_IN | 138,384 |
| ACTS_UPSTREAM_OF_OR_WITHIN | 135,545 |
| GO_PART_OF | 134,968 |
| HAS_PART | 7,459 |
| CONTRIBUTES_TO | 6,302 |
| COLOCALIZES_WITH | 3,578 |
| ACTS_UPSTREAM_OF | 3,354 |
| HAS_REGION | 1,474 |
| PART_OF | 224 |
| **Total** | **17,482,363** |

---

## 1. Overview: What Counts as Annotation

NCBI provides many layers of annotation beyond Gene Ontology terms. This report assesses coverage across **10 annotation types** present in the knowledge graph, all sourced from NCBI data:

| # | Annotation type | Source | Graph location |
|---|---|---|---|
| 1 | Gene symbol | NCBI Gene nomenclature | Gene.symbol |
| 2 | Gene description | NCBI Gene descriptive text | Gene.description |
| 3 | Gene summary | NCBI curated functional summary | Gene.summary |
| 4 | Gene synonyms | NCBI alternative names | Gene.synonyms |
| 5 | GO terms | NCBI gene2go (9 predicates) | Gene → GOTerm edges |
| 6 | Protein domains | NCBI pre-computed CDD (GenPept) | Protein → Domain edges |
| 6b | Protein sites | NCBI pre-computed CDD + RefSeq curation (GenPept) | Protein → ProteinSite edges |
| 6c | Protein regions | RefSeq curation (GenPept) | Protein → ProteinRegion edges |
| 7 | Orthologs | NCBI Ortholog | Gene → Gene edges |
| 8 | OMIM IDs | NCBI OMIM cross-reference | Gene.omimIds |
| 9 | Swiss-Prot accessions | NCBI UniProt cross-reference | Gene.swissprotAccessions |
| 10 | Protein name | NCBI RefSeq protein annotation | Protein.name |

All metrics are computed for **protein-coding genes only** (the meaningful comparison set). Non-coding genes (ncRNA, tRNA, pseudogene, etc.) typically do not receive functional annotations by design.

**Core annotation depth score**: For each protein-coding gene, we count how many of 6 core types are present: symbol, description, summary, GO terms, protein domains, orthologs. This gives a 0–6 depth score per gene.

---

## 2. Per-Organism Annotation Coverage Matrix

Percentage of protein-coding genes with each annotation type present:

| Organism | PC genes | Symbol | Desc | Summary | Synonyms | GO | Domain | Ortholog | OMIM | SwissProt | Prot name |
|---|---|---|---|---|---|---|---|---|---|---|---|
| *Homo sapiens* | 20,127 | 100.0 | 100.0 | 93.9 | 84.6 | 93.8 | 94.8 | 58.9 | 83.5 | 95.8 | 99.7 |
| *Mus musculus* | 22,339 | 100.0 | 100.0 | 92.4 | 88.0 | 91.6 | 93.4 | 60.4 | — | 75.9 | 97.9 |
| *Rattus norvegicus* | 23,114 | 100.0 | 100.0 | 90.8 | 55.6 | 86.6 | 83.1 | 65.2 | — | 35.1 | 85.7 |
| *Danio rerio* | 28,486 | 100.0 | 100.0 | 73.3 | 64.9 | 70.9 | 55.0 | 35.6 | — | 11.7 | 99.7 |
| *Drosophila melanogaster* | 13,986 | 100.0 | 100.0 | 86.6 | 100.0 | 91.2 | 82.2 | 0.0 | — | — | 99.9 |
| *Caenorhabditis elegans* | 19,983 | 100.0 | 100.0 | 74.9 | 0.0 | 58.9 | 72.7 | 0.0 | — | — | 99.9 |
| *Saccharomyces cerevisiae* | 6,021 | 100.0 | 100.0 | 95.2 | 33.8 | 99.8 | 85.9 | 0.0 | — | — | 99.7 |
| *Arabidopsis thaliana* | 27,562 | 100.0 | 100.0 | 31.6 | 76.8 | 99.1 | 83.3 | 0.0 | — | — | 99.6 |
| *Zea mays* | 34,265 | 100.0 | 100.0 | 0.0 | 77.6 | 67.9 | 83.4 | 0.0 | — | 1.7 | 99.3 |
| *Triticum aestivum* | 103,803 | 100.0 | 100.0 | 0.0 | 2.7 | 69.8 | 84.5 | 0.0 | — | 0.2 | 100.0 |
| *Oryza sativa* | 29,726 | 100.0 | 100.0 | 0.0 | 30.8 | 71.3 | 85.9 | 0.0 | — | 11.8 | 98.3 |
| *Glycine max* | 47,136 | 100.0 | 100.0 | 0.0 | 4.7 | 74.2 | 88.8 | 0.0 | — | 0.7 | 99.5 |
| *Solanum lycopersicum* | 28,683 | 100.0 | 100.0 | 0.1 | 5.3 | 70.6 | 86.8 | 0.0 | — | 1.2 | 98.5 |
| *Solanum tuberosum* | 28,411 | 100.0 | 100.0 | 0.0 | 1.8 | 73.0 | 89.7 | 0.0 | — | 0.6 | 99.7 |
| *Bos taurus* | 21,685 | 100.0 | 100.0 | 5.5 | 21.8 | 89.1 | 94.9 | 60.8 | — | 27.3 | 99.4 |
| *Sus scrofa* | 22,117 | 100.0 | 100.0 | 0.1 | 14.1 | 84.8 | 91.9 | 74.1 | — | 6.2 | 99.8 |
| *Gallus gallus* | 18,106 | 100.0 | 100.0 | 0.4 | 28.9 | 83.9 | 91.6 | 68.2 | — | 11.9 | 99.4 |
| *Salmo salar* | 43,038 | 100.0 | 100.0 | 0.0 | 17.5 | 86.5 | 94.7 | 19.0 | — | 0.3 | 99.3 |
| *Oncorhynchus mykiss* | 41,956 | 100.0 | 100.0 | 0.0 | 9.3 | 85.6 | 94.5 | 18.2 | — | 0.3 | 99.8 |
| *Ovis aries* | 21,309 | 100.0 | 100.0 | 0.0 | 10.5 | 88.6 | 95.9 | 76.9 | — | 1.8 | 99.8 |
| *Capra hircus* | 20,598 | 100.0 | 100.0 | 0.0 | 8.6 | 89.0 | 96.1 | 79.3 | — | 0.5 | 99.6 |
| *Vitis vinifera* | 25,257 | 100.0 | 100.0 | 0.0 | 9.3 | 76.1 | 90.2 | 0.0 | — | 0.3 | 99.1 |

OMIM is human-only by design (— = not applicable). All values are percentages unless noted.

---

## 3. Annotation Depth Distribution

For each protein-coding gene, the depth score counts how many of 6 core annotation types are present: symbol, description, summary, GO, domains, orthologs. Since symbol and description are universal, the practical range is 2–6.

| Organism | Depth 2 | Depth 3 | Depth 4 | Depth 5 | Depth 6 | Max depth |
|---|---|---|---|---|---|---|
| *Homo sapiens* | 437 (2.2%) | 451 (2.2%) | 613 (3.0%) | 7,441 (37.0%) | 11,185 (55.6%) | 6 |
| *Mus musculus* | 346 (1.5%) | 1,216 (5.4%) | 1,032 (4.6%) | 6,814 (30.5%) | 12,931 (57.9%) | 6 |
| *Rattus norvegicus* | 1,702 (7.4%) | 738 (3.2%) | 1,465 (6.3%) | 5,218 (22.6%) | 13,991 (60.5%) | 6 |
| *Danio rerio* | 6,058 (21.3%) | 1,581 (5.6%) | 4,071 (14.3%) | 9,941 (34.9%) | 6,835 (24.0%) | 6 |
| *Drosophila melanogaster* | 515 (3.7%) | 1,308 (9.4%) | 1,436 (10.3%) | 10,727 (76.7%) | — | 5 |
| *Caenorhabditis elegans* | 3,137 (15.7%) | 3,203 (16.0%) | 2,874 (14.4%) | 10,769 (53.9%) | — | 5 |
| *Saccharomyces cerevisiae* | 12 (0.2%) | 241 (4.0%) | 636 (10.6%) | 5,132 (85.2%) | — | 5 |
| *Arabidopsis thaliana* | 154 (0.6%) | 3,880 (14.1%) | 15,486 (56.2%) | 8,042 (29.2%) | — | 5 |
| *Zea mays* | 4,839 (14.1%) | 7,018 (20.5%) | 22,408 (65.4%) | — | — | 4 |
| *Triticum aestivum* | 13,628 (13.1%) | 20,179 (19.4%) | 69,996 (67.4%) | — | — | 4 |
| *Oryza sativa* | 3,501 (11.8%) | 5,719 (19.2%) | 20,505 (69.0%) | 1 (0.0%) | — | 5 |
| *Glycine max* | 4,126 (8.8%) | 9,142 (19.4%) | 33,868 (71.9%) | — | — | 4 |
| *Solanum lycopersicum* | 2,851 (9.9%) | 6,517 (22.7%) | 19,283 (67.2%) | 32 (0.1%) | — | 5 |
| *Solanum tuberosum* | 2,284 (8.0%) | 6,035 (21.2%) | 20,092 (70.7%) | — | — | 4 |
| *Bos taurus* | 520 (2.4%) | 999 (4.6%) | 7,298 (33.7%) | 12,789 (59.0%) | 79 (0.4%) | 6 |
| *Sus scrofa* | 1,324 (6.0%) | 687 (3.1%) | 5,513 (24.9%) | 14,583 (65.9%) | 10 (0.0%) | 6 |
| *Gallus gallus* | 1,089 (6.0%) | 1,080 (6.0%) | 4,766 (26.3%) | 11,115 (61.4%) | 56 (0.3%) | 6 |
| *Salmo salar* | 1,511 (3.5%) | 4,088 (9.5%) | 30,297 (70.4%) | 7,142 (16.6%) | — | 5 |
| *Oncorhynchus mykiss* | 1,638 (3.9%) | 4,140 (9.9%) | 29,458 (70.2%) | 6,720 (16.0%) | — | 5 |
| *Ovis aries* | 348 (1.6%) | 699 (3.3%) | 5,788 (27.2%) | 14,468 (67.9%) | 6 (0.0%) | 6 |
| *Capra hircus* | 332 (1.6%) | 575 (2.8%) | 5,199 (25.2%) | 14,486 (70.3%) | 6 (0.0%) | 6 |
| *Vitis vinifera* | 1,997 (7.9%) | 4,528 (17.9%) | 18,732 (74.2%) | — | — | 4 |

---

## 4. Domain Annotation Detail (NCBI pre-computed CDD)

Domain annotations from NCBI's pre-computed GenPept records (rpsbproc pipeline against the NCBI Conserved Domain Database), covering ALL proteins from all 22 organisms. No local RPS-BLAST was run; NCBI applies curated bit-score thresholds via rpsbproc.

### Per-organism domain coverage

| Organism | Proteins | Proteins with domains | Coverage | Total domain hits | Avg domains/protein |
|---|---|---|---|---|---|
| *Homo sapiens* | 136,698 | 130,926 | 95.8% | 551,963 | 4.2 |
| *Mus musculus* | 95,639 | 91,528 | 95.7% | 382,862 | 4.2 |
| *Rattus norvegicus* | 28,657 | 27,625 | 96.4% | 102,516 | 3.7 |
| *Danio rerio* | 93,982 | 18,451 | 19.6% | 61,197 | 3.3 |
| *Drosophila melanogaster* | 30,789 | 26,509 | 86.1% | 88,650 | 3.3 |
| *Caenorhabditis elegans* | 28,590 | 21,188 | 74.1% | 59,550 | 2.8 |
| *Saccharomyces cerevisiae* | 6,002 | 5,173 | 86.2% | 8,545 | 1.7 |
| *Arabidopsis thaliana* | 48,147 | 41,434 | 86.1% | 89,118 | 2.2 |
| *Zea mays* | 57,069 | 48,877 | 85.6% | 104,750 | 2.1 |
| *Triticum aestivum* | 142,414 | 118,727 | 83.4% | 271,871 | 2.3 |
| *Oryza sativa* | 42,727 | 37,276 | 87.2% | 88,022 | 2.4 |
| *Glycine max* | 74,034 | 66,600 | 90.0% | 146,464 | 2.2 |
| *Solanum lycopersicum* | 43,943 | 38,901 | 88.5% | 88,749 | 2.3 |
| *Solanum tuberosum* | 37,881 | 34,096 | 90.0% | 78,628 | 2.3 |
| *Bos taurus* | 64,443 | 62,021 | 96.2% | 243,890 | 3.9 |
| *Sus scrofa* | 111,196 | 105,415 | 94.8% | 471,000 | 4.5 |
| *Gallus gallus* | 68,644 | 65,318 | 95.2% | 270,482 | 4.1 |
| *Salmo salar* | 85,060 | 81,640 | 96.0% | 367,908 | 4.5 |
| *Oncorhynchus mykiss* | 97,686 | 93,268 | 95.5% | 410,933 | 4.4 |
| *Ovis aries* | 76,654 | 74,562 | 97.3% | 326,449 | 4.4 |
| *Capra hircus* | 42,621 | 41,309 | 96.9% | 181,381 | 4.4 |
| *Vitis vinifera* | 40,469 | 36,910 | 91.2% | 107,622 | 2.9 |

### Domain source database distribution

| Source DB | Domain count |
|---|---|
| CDD | 15,089 |
| Pfam | 7,683 |
| COG | 1,470 |
| SMART | 665 |
| TIGR | 643 |
| PRK | 621 |
| CHL | 58 |

---

## 5. Protein Sites and Regions (New in v1.2)

Functional sites and curated regions parsed from GenPept FEATURES tables. UniProtKB-propagated features are excluded by design (324,826 features skipped).

### Site sources

| Source | Sites | Share |
|---|---|---|
| CDD (pre-computed, from domain alignments) | 1,542,359 | 82.4% |
| RefSeq curation (mostly PTMs) | 329,144 | 17.6% |
| **Total** | **1,871,503** | |

### Site types (top 10)

| Site type | Count | Note |
|---|---|---|
| other | 1,172,050 | CDD-annotated sites without a specific type |
| active | 329,688 | catalytic / active-site residues |
| phosphorylation | 201,342 | RefSeq-curated PTM |
| glycosylation | 71,354 | RefSeq-curated PTM |
| DNA binding | 36,267 | |
| acetylation | 33,438 | RefSeq-curated PTM |
| methylation | 10,333 | RefSeq-curated PTM |
| metal-binding | 9,160 | |
| hydroxylation | 2,312 | RefSeq-curated PTM |
| cleavage | 2,028 | |

### RefSeq-curated regions (1,474 total, all source=RefSeq)

Top region categories: repeats (257), alternative start codon (75), transmembrane (66), zinc finger (44), calcium binding region (21), cysteine-rich domain (17).

## 6. Gene-Type Composition

| Organism | Protein-coding | ncRNA | Pseudogene | Other | Total |
|---|---|---|---|---|---|
| *Homo sapiens* | 20,127 | 22,189 | 17,049 | 128,613 | 187,978 |
| *Mus musculus* | 22,339 | 17,602 | 10,249 | 40,770 | 90,960 |
| *Rattus norvegicus* | 23,114 | 14,880 | 8,840 | 504 | 47,338 |
| *Danio rerio* | 28,486 | 24,351 | 708 | 77 | 53,622 |
| *Drosophila melanogaster* | 13,986 | 3,575 | 311 | 0 | 17,872 |
| *Caenorhabditis elegans* | 19,983 | 25,022 | 1,921 | 0 | 46,926 |
| *Saccharomyces cerevisiae* | 6,021 | 438 | 18 | 0 | 6,477 |
| *Arabidopsis thaliana* | 27,562 | 6,828 | 3,922 | 0 | 38,312 |
| *Zea mays* | 34,265 | 10,193 | 5,191 | 25 | 49,674 |
| *Triticum aestivum* | 103,803 | 32,598 | 19,065 | 1 | 155,467 |
| *Oryza sativa* | 29,726 | 7,738 | 1,907 | 13 | 39,384 |
| *Glycine max* | 47,136 | 7,072 | 4,761 | 79 | 59,048 |
| *Solanum lycopersicum* | 28,683 | 11,327 | 1,456 | 10 | 41,476 |
| *Solanum tuberosum* | 28,411 | 2,392 | 2,027 | 2 | 32,832 |
| *Bos taurus* | 21,685 | 10,652 | 4,546 | 170 | 37,053 |
| *Sus scrofa* | 22,117 | 13,087 | 3,838 | 53 | 39,095 |
| *Gallus gallus* | 18,106 | 7,251 | 198 | 73 | 25,628 |
| *Salmo salar* | 43,038 | 39,223 | 3,903 | 51 | 86,215 |
| *Oncorhynchus mykiss* | 41,956 | 27,967 | 2,712 | 161 | 72,796 |
| *Ovis aries* | 21,309 | 9,710 | 3,822 | 210 | 35,051 |
| *Capra hircus* | 20,598 | 3,982 | 4,143 | 164 | 28,887 |
| *Vitis vinifera* | 25,257 | 2,847 | 1,450 | 37 | 29,591 |

---

## 7. Key Takeaways

1. **22 organisms, 647,708 protein-coding genes** in the v1.2 graph.
2. **Domain annotations now cover ALL organisms** — NCBI pre-computed CDD annotations (via GenPept) cover all 647,708 protein-coding genes' proteins, not just human as in v1.0.
3. **1,267,754 proteins have domain annotations** across all 22 organisms.
4. **IN_TAXON edges** directly connect each Gene to its OrganismTaxon, enabling efficient per-species queries without traversing the full taxonomy tree.
5. See the per-organism coverage matrix above for detailed breakdowns.

---

*Report generated by generate_coverage_report.py at 2026-09-16T13:39:32.265289*