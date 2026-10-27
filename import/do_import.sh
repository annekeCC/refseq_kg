#!/bin/bash
export JAVA_HOME=/workspace/jdk-21.0.5+11
export PATH=/workspace/bin:$JAVA_HOME/bin:$PATH
export NEO4J_HOME=/workspace/neo4j-community-5.26.0
IMPORT=/workspace/import
RESULTS=/mnt/results/refseq_kg

echo "=== Running full import ==="
$NEO4J_HOME/bin/neo4j-admin database import full neo4j \
  --overwrite-destination=true \
  --skip-bad-relationships=true \
  --skip-duplicate-nodes=true \
  --bad-tolerance=1000 \
  --report-file=$IMPORT/import_report_final.txt \
  --nodes=$IMPORT/nodes_Chromosome.csv \
  --nodes=$IMPORT/nodes_Domain.csv \
  --nodes=$IMPORT/nodes_GOTerm.csv \
  --nodes=$IMPORT/nodes_Gene.csv \
  --nodes=$IMPORT/nodes_Genome.csv \
  --nodes=$IMPORT/nodes_OrganismTaxon.csv \
  --nodes=$IMPORT/nodes_Protein.csv \
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
  --relationships=$IMPORT/edges_HAS_GENE_PRODUCT.csv \
  --relationships=$IMPORT/edges_HAS_PART.csv \
  --relationships=$IMPORT/edges_HAS_PART_domain.csv \
  --relationships=$IMPORT/edges_HAS_SEQUENCE_LOCATION.csv \
  --relationships=$IMPORT/edges_IN_TAXON.csv \
  --relationships=$IMPORT/edges_ORTHOLOGOUS_TO.csv \
  --relationships=$IMPORT/edges_PART_OF.csv \
  --relationships=$IMPORT/edges_TRANSCRIBED_TO.csv \
  --relationships=$IMPORT/edges_TRANSLATES_TO.csv 2>&1

echo ""
echo "=== Starting Neo4j ==="
$NEO4J_HOME/bin/neo4j start 2>&1
sleep 20

echo ""
echo "=== Applying schema ==="
$NEO4J_HOME/bin/cypher-shell --file /workspace/schema.cypher 2>&1 || true
sleep 5

echo ""
echo "=== Node counts ==="
echo "MATCH (n) RETURN labels(n)[0] AS label, count(*) AS count ORDER BY count DESC;" | $NEO4J_HOME/bin/cypher-shell 2>&1

echo ""
echo "=== Edge counts ==="
echo "MATCH ()-[r]->() RETURN type(r) AS type, count(*) AS count ORDER BY count DESC;" | $NEO4J_HOME/bin/cypher-shell 2>&1

echo ""
echo "=== TP53 traversal ==="
echo "MATCH (g:Gene {symbol: 'TP53'})-[:TRANSCRIBED_TO]->(t:Transcript)-[:TRANSLATES_TO]->(p:Protein) RETURN g.symbol, g.id, t.id, p.id, p.uniprotAccession LIMIT 5;" | $NEO4J_HOME/bin/cypher-shell 2>&1

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
echo "=== Stopping Neo4j ==="
$NEO4J_HOME/bin/neo4j stop 2>&1 || true
sleep 10

echo ""
echo "=== Creating dump ==="
$NEO4J_HOME/bin/neo4j-admin database dump neo4j --to-path=$RESULTS 2>&1
echo "Dump file:"
ls -la $RESULTS/neo4j.dump 2>/dev/null

echo ""
echo "=== DONE ==="
