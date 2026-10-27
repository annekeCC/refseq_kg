#!/usr/bin/env python3
"""
Generate the v1.1 Annotation Coverage Report by querying the loaded Neo4j graph.
Run AFTER neo4j-admin import and schema application.

Outputs: /mnt/results/refseq_kg/annotation_coverage_report.md
"""
import sys, os, textwrap
from datetime import datetime
from neo4j import GraphDatabase

NEO4J_URI = "bolt://localhost:7687"
NEO4J_USER = "neo4j"
NEO4J_PASS = "neo4j"  # default, change if needed

# 22 organisms: (scientific_name, taxid, common_name)
ORGANISMS = [
    ("Homo sapiens", 9606, "Human"),
    ("Mus musculus", 10090, "Mouse"),
    ("Rattus norvegicus", 10116, "Rat"),
    ("Danio rerio", 7955, "Zebrafish"),
    ("Drosophila melanogaster", 7227, "Fly"),
    ("Caenorhabditis elegans", 6239, "Worm"),
    ("Saccharomyces cerevisiae", 4932, "Yeast"),
    ("Arabidopsis thaliana", 3702, "Arabidopsis"),
    ("Zea mays", 4577, "Maize"),
    ("Triticum aestivum", 4565, "Bread wheat"),
    ("Oryza sativa", 4530, "Rice"),
    ("Glycine max", 3847, "Soybean"),
    ("Solanum lycopersicum", 4081, "Tomato"),
    ("Solanum tuberosum", 4113, "Potato"),
    ("Bos taurus", 9913, "Cattle"),
    ("Sus scrofa", 9823, "Pig"),
    ("Gallus gallus", 9031, "Chicken"),
    ("Salmo salar", 8030, "Atlantic salmon"),
    ("Oncorhynchus mykiss", 8022, "Rainbow trout"),
    ("Ovis aries", 9940, "Sheep"),
    ("Capra hircus", 9925, "Goat"),
    ("Vitis vinifera", 29760, "Grape"),
]

# Some organisms use a different gene_taxid than the species taxid
# For IN_TAXON queries, we query by the species-level OrganismTaxon node
# which is connected to genes via IN_TAXON edges.
# The build uses gene_taxid for the IN_TAXON edge, so we need to match
# by the taxid stored in the OrganismTaxon node.
# For rice, genes are under 39947 (Japonica Group), not 4530.
# We'll query by the OrganismTaxon node that genes point to.
# Actually, the IN_TAXON edge connects Gene to OrganismTaxon by the gene_taxid.
# So for rice, genes point to taxon 39947, not 4530.
# We need to handle this: query all species-level taxa that have genes.

def fmt_pct(num, denom):
    if denom == 0:
        return "—"
    return f"{100*num/denom:.1f}"

def fmt_num(n):
    return f"{n:,}"

def run_query(session, query, params=None):
    result = session.run(query, params or {})
    return [r.data() for r in result]


