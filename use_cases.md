# RefSeq Knowledge Graph (v1.2) — Use Cases

A BioLink-conformant Neo4j property graph built from NCBI RefSeq data for 22 model organisms. 6.5M nodes, 17.5M relationships, 94M properties.

---

## 1. KG Embeddings & Link Prediction

Train TransE, RotatE, ComplEx, or GNN models on the graph's typed triples.

**Why this graph works:**
- 10 node types with clear semantic distinctions (Gene, Protein, Domain, ProteinSite, ProteinRegion, GOTerm, etc.)
- 20 edge types with BioLink predicates as relation labels
- Rich node properties for feature engineering (gene symbols, domain names, site types, evidence codes)
- Ortholog edges provide cross-species positive examples

**Export format:** Cypher query → CSV (head, relation, tail) + node feature table

---

## 2. Protein Function Prediction

Predict GO terms, domains, or sites for unannotated proteins.

**Query pattern:**
```cypher
// Find proteins lacking domain annotations
MATCH (p:Protein)
WHERE NOT EXISTS { MATCH (p)-[:HAS_DOMAIN]->() }
RETURN p.id, p.name, p.length LIMIT 100;
```

**Training signal:** Proteins with known domains/sites can serve as labels for ML-based function prediction.

---

## 3. Cross-Species Comparative Genomics

Leverage ortholog edges and taxonomy to compare annotation coverage across organisms.

**Query pattern:**
```cypher
// Compare domain coverage between human and zebrafish orthologs
MATCH (h:Gene)-[:ORTHOLOGOUS_TO]->(z:Gene)
MATCH (h)-[:IN_TAXON]->(:OrganismTaxon {id: 'NCBITaxon:9606'})
MATCH (z)-[:IN_TAXON]->(:OrganismTaxon {id: 'NCBITaxon:7955'})
MATCH (h)-[:TRANSCRIBED_TO]->()-[:TRANSLATES_TO]->(hp:Protein)
MATCH (z)-[:TRANSCRIBED_TO]->()-[:TRANSLATES_TO]->(zp:Protein)
RETURN h.symbol,
       EXISTS { MATCH (hp)-[:HAS_DOMAIN]->() } AS human_has_domain,
       EXISTS { MATCH (zp)-[:HAS_DOMAIN]->() } AS zebrafish_has_domain
LIMIT 50;
```

---

## 4. Domain Architecture Analysis

Study the arrangement of protein domains, sites, and regions across protein families.

**Query pattern:**
```cypher
// Find proteins with both kinase domains and active sites
MATCH (p:Protein)-[:HAS_DOMAIN]->(d:Domain)
WHERE d.name CONTAINS 'kinase'
MATCH (p)-[:HAS_SITE]->(s:ProteinSite {siteType: 'active'})
RETURN p.id, p.name, d.name, s.name, s.location LIMIT 20;
```

---

## 5. Functional Site Mining (New in v1.2)

Discover catalytic active sites, binding sites, and curated functional regions across all 22 organisms.

**Query pattern:**
```cypher
// Find all zinc-binding sites across all proteins
MATCH (p:Protein)-[:HAS_SITE]->(s:ProteinSite)
WHERE s.name CONTAINS 'zinc binding'
RETURN p.id, p.name, s.location, s.source LIMIT 50;
```

```cypher
// Find proteins with transmembrane regions (RefSeq-curated)
MATCH (p:Protein)-[:HAS_REGION]->(r:ProteinRegion)
WHERE r.name CONTAINS 'transmembrane'
RETURN count(DISTINCT p) AS proteins_with_tm_regions;
```

---

## 6. Annotation Gap Discovery

Identify genes or proteins lacking specific annotation types.

**Query pattern:**
```cypher
// Protein-coding genes with no GO, no domain, and no site annotations
MATCH (g:Gene)-[:IN_TAXON]->(t:OrganismTaxon {rank: 'species'})
WHERE g.geneType = 'PROTEIN_CODING'
  AND NOT EXISTS { MATCH (g)-[:ENABLES|ACTIVELY_INVOLVED_IN|LOCATED_IN|IS_ACTIVE_IN|PART_OF|CONTRIBUTES_TO|COLOCALIZES_WITH|ACTS_UPSTREAM_OF|ACTS_UPSTREAM_OF_OR_WITHIN]->(:GOTerm) }
  AND NOT EXISTS { MATCH (g)-[:TRANSCRIBED_TO]->()-[:TRANSLATES_TO]->(:Protein)-[:HAS_DOMAIN]->() }
  AND NOT EXISTS { MATCH (g)-[:TRANSCRIBED_TO]->()-[:TRANSLATES_TO]->(:Protein)-[:HAS_SITE]->() }
RETURN t.name, count(g) AS unannotated_genes
ORDER BY unannotated_genes DESC;
```

---

## 7. LLM Context / RAG Grounding

Serialize graph neighborhoods as structured text for retrieval-augmented generation.

**Query pattern:**
```cypher
// Get full annotation profile for a gene
MATCH (g:Gene {symbol: 'TP53'})-[:IN_TAXON]->(t:OrganismTaxon)
OPTIONAL MATCH (g)-[:TRANSCRIBED_TO]->(tr:Transcript)-[:TRANSLATES_TO]->(p:Protein)
OPTIONAL MATCH (p)-[:HAS_DOMAIN]->(d:Domain)
OPTIONAL MATCH (p)-[:HAS_SITE]->(s:ProteinSite)
OPTIONAL MATCH (p)-[:HAS_REGION]->(r:ProteinRegion)
OPTIONAL MATCH (g)-[:ENABLES|ACTIVELY_INVOLVED_IN|LOCATED_IN]->(go:GOTerm)
RETURN g.symbol, g.description, g.summary,
       collect(DISTINCT d.name) AS domains,
       collect(DISTINCT s.name) AS sites,
       collect(DISTINCT r.name) AS regions,
       collect(DISTINCT go.name) AS go_terms;
```

---

## 8. Ortholog-Based Drug Target Prioritization

Use cross-species orthologs to prioritize conserved drug targets.

**Query pattern:**
```cypher
// Find human genes with orthologs in cattle that have known drug domains
MATCH (h:Gene)-[:IN_TAXON]->(:OrganismTaxon {id: 'NCBITaxon:9606'})
MATCH (h)-[:ORTHOLOGOUS_TO]->(o:Gene)-[:IN_TAXON]->(:OrganismTaxon {id: 'NCBITaxon:9913'})
MATCH (h)-[:TRANSCRIBED_TO]->()-[:TRANSLATES_TO]->(p:Protein)-[:HAS_DOMAIN]->(d:Domain)
WHERE d.name CONTAINS 'kinase' OR d.name CONTAINS 'receptor'
RETURN h.symbol, h.description, d.name
ORDER BY h.symbol;
```

---

## Key Design Decisions

- **22 model organisms** spanning mammals, fish, insects, worms, yeast, and plants
- **BioLink-conformant** predicates and categories for interoperability
- **NCBI-sourced annotations only** — domains from NCBI GenPept pre-computed CDD annotations (v1.2), not local RPS-BLAST
- **UniProtKB-propagated features excluded** — only NCBI-curated (CDD + RefSeq) features included
- **Direct IN_TAXON edges** (v1.1) for efficient organism filtering without taxonomy tree traversal
- **ProteinSite and ProteinRegion** (v1.2) capture functional sites and curated regions from GenPept records
