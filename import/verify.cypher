
// Node counts by label
MATCH (n) RETURN labels(n)[0] AS label, count(*) AS count ORDER BY count DESC;

// Edge counts by type
MATCH ()-[r]->() RETURN type(r) AS type, count(*) AS count ORDER BY count DESC;

// Sample: TP53 traversal (human)
MATCH (g:Gene {symbol: 'TP53'})-[:TRANSCRIBED_TO]->(t:Transcript)-[:TRANSLATES_TO]->(p:Protein)
RETURN g.symbol, g.id, t.id, p.id, p.uniprotAccession LIMIT 5;

// Every node has category
MATCH (n) WHERE n.category IS NULL RETURN count(*) AS missing_category;

// Every edge has predicate
MATCH ()-[r]->() WHERE r.predicate IS NULL RETURN count(*) AS missing_predicate;

// Organism count
MATCH (o:OrganismTaxon {rank: 'species'}) RETURN count(*) AS species_count;
MATCH (o:OrganismTaxon {rank: 'no rank'}) WHERE o.name CONTAINS 'S288C' RETURN o.id, o.name;
