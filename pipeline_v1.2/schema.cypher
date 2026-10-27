// RefSeq KG — Neo4j schema: constraints and indexes
// Run AFTER neo4j-admin import, BEFORE verification queries.

// Uniqueness constraints on primary IDs (one per node label)
CREATE CONSTRAINT IF NOT EXISTS FOR (n:OrganismTaxon) REQUIRE n.id IS UNIQUE;
CREATE CONSTRAINT IF NOT EXISTS FOR (n:Genome) REQUIRE n.id IS UNIQUE;
CREATE CONSTRAINT IF NOT EXISTS FOR (n:Chromosome) REQUIRE n.id IS UNIQUE;
CREATE CONSTRAINT IF NOT EXISTS FOR (n:Gene) REQUIRE n.id IS UNIQUE;
CREATE CONSTRAINT IF NOT EXISTS FOR (n:Transcript) REQUIRE n.id IS UNIQUE;
CREATE CONSTRAINT IF NOT EXISTS FOR (n:Protein) REQUIRE n.id IS UNIQUE;
CREATE CONSTRAINT IF NOT EXISTS FOR (n:GOTerm) REQUIRE n.id IS UNIQUE;
CREATE CONSTRAINT IF NOT EXISTS FOR (n:Domain) REQUIRE n.id IS UNIQUE;
CREATE CONSTRAINT IF NOT EXISTS FOR (n:ProteinSite) REQUIRE n.id IS UNIQUE;
CREATE CONSTRAINT IF NOT EXISTS FOR (n:ProteinRegion) REQUIRE n.id IS UNIQUE;

// Lookup indexes for common query patterns
CREATE INDEX IF NOT EXISTS FOR (g:Gene) ON (g.symbol);
CREATE INDEX IF NOT EXISTS FOR (g:Gene) ON (g.geneType);
CREATE INDEX IF NOT EXISTS FOR (p:Protein) ON (p.uniprotAccession);
CREATE INDEX IF NOT EXISTS FOR (p:Protein) ON (p.md5);
CREATE INDEX IF NOT EXISTS FOR (t:Transcript) ON (t.transcriptType);
CREATE INDEX IF NOT EXISTS FOR (d:Domain) ON (d.sourceDb);
CREATE INDEX IF NOT EXISTS FOR (s:ProteinSite) ON (s.siteType);
CREATE INDEX IF NOT EXISTS FOR (s:ProteinSite) ON (s.source);
CREATE INDEX IF NOT EXISTS FOR (o:OrganismTaxon) ON (o.rank);
CREATE INDEX IF NOT EXISTS FOR (g:GOTerm) ON (g.aspect);

// Full-text index for text search over gene symbols/descriptions
CREATE FULLTEXT INDEX geneTextIndex IF NOT EXISTS
FOR (g:Gene) ON EACH [g.symbol, g.description, g.summary];
