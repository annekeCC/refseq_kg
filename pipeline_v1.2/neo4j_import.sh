#!/bin/bash
# RefSeq KG v1.2 — Neo4j import, schema application, verification, dump.
# v1.2 CSV set: adds nodes_ProteinSite / nodes_ProteinRegion and
# edges_HAS_DOMAIN / edges_HAS_SITE / edges_HAS_REGION (GenPept-derived).
# The v1.1 edges_HAS_PART_domain.csv (local RPS-BLAST output) is retired.
#
# Java note: v1.2 was built with conda Java 23 (the JDK 21 download failed).
# Neo4j 5.26 works despite the "unsupported Java runtime" warning.
export JAVA_HOME=${JAVA_HOME:-/opt/conda}
export PATH=$JAVA_HOME/bin:$PATH
export NEO4J_HOME=${NEO4J_HOME:-/workspace/neo4j-community-5.26.0}
IMPORT=${IMPORT:-/workspace/import}
RESULTS=${RESULTS:-/mnt/results/refseq_kg}

echo "=== Running full import (v1.2: 10 node files, 20 relationship files) ==="
$NEO4J_HOME/bin/neo4j-admin database import full neo4j \
  --overwrite-destination=true \
  --skip-bad-relationships=true \
  --skip-duplicate-nodes=true \
  --report-file=$IMPORT/import_report_final.txt \
  --nodes=$IMPORT/nodes_Chromosome.csv \
  --nodes=$IMPORT/nodes_Domain.csv \
  --nodes=$IMPORT/nodes_GOTerm.csv \
  --nodes=$IMPORT/nodes_Gene.csv \
  --nodes=$IMPORT/nodes_Genome.csv \
  --nodes=$IMPORT/nodes_OrganismTaxon.csv \
  --nodes=$IMPORT/nodes_Protein.csv \
  --nodes=$IMPORT/nodes_ProteinRegion.csv \
  --nodes=$IMPORT/nodes_ProteinSite.csv \
  --nodes=$IMPORT/nodes_Transcript.csv \
  --relationships=$IMPORT/edges_GO_ACTIVELY_INVOLVED_IN.csv \
  --relationships=$IMPORT/edges_GO_ACTS_UPSTREAM_OF.csv \
  --relationships=$IMPORT/edges_GO_ACTS_UPSTREAM_OF_OR_WITHIN.csv \
  --relationships=$IMPORT/edges_GO_COLOCALIZES_WITH.csv \
  --relationships=$IMPORT/edges_GO_CONTRIBUTES_TO.csv \
  --relationships=$IMPORT/edges_GO_ENABLES.csv \
  --relationships=$IMPORT/edges_GO_GO_PART_OF.csv \
  --relationships=$IMPORT/edges_GO_IS_ACTIVE_IN.csv \
  --relationships=$IMPORT/edges_GO_LOCATED_IN.csv \
  --relationships=$IMPORT/edges_HAS_DOMAIN.csv \
  --relationships=$IMPORT/edges_HAS_GENE_PRODUCT.csv \
  --relationships=$IMPORT/edges_HAS_PART.csv \
  --relationships=$IMPORT/edges_HAS_REGION.csv \
  --relationships=$IMPORT/edges_HAS_SEQUENCE_LOCATION.csv \
  --relationships=$IMPORT/edges_HAS_SITE.csv \
  --relationships=$IMPORT/edges_IN_TAXON.csv \
  --relationships=$IMPORT/edges_ORTHOLOGOUS_TO.csv \
  --relationships=$IMPORT/edges_PART_OF.csv \
  --relationships=$IMPORT/edges_TRANSCRIBED_TO.csv \
  --relationships=$IMPORT/edges_TRANSLATES_TO.csv 2>&1

echo ""
echo "=== Starting Neo4j ==="
$NEO4J_HOME/bin/neo4j start 2>&1
sleep 30
# Databases can take a while to come online after a fresh import; retry once.
$NEO4J_HOME/bin/neo4j status >/dev/null 2>&1 || $NEO4J_HOME/bin/neo4j start 2>&1
sleep 20

echo ""
echo "=== Applying schema (v1.2: includes ProteinSite/ProteinRegion constraints) ==="
$NEO4J_HOME/bin/cypher-shell --file /workspace/schema.cypher 2>&1 || true
sleep 5

echo ""
echo "=== Node counts ==="
echo "MATCH (n) RETURN labels(n)[0] AS label, count(*) AS count ORDER BY count DESC;" | $NEO4J_HOME/bin/cypher-shell 2>&1

echo ""
echo "=== Edge counts ==="
echo "MATCH ()-[r]->() RETURN type(r) AS type, count(*) AS count ORDER BY count DESC;" | $NEO4J_HOME/bin/cypher-shell 2>&1

echo ""
echo "=== TP53 traversal (domains + sites, v1.2) ==="
echo "MATCH (g:Gene {symbol: 'TP53'})-[:TRANSCRIBED_TO]->(t:Transcript)-[:TRANSLATES_TO]->(p:Protein) OPTIONAL MATCH (p)-[:HAS_DOMAIN]->(d:Domain) OPTIONAL MATCH (p)-[:HAS_SITE]->(s:ProteinSite) RETURN g.symbol, p.id, collect(DISTINCT d.id)[..5] AS domains, collect(DISTINCT s.siteType)[..5] AS siteTypes LIMIT 5;" | $NEO4J_HOME/bin/cypher-shell 2>&1

echo ""
echo "=== Missing category ==="
echo "MATCH (n) WHERE n.category IS NULL RETURN count(*) AS missing_category;" | $NEO4J_HOME/bin/cypher-shell 2>&1

echo ""
echo "=== Missing predicate ==="
echo "MATCH ()-[r]->() WHERE r.predicate IS NULL RETURN count(*) AS missing_predicate;" | $NEO4J_HOME/bin/cypher-shell 2>&1

echo ""
echo "=== Species count ==="
echo "MATCH (o:OrganismTaxon {rank: 'species'}) RETURN count(*) AS species_count;" | $NEO4J_HOME/bin/cypher-shell 2>&1

echo ""
echo "=== Stopping Neo4j (stop can take >2 min; verify with 'ps aux | grep neo4j' if it reports failure) ==="
$NEO4J_HOME/bin/neo4j stop 2>&1 || true
sleep 15

echo ""
echo "=== Creating dump ==="
$NEO4J_HOME/bin/neo4j-admin database dump neo4j --to-path=$RESULTS 2>&1
echo "Dump file:"
ls -la $RESULTS/neo4j.dump 2>/dev/null

echo ""
echo "=== DONE ==="
