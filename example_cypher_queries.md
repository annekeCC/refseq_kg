# RefSeq Knowledge Graph — Example Cypher Queries (v1.2)

A curated collection of queries that demonstrate the value of the graph, organized by what they reveal. All queries run against the loaded Neo4j instance (6.5M nodes, 17.5M relationships, 22 organisms).

---

## Protein Sites and Regions (New in v1.2)

Domain annotations are now sourced from NCBI's pre-computed GenPept records. New node types capture functional sites and curated regions.

### Find all active sites on a protein
```cypher
MATCH (p:Protein)-[:HAS_SITE]->(s:ProteinSite {siteType: 'active'})
RETURN p.id, p.name, s.name, s.location, s.source
ORDER BY p.id LIMIT 20;
```

### Find all DNA-binding sites across human proteins
```cypher
MATCH (g:Gene)-[:IN_TAXON]->(:OrganismTaxon {id: 'NCBITaxon:9606'})
MATCH (g)-[:TRANSCRIBED_TO]->()-[:TRANSLATES_TO]->(p:Protein)-[:HAS_SITE]->(s:ProteinSite)
WHERE s.siteType CONTAINS 'DNA binding'
RETURN g.symbol, p.id, s.name, s.location LIMIT 20;
```

### Find proteins with transmembrane domains (RefSeq-curated regions)
```cypher
MATCH (p:Protein)-[:HAS_REGION]->(r:ProteinRegion)
WHERE r.name CONTAINS 'transmembrane'
RETURN p.id, p.name, r.name, r.id LIMIT 20;
```

### Count site types across all organisms
```cypher
MATCH (p:Protein)-[:HAS_SITE]->(s:ProteinSite)
RETURN s.siteType, s.source, count(*) AS count
ORDER BY count DESC;
```

### Domain coverage per organism (v1.2 — NCBI pre-computed)
```cypher
MATCH (g:Gene)-[:IN_TAXON]->(t:OrganismTaxon)
WHERE g.geneType = 'PROTEIN_CODING' AND t.rank = 'species'
MATCH (g)-[:TRANSCRIBED_TO]->()-[:TRANSLATES_TO]->(p:Protein)-[:HAS_DOMAIN]->(d:Domain)
RETURN t.name, count(DISTINCT p) AS proteins_with_domains, count(DISTINCT d) AS unique_domains
ORDER BY proteins_with_domains DESC;
```

---

## Key Patterns Demonstrated

- **Multi-hop traversal**: gene -> transcript -> protein -> domain/site/region in a single query
- **Cross-species reasoning**: ortholog edges connect genes across all 22 organisms
- **Annotation gap discovery**: `NOT EXISTS` subqueries find what's missing
- **Evidence-aware filtering**: evidence codes let you separate experimental from computational annotations
- **Composite annotation profiles**: combining GO + domains + sites + regions + OMIM + UniProt in one result set
- **Row-safe aggregation**: `EXISTS {}` subqueries avoid the row multiplication problem that `OPTIONAL MATCH` causes when checking coverage

## Cypher Tips for This Graph

- **Gene -> organism path (v1.1)**: `(g:Gene)-[:IN_TAXON]->(org:OrganismTaxon)` — direct edge, one hop
- **Gene -> organism path (original)**: `(g:Gene)-[:HAS_SEQUENCE_LOCATION]->(c:Chromosome)<-[:HAS_PART]-(gen:Genome)<-[:HAS_PART]-(org:OrganismTaxon)` — 4-hop chain
- **Any GO annotation**: `MATCH (g)-[]->(go:GOTerm)` — matches all 9 GO predicate types
- **Experimental evidence codes**: IDA, IPI, IMP, IGI, IEP, EXP, HDA
- **Electronic evidence code**: IEA
- **Phylogenetic/sequence evidence codes**: IBA, IBD, ISO, ISS, ISM
- **Yeast organism node**: use `NCBITaxon:559292` (S288C strain), not 4932 (species)
- **Rice organism node**: use `NCBITaxon:39947` (Japonica Group), not 4530 (species — only organellar genes)
- **Coverage checks**: use `EXISTS {}` subqueries, not `OPTIONAL MATCH`, to avoid row multiplication
- **Protein sites (v1.2)**: `ProteinSite` nodes capture CDD functional sites (active, binding) and RefSeq-curated PTM sites
- **Protein regions (v1.2)**: `ProteinRegion` nodes capture RefSeq-curated functional regions (transmembrane, extracellular, etc.)
- **Domain source (v1.2)**: Domain annotations now come from NCBI GenPept records (pre-computed by rpsbproc) instead of local RPS-BLAST