def main():
    driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASS))
    
    report = []
    report.append("# RefSeq Knowledge Graph — Annotation Coverage Report")
    report.append("")
    report.append(f"**Generated**: {datetime.now().strftime('%Y-%m-%d')} (v1.1)")
    report.append("**Graph version**: 1.1")
    report.append("**Source**: NCBI RefSeq, 22 model organisms")
    report.append("**Query engine**: Neo4j 5.26.0 Community Edition")
    report.append("**Scope**: All NCBI-provided annotation types, including RPS-BLAST domain annotation on ALL proteins")
    report.append("")
    report.append("---")
    report.append("")

    with driver.session() as session:
        # === Overall graph stats ===
        report.append("## 0. Graph Overview")
        report.append("")
        
        node_counts = run_query(session, """
            MATCH (n) RETURN labels(n)[0] AS label, count(*) AS count ORDER BY count DESC
        """)
        report.append("### Node counts")
        report.append("")
        report.append("| Label | Count |")
        report.append("|---|---|")
        total_nodes = 0
        for r in node_counts:
            report.append(f"| {r['label']} | {fmt_num(r['count'])} |")
            total_nodes += r['count']
        report.append(f"| **Total** | **{fmt_num(total_nodes)}** |")
        report.append("")
        
        edge_counts = run_query(session, """
            MATCH ()-[r]->() RETURN type(r) AS type, count(*) AS count ORDER BY count DESC
        """)
        report.append("### Edge counts")
        report.append("")
        report.append("| Type | Count |")
        report.append("|---|---|")
        total_edges = 0
        for r in edge_counts:
            report.append(f"| {r['type']} | {fmt_num(r['count'])} |")
            total_edges += r['count']
        report.append(f"| **Total** | **{fmt_num(total_edges)}** |")
        report.append("")
        report.append("---")
        report.append("")

        # === Section 1: Overview ===
        report.append("## 1. Overview: What Counts as Annotation")
        report.append("")
        report.append(textwrap.dedent("""\
            NCBI provides many layers of annotation beyond Gene Ontology terms. This report assesses coverage across **10 annotation types** present in the knowledge graph, all sourced from NCBI data:

            | # | Annotation type | Source | Graph location |
            |---|---|---|---|
            | 1 | Gene symbol | NCBI Gene nomenclature | Gene.symbol |
            | 2 | Gene description | NCBI Gene descriptive text | Gene.description |
            | 3 | Gene summary | NCBI curated functional summary | Gene.summary |
            | 4 | Gene synonyms | NCBI alternative names | Gene.synonyms |
            | 5 | GO terms | NCBI gene2go (9 predicates) | Gene → GOTerm edges |
            | 6 | Protein domains | CDD via RPS-BLAST | Protein → Domain edges |
            | 7 | Orthologs | NCBI Ortholog | Gene → Gene edges |
            | 8 | OMIM IDs | NCBI OMIM cross-reference | Gene.omimIds |
            | 9 | Swiss-Prot accessions | NCBI UniProt cross-reference | Gene.swissprotAccessions |
            | 10 | Protein name | NCBI RefSeq protein annotation | Protein.name |

            All metrics are computed for **protein-coding genes only** (the meaningful comparison set). Non-coding genes (ncRNA, tRNA, pseudogene, etc.) typically do not receive functional annotations by design.

            **Core annotation depth score**: For each protein-coding gene, we count how many of 6 core types are present: symbol, description, summary, GO terms, protein domains, orthologs. This gives a 0–6 depth score per gene.
        """))
        report.append("---")
        report.append("")

        # === Section 2: Per-Organism Coverage Matrix ===
        report.append("## 2. Per-Organism Annotation Coverage Matrix")
        report.append("")
        report.append("Percentage of protein-coding genes with each annotation type present:")
        report.append("")
        report.append("| Organism | PC genes | Symbol | Desc | Summary | Synonyms | GO | Domain | Ortholog | OMIM | SwissProt | Prot name |")
        report.append("|---|---|---|---|---|---|---|---|---|---|---|---|")

        # Get per-organism stats
        # We query by the OrganismTaxon that genes point to via IN_TAXON
        # For most organisms, this is the species taxid.
        # For rice, it's 39947 (Japonica Group).
        # We'll get all taxa that have IN_TAXON edges from genes, then map to our organism list.
        
        org_data = {}
        for sci_name, taxid, common in ORGANISMS:
            # Try the species taxid first, then try gene_taxid variants
            # For rice, genes point to 39947
            query_taxid = taxid
            if taxid == 4530:
                query_taxid = 39947  # Japonica Group for rice nuclear genes
            if taxid == 4932:
                query_taxid = 559292  # S. cerevisiae S288C taxid used by NCBI Gene
            taxon_id = f"NCBITaxon:{query_taxid}"
            
            # Get protein-coding gene count
            pc_count = run_query(session, """
                MATCH (g:Gene)-[:IN_TAXON]->(t:OrganismTaxon {id: $taxid})
                WHERE g.geneType = 'PROTEIN_CODING'
                RETURN count(*) AS count
            """, {"taxid": taxon_id})
            pc_genes = pc_count[0]['count'] if pc_count else 0

            if pc_genes == 0:
                # Try the original taxid
                pc_count = run_query(session, """
                    MATCH (g:Gene)-[:IN_TAXON]->(t:OrganismTaxon {id: $taxid})
                    WHERE g.geneType = 'PROTEIN_CODING'
                    RETURN count(*) AS count
                """, {"taxid": taxon_id})
                pc_genes = pc_count[0]['count'] if pc_count else 0
                query_taxid = taxid

            if pc_genes == 0:
                org_data[taxid] = None
                continue

            # Symbol coverage
            sym = run_query(session, """
                MATCH (g:Gene)-[:IN_TAXON]->(t:OrganismTaxon {id: $taxid})
                WHERE g.geneType = 'PROTEIN_CODING' AND g.symbol IS NOT NULL AND g.symbol <> ''
                RETURN count(*) AS count
            """, {"taxid": taxon_id})[0]['count']

            # Description coverage
            desc = run_query(session, """
                MATCH (g:Gene)-[:IN_TAXON]->(t:OrganismTaxon {id: $taxid})
                WHERE g.geneType = 'PROTEIN_CODING' AND g.description IS NOT NULL AND g.description <> ''
                RETURN count(*) AS count
            """, {"taxid": taxon_id})[0]['count']

            # Summary coverage
            summ = run_query(session, """
                MATCH (g:Gene)-[:IN_TAXON]->(t:OrganismTaxon {id: $taxid})
                WHERE g.geneType = 'PROTEIN_CODING' AND g.summary IS NOT NULL AND g.summary <> ''
                RETURN count(*) AS count
            """, {"taxid": taxon_id})[0]['count']

            # Synonyms coverage
            syn = run_query(session, """
                MATCH (g:Gene)-[:IN_TAXON]->(t:OrganismTaxon {id: $taxid})
                WHERE g.geneType = 'PROTEIN_CODING' AND g.synonyms IS NOT NULL AND g.synonyms <> ''
                RETURN count(*) AS count
            """, {"taxid": taxon_id})[0]['count']

            # GO coverage (gene has at least one GO edge)
            go = run_query(session, """
                MATCH (g:Gene)-[:IN_TAXON]->(t:OrganismTaxon {id: $taxid})
                WHERE g.geneType = 'PROTEIN_CODING'
                AND EXISTS { MATCH (g)-[:ENABLES|CONTRIBUTES_TO|ACTIVELY_INVOLVED_IN|PART_OF|LOCATED_IN|IS_ACTIVE_IN|COLOCALIZES_WITH|ACTS_UPSTREAM_OF|ACTS_UPSTREAM_OF_OR_WITHIN]->(:GOTerm) }
                RETURN count(*) AS count
            """, {"taxid": taxon_id})[0]['count']

            # Domain coverage (gene's protein has at least one domain)
            dom = run_query(session, """
                MATCH (g:Gene)-[:IN_TAXON]->(t:OrganismTaxon {id: $taxid})
                WHERE g.geneType = 'PROTEIN_CODING'
                AND EXISTS { MATCH (g)-[:TRANSCRIBED_TO]->(:Transcript)-[:TRANSLATES_TO]->(p:Protein)-[:HAS_DOMAIN]->(:Domain) }
                RETURN count(*) AS count
            """, {"taxid": taxon_id})[0]['count']

            # Ortholog coverage
            orth = run_query(session, """
                MATCH (g:Gene)-[:IN_TAXON]->(t:OrganismTaxon {id: $taxid})
                WHERE g.geneType = 'PROTEIN_CODING'
                AND EXISTS { MATCH (g)-[:ORTHOLOGOUS_TO]->(:Gene) }
                RETURN count(*) AS count
            """, {"taxid": taxon_id})[0]['count']

            # OMIM coverage
            omim = run_query(session, """
                MATCH (g:Gene)-[:IN_TAXON]->(t:OrganismTaxon {id: $taxid})
                WHERE g.geneType = 'PROTEIN_CODING' AND g.omimIds IS NOT NULL AND g.omimIds <> ''
                RETURN count(*) AS count
            """, {"taxid": taxon_id})[0]['count']

            # SwissProt coverage
            swiss = run_query(session, """
                MATCH (g:Gene)-[:IN_TAXON]->(t:OrganismTaxon {id: $taxid})
                WHERE g.geneType = 'PROTEIN_CODING' AND g.swissprotAccessions IS NOT NULL AND g.swissprotAccessions <> ''
                RETURN count(*) AS count
            """, {"taxid": taxon_id})[0]['count']

            # Protein name coverage
            pname = run_query(session, """
                MATCH (g:Gene)-[:IN_TAXON]->(t:OrganismTaxon {id: $taxid})
                WHERE g.geneType = 'PROTEIN_CODING'
                AND EXISTS { MATCH (g)-[:TRANSCRIBED_TO]->(:Transcript)-[:TRANSLATES_TO]->(p:Protein) WHERE p.name IS NOT NULL AND p.name <> '' }
                RETURN count(*) AS count
            """, {"taxid": taxon_id})[0]['count']

            org_data[taxid] = {
                "sci_name": sci_name, "common": common, "pc_genes": pc_genes,
                "query_taxid": query_taxid,
                "sym": sym, "desc": desc, "summ": summ, "syn": syn,
                "go": go, "dom": dom, "orth": orth, "omim": omim,
                "swiss": swiss, "pname": pname,
            }

            it = org_data[taxid]
            report.append(
                f"| *{sci_name}* | {fmt_num(pc_genes)} | "
                f"{fmt_pct(sym, pc_genes)} | {fmt_pct(desc, pc_genes)} | "
                f"{fmt_pct(summ, pc_genes)} | {fmt_pct(syn, pc_genes)} | "
                f"{fmt_pct(go, pc_genes)} | {fmt_pct(dom, pc_genes)} | "
                f"{fmt_pct(orth, pc_genes)} | "
                f"{'—' if omim == 0 else fmt_pct(omim, pc_genes)} | "
                f"{'—' if swiss == 0 else fmt_pct(swiss, pc_genes)} | "
                f"{fmt_pct(pname, pc_genes)} |"
            )
            print(f"  {common}: {pc_genes} PC genes, GO={fmt_pct(go, pc_genes)}%, Domain={fmt_pct(dom, pc_genes)}%", flush=True)

        report.append("")
        report.append("OMIM is human-only by design (— = not applicable). All values are percentages unless noted.")
        report.append("")
        report.append("---")
        report.append("")

        # === Section 3: Annotation Depth Distribution ===
        report.append("## 3. Annotation Depth Distribution")
        report.append("")
        report.append("For each protein-coding gene, the depth score counts how many of 6 core annotation types are present: symbol, description, summary, GO, domains, orthologs. Since symbol and description are universal, the practical range is 2–6.")
        report.append("")
        report.append("| Organism | Depth 2 | Depth 3 | Depth 4 | Depth 5 | Depth 6 | Max depth |")
        report.append("|---|---|---|---|---|---|---|")

        for sci_name, taxid, common in ORGANISMS:
            it = org_data.get(taxid)
            if not it:
                report.append(f"| *{sci_name}* | — | — | — | — | — | — |")
                continue
            
            qt = it["query_taxid"]
            # Compute depth per gene
            depth_data = run_query(session, """
                MATCH (g:Gene)-[:IN_TAXON]->(t:OrganismTaxon {id: $taxid})
                WHERE g.geneType = 'PROTEIN_CODING'
                OPTIONAL MATCH (g)-[:TRANSCRIBED_TO]->(:Transcript)-[:TRANSLATES_TO]->(p:Protein)-[:HAS_DOMAIN]->(:Domain)
                WITH g, collect(DISTINCT p) AS proteins
                WITH g, proteins,
                     CASE WHEN g.symbol IS NOT NULL AND g.symbol <> '' THEN 1 ELSE 0 END AS has_sym,
                     CASE WHEN g.description IS NOT NULL AND g.description <> '' THEN 1 ELSE 0 END AS has_desc,
                     CASE WHEN g.summary IS NOT NULL AND g.summary <> '' THEN 1 ELSE 0 END AS has_summ,
                     CASE WHEN EXISTS { MATCH (g)-[:ENABLES|CONTRIBUTES_TO|ACTIVELY_INVOLVED_IN|PART_OF|LOCATED_IN|IS_ACTIVE_IN|COLOCALIZES_WITH|ACTS_UPSTREAM_OF|ACTS_UPSTREAM_OF_OR_WITHIN]->(:GOTerm) } THEN 1 ELSE 0 END AS has_go,
                     CASE WHEN size(proteins) > 0 THEN 1 ELSE 0 END AS has_dom,
                     CASE WHEN EXISTS { MATCH (g)-[:ORTHOLOGOUS_TO]->(:Gene) } THEN 1 ELSE 0 END AS has_orth
                WITH g, has_sym + has_desc + has_summ + has_go + has_dom + has_orth AS depth
                RETURN depth, count(*) AS count ORDER BY depth
            """, {"taxid": f"NCBITaxon:{qt}"})
            
            depth_map = {r['depth']: r['count'] for r in depth_data}
            pc = it["pc_genes"]
            max_depth = max(depth_map.keys()) if depth_map else 0
            
            def depth_pct(d):
                c = depth_map.get(d, 0)
                if c == 0:
                    return "—"
                return f"{fmt_num(c)} ({fmt_pct(c, pc)}%)"
            
            report.append(
                f"| *{sci_name}* | {depth_pct(2)} | {depth_pct(3)} | {depth_pct(4)} | {depth_pct(5)} | {depth_pct(6)} | {max_depth} |"
            )
            print(f"  {common} depth: {depth_map}", flush=True)

        report.append("")
        report.append("---")
        report.append("")

        # === Section 4: Domain Annotation Detail ===
        report.append("## 4. Domain Annotation Detail (RPS-BLAST vs CDD)")
        report.append("")
        report.append("Domain annotations from RPS-BLAST against the NCBI Conserved Domain Database (CDD), run on ALL proteins from all 22 organisms.")
        report.append("")
        report.append("### Per-organism domain coverage")
        report.append("")
        report.append("| Organism | Proteins | Proteins with domains | Coverage | Total domain hits | Avg domains/protein |")
        report.append("|---|---|---|---|---|---|")

        for sci_name, taxid, common in ORGANISMS:
            it = org_data.get(taxid)
            if not it:
                report.append(f"| *{sci_name}* | — | — | — | — | — |")
                continue
            
            qt = it["query_taxid"]
            # Total proteins
            prot_count = run_query(session, """
                MATCH (g:Gene)-[:IN_TAXON]->(t:OrganismTaxon {id: $taxid})
                WHERE g.geneType = 'PROTEIN_CODING'
                MATCH (g)-[:TRANSCRIBED_TO]->(:Transcript)-[:TRANSLATES_TO]->(p:Protein)
                RETURN count(DISTINCT p) AS count
            """, {"taxid": f"NCBITaxon:{qt}"})[0]['count']

            # Proteins with domains
            prot_with_dom = run_query(session, """
                MATCH (g:Gene)-[:IN_TAXON]->(t:OrganismTaxon {id: $taxid})
                WHERE g.geneType = 'PROTEIN_CODING'
                MATCH (g)-[:TRANSCRIBED_TO]->(:Transcript)-[:TRANSLATES_TO]->(p:Protein)-[:HAS_DOMAIN]->(d:Domain)
                RETURN count(DISTINCT p) AS prot_count, count(DISTINCT d) AS dom_count, count(*) AS hit_count
            """, {"taxid": f"NCBITaxon:{qt}"})
            
            if prot_with_dom and prot_with_dom[0]['prot_count'] > 0:
                r = prot_with_dom[0]
                avg = r['hit_count'] / r['prot_count'] if r['prot_count'] > 0 else 0
                report.append(
                    f"| *{sci_name}* | {fmt_num(prot_count)} | {fmt_num(r['prot_count'])} | "
                    f"{fmt_pct(r['prot_count'], prot_count)}% | {fmt_num(r['hit_count'])} | {avg:.1f} |"
                )
            else:
                report.append(f"| *{sci_name}* | {fmt_num(prot_count)} | 0 | 0% | 0 | — |")

        report.append("")
        report.append("### Domain source database distribution")
        report.append("")
        report.append("| Source DB | Domain count |")
        report.append("|---|---|")
        dom_sources = run_query(session, """
            MATCH (d:Domain) RETURN d.sourceDb AS db, count(*) AS count ORDER BY count DESC
        """)
        for r in dom_sources:
            report.append(f"| {r['db']} | {fmt_num(r['count'])} |")
        report.append("")
        report.append("---")
        report.append("")

        # === Section 5: Gene-Type Composition ===
        report.append("## 5. Gene-Type Composition")
        report.append("")
        report.append("| Organism | Protein-coding | ncRNA | Pseudogene | Other | Total |")
        report.append("|---|---|---|---|---|---|")

        for sci_name, taxid, common in ORGANISMS:
            it = org_data.get(taxid)
            if not it:
                report.append(f"| *{sci_name}* | — | — | — | — | — |")
                continue
            
            qt = it["query_taxid"]
            gene_types = run_query(session, """
                MATCH (g:Gene)-[:IN_TAXON]->(t:OrganismTaxon {id: $taxid})
                RETURN g.geneType AS type, count(*) AS count ORDER BY count DESC
            """, {"taxid": f"NCBITaxon:{qt}"})
            
            type_map = {r['type']: r['count'] for r in gene_types}
            total = sum(type_map.values())
            pc = type_map.get('PROTEIN_CODING', 0)
            ncrna = sum(v for k, v in type_map.items() if k and ('RNA' in k.upper()) and k.upper() != 'PROTEIN_CODING')
            pseudo = sum(v for k, v in type_map.items() if k and 'PSEUDO' in k.upper())
            other = total - pc - ncrna - pseudo
            
            report.append(
                f"| *{sci_name}* | {fmt_num(pc)} | {fmt_num(ncrna)} | {fmt_num(pseudo)} | {fmt_num(other)} | {fmt_num(total)} |"
            )

        report.append("")
        report.append("---")
        report.append("")

        # === Section 6: Key Takeaways ===
        report.append("## 6. Key Takeaways")
        report.append("")
        
        # Compute some summary stats
        total_pc = sum(it["pc_genes"] for it in org_data.values() if it)
        total_dom = sum(run_query(session, """
            MATCH (g:Gene)-[:IN_TAXON]->(t:OrganismTaxon {id: $taxid})
            WHERE g.geneType = 'PROTEIN_CODING'
            MATCH (g)-[:TRANSCRIBED_TO]->(:Transcript)-[:TRANSLATES_TO]->(p:Protein)-[:HAS_DOMAIN]->(:Domain)
            RETURN count(DISTINCT p) AS count
        """, {"taxid": "NCBITaxon:" + str(it["query_taxid"])})[0]['count'] for it in org_data.values() if it)
        
        report.append(f"1. **22 organisms, {fmt_num(total_pc)} protein-coding genes** in the v1.1 graph.")
        report.append(f"2. **Domain annotations now cover ALL organisms** — RPS-BLAST against CDD was run on all {fmt_num(total_pc)} protein-coding genes' proteins, not just human as in v1.0.")
        report.append(f"3. **{fmt_num(total_dom)} proteins have domain annotations** across all 22 organisms.")
        report.append("4. **IN_TAXON edges** directly connect each Gene to its OrganismTaxon, enabling efficient per-species queries without traversing the full taxonomy tree.")
        report.append("5. See the per-organism coverage matrix above for detailed breakdowns.")
        report.append("")
        report.append("---")
        report.append("")
        report.append(f"*Report generated by generate_coverage_report.py at {datetime.now().isoformat()}*")

    driver.close()
    
    # Write report
    output = "\n".join(report)
    outpath = "/mnt/results/refseq_kg/annotation_coverage_report.md"
    # Remove existing file first (S3 mount limitation)
    if os.path.exists(outpath):
        os.remove(outpath)
    with open(outpath, "w") as f:
        f.write(output)
    print(f"\nReport written to {outpath}")
    print(f"Report size: {len(output)} bytes")


if __name__ == "__main__":
    main()
