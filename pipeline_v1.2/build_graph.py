#!/usr/bin/env python3
"""
RefSeq Knowledge Graph builder.
Parses NCBI Datasets gene + product reports for 8 organisms, hashes sequences,
and emits neo4j-admin-import-compatible node/edge CSVs plus companion FASTA.

BioLink-conformant: every node has a `category` property (biolink CURIE),
every edge has a `predicate` property (biolink CURIE).
"""
import json, os, sys, csv, hashlib, glob, re
from collections import defaultdict

SRC = "/workspace/refseq_src"
IMPORT = "/workspace/import"
RESULTS = "/mnt/results/refseq_kg"
os.makedirs(IMPORT, exist_ok=True)
os.makedirs(RESULTS, exist_ok=True)

# ---------- BioLink mapping ----------
NODE_CATEGORY = {
    "OrganismTaxon": "biolink:OrganismTaxon",
    "Genome": "biolink:Genome",
    "Chromosome": "biolink:Chromosome",
    "Gene": "biolink:Gene",
    "Transcript": "biolink:Transcript",
    "Protein": "biolink:Protein",
    "GOTerm": "biolink:GeneOntologyClass",
    "Domain": "biolink:ProteinDomain",
}
GO_ASPECT_CATEGORY = {
    "molecular_function": "biolink:MolecularFunction",
    "biological_process": "biolink:BiologicalProcess",
    "cellular_component": "biolink:CellularComponent",
}
GO_QUALIFIER_PRED = {
    "enables": ("ENABLES", "biolink:enables"),
    "involved_in": ("ACTIVELY_INVOLVED_IN", "biolink:actively_involved_in"),
    "located_in": ("LOCATED_IN", "biolink:located_in"),
    "part_of": ("GO_PART_OF", "biolink:part_of"),
    "contributes_to": ("CONTRIBUTES_TO", "biolink:contributes_to"),
    "acts_upstream_of": ("ACTS_UPSTREAM_OF", "biolink:acts_upstream_of"),
    "acts_upstream_of_or_within": ("ACTS_UPSTREAM_OF_OR_WITHIN", "biolink:acts_upstream_of_or_within"),
    "is_active_in": ("IS_ACTIVE_IN", "biolink:is_active_in"),
    "colocalizes_with": ("COLOCALIZES_WITH", "biolink:colocalizes_with"),
}
DEFAULT_GO_PRED = ("RELATED_TO", "biolink:related_to")

EDGE_PREDICATE = {
    "PART_OF": "biolink:part_of",
    "HAS_PART": "biolink:has_part",
    "HAS_SEQUENCE_LOCATION": "biolink:has_sequence_location",
    "TRANSCRIBED_TO": "biolink:transcribed_to",
    "TRANSLATES_TO": "biolink:translates_to",
    "HAS_GENE_PRODUCT": "biolink:has_gene_product",
    "ORTHOLOGOUS_TO": "biolink:orthologous_to",
    "IN_TAXON": "biolink:in_taxon",
}

# ---------- helpers ----------
def arr(v):
    """Join list to ;-delimited string for neo4j :string[] import."""
    if not v:
        return ""
    if isinstance(v, list):
        return ";".join(str(x) for x in v if x is not None and str(x) != "")
    return str(v)

def safe(s):
    if s is None:
        return ""
    return str(s).replace("\n", " ").replace("\r", " ").strip()

def md5_of(seq):
    return hashlib.md5(seq.upper().encode()).hexdigest()

def gc_of(seq):
    seq = seq.upper()
    n = len(seq)
    if n == 0:
        return 0.0
    gc = sum(1 for c in seq if c in "GC")
    return round(100.0 * gc / n, 2)

AA = "ACDEFGHIKLMNPQRSTVWY"
def aa_comp(seq):
    seq = seq.upper()
    n = len(seq)
    comp = {}
    for a in AA:
        comp[a] = sum(1 for c in seq if c == a)
    comp["other"] = sum(1 for c in seq if c not in AA and c != "*")
    comp["length"] = n
    return json.dumps(comp, separators=(",", ":"))

def fasta_iter(path):
    """Yield (id, seq) for each record in a FASTA file."""
    if not os.path.exists(path):
        return
    hid, chunks = None, []
    with open(path) as f:
        for line in f:
            line = line.rstrip("\n")
            if line.startswith(">"):
                if hid is not None:
                    yield hid, "".join(chunks)
                hid = line[1:].split()[0]
                chunks = []
            else:
                chunks.append(line)
        if hid is not None:
            yield hid, "".join(chunks)

# ---------- CSV writers ----------
class NodeWriter:
    def __init__(self, path, header):
        self.f = open(path, "w", newline="")
        self.w = csv.writer(self.f)
        self.w.writerow(header)
        self.header = header
        self.n = 0
    def write(self, row):
        self.w.writerow(row)
        self.n += 1
    def close(self):
        self.f.close()

class EdgeWriter:
    def __init__(self, path, header):
        self.f = open(path, "w", newline="")
        self.w = csv.writer(self.f)
        self.w.writerow(header)
        self.header = header
        self.n = 0
    def write(self, row):
        self.w.writerow(row)
        self.n += 1
    def close(self):
        self.f.close()

# ---------- main ----------
def main():
    manifest = json.load(open(f"{SRC}/manifest.json"))
    orgs = manifest["organisms"]
    # representative assembly per gene_taxid
    repr_asm = {o["gene_taxid"]: o["assembly_accession"] for o in orgs}
    org_meta = {o["gene_taxid"]: o for o in orgs}

    # --- chromosome lengths from genome seq-reports ---
    # sequence_report.jsonl lives under data/<asm_acc>/ in the genome package
    chr_len = {}
    for o in orgs:
        gtx = o["gene_taxid"]
        sr_files = glob.glob(f"{SRC}/genome_{gtx}/ncbi_dataset/data/*/sequence_report.jsonl")
        for sr in sr_files:
            with open(sr) as f:
                for line in f:
                    if not line.strip():
                        continue
                    rec = json.loads(line)
                    ln = rec.get("length")
                    if not ln:
                        continue
                    # key by both refseq and genbank accessions
                    for acc in (rec.get("refseqAccession"), rec.get("genbankAccession")):
                        if acc:
                            chr_len[acc] = int(ln)
    print(f"chromosome lengths loaded for {len(chr_len)} sequences")

    # --- taxonomy lineages ---
    lineages = json.load(open(f"{SRC}/lineage.json"))

    # --- open writers ---
    nw = {}
    nw["OrganismTaxon"] = NodeWriter(f"{IMPORT}/nodes_OrganismTaxon.csv",
        ["id:ID","name","rank","commonName","category",":LABEL"])
    nw["Genome"] = NodeWriter(f"{IMPORT}/nodes_Genome.csv",
        ["id:ID","assemblyName","annotationName","releaseDate","category",":LABEL"])
    nw["Chromosome"] = NodeWriter(f"{IMPORT}/nodes_Chromosome.csv",
        ["id:ID","sequenceName","length:int","category",":LABEL"])
    nw["Gene"] = NodeWriter(f"{IMPORT}/nodes_Gene.csv",
        ["id:ID","symbol","description","geneType","orientation","synonyms:string[]",
         "ensemblGeneId","omimIds:string[]","swissprotAccessions:string[]","summary","category",":LABEL"])
    nw["Transcript"] = NodeWriter(f"{IMPORT}/nodes_Transcript.csv",
        ["id:ID","name","length:int","md5","gc:double","transcriptType","selectCategory",
         "ensemblTranscript","category",":LABEL"])
    nw["Protein"] = NodeWriter(f"{IMPORT}/nodes_Protein.csv",
        ["id:ID","name","length:int","md5","aaComposition","isoformName","ensemblProtein",
         "uniprotAccession","category",":LABEL"])
    nw["GOTerm"] = NodeWriter(f"{IMPORT}/nodes_GOTerm.csv",
        ["id:ID","name","aspect","category",":LABEL"])
    nw["Domain"] = NodeWriter(f"{IMPORT}/nodes_Domain.csv",
        ["id:ID","name","sourceDb","category",":LABEL"])

    ew = {}
    ew["PART_OF"] = EdgeWriter(f"{IMPORT}/edges_PART_OF.csv",
        [":START_ID",":END_ID",":TYPE","predicate"])
    ew["HAS_PART"] = EdgeWriter(f"{IMPORT}/edges_HAS_PART.csv",
        [":START_ID",":END_ID",":TYPE","predicate"])
    ew["HAS_SEQUENCE_LOCATION"] = EdgeWriter(f"{IMPORT}/edges_HAS_SEQUENCE_LOCATION.csv",
        [":START_ID",":END_ID",":TYPE","predicate","begin:int","end:int","orientation"])
    ew["TRANSCRIBED_TO"] = EdgeWriter(f"{IMPORT}/edges_TRANSCRIBED_TO.csv",
        [":START_ID",":END_ID",":TYPE","predicate"])
    ew["TRANSLATES_TO"] = EdgeWriter(f"{IMPORT}/edges_TRANSLATES_TO.csv",
        [":START_ID",":END_ID",":TYPE","predicate","cdsBegin:int","cdsEnd:int"])
    ew["HAS_GENE_PRODUCT"] = EdgeWriter(f"{IMPORT}/edges_HAS_GENE_PRODUCT.csv",
        [":START_ID",":END_ID",":TYPE","predicate"])
    ew["ORTHOLOGOUS_TO"] = EdgeWriter(f"{IMPORT}/edges_ORTHOLOGOUS_TO.csv",
        [":START_ID",":END_ID",":TYPE","predicate","groupId","method"])
    ew["IN_TAXON"] = EdgeWriter(f"{IMPORT}/edges_IN_TAXON.csv",
        [":START_ID",":END_ID",":TYPE","predicate"])
    # GO edges: one writer per predicate type
    go_ew = {}
    def go_writer(pred_type):
        if pred_type not in go_ew:
            go_ew[pred_type] = EdgeWriter(f"{IMPORT}/edges_GO_{pred_type}.csv",
                [":START_ID",":END_ID",":TYPE","predicate","evidenceCode","qualifier","assignedBy","pmids:string[]","negated:boolean"])
        return go_ew[pred_type]
    # Domain/site/region edges added later from GenPept-derived CSVs (parse_genpept.py)

    seen_nodes = defaultdict(set)  # label -> set of ids (dedup)
    seen_edges = defaultdict(set)  # (type, start, end) -> dedup
    ortho_groups = defaultdict(list)  # group_id -> [gene_node_ids]
    go_terms = {}  # goid -> (name, aspect)
    comp_fasta_rna = open(f"{IMPORT}/refseq_transcripts.fna", "w")
    comp_fasta_protein = open(f"{IMPORT}/refseq_proteins.faa", "w")

    def add_node(label, nid, props):
        if nid in seen_nodes[label]:
            return
        seen_nodes[label].add(nid)
        nw[label].write(props)

    def add_edge(etype, start, end, row_prefix, dedup_key=None):
        key = (etype, start, end) if dedup_key is None else dedup_key
        if key in seen_edges[etype]:
            return
        seen_edges[etype].add(key)
        ew[etype].write(row_prefix)

    # --- build taxonomy tree (all organisms) ---
    all_taxa = {}  # taxid -> (name, rank)
    for tx, lin in lineages.items():
        prev = None
        for i, t in enumerate(lin):
            tid = t["taxid"]
            all_taxa[tid] = (t["name"], t["rank"])
            is_leaf = (i == len(lin) - 1)
            common = org_meta.get(int(tx), {}).get("common_name", "") if is_leaf else ""
            add_node("OrganismTaxon", f"NCBITaxon:{tid}",
                [f"NCBITaxon:{tid}", safe(t["name"]), safe(t["rank"]), safe(common),
                 NODE_CATEGORY["OrganismTaxon"], "OrganismTaxon"])
            if prev is not None:
                add_edge("PART_OF", f"NCBITaxon:{tid}", f"NCBITaxon:{prev}",
                    [f"NCBITaxon:{tid}", f"NCBITaxon:{prev}", "PART_OF", EDGE_PREDICATE["PART_OF"]])
            prev = tid
    print(f"taxonomy: {len(all_taxa)} taxa, {ew['PART_OF'].n} part_of edges")

    # --- process each organism ---
    gene_count = 0
    gene_swiss = {}  # gene_id -> swissprot accessions (from data_report)
    for o in orgs:
        gtx = o["gene_taxid"]
        gdir = f"{SRC}/gene_{gtx}/ncbi_dataset/data"
        dr_path = f"{gdir}/data_report.jsonl"
        pr_path = f"{gdir}/product_report.jsonl"
        if not os.path.exists(dr_path):
            print(f"WARNING: no data_report for taxon {gtx}, skipping")
            continue
        asm = o["assembly_accession"]
        asm_name = o["assembly_name"]
        ann_name = o["annotation_name"]
        rel_date = o["annotation_release_date"]
        genome_id = f"RefSeqAssembly:{asm}"
        add_node("Genome", genome_id,
            [genome_id, safe(asm_name), safe(ann_name), safe(rel_date),
             NODE_CATEGORY["Genome"], "Genome"])
        # organism -> genome
        org_id = f"NCBITaxon:{gtx}"
        add_edge("HAS_PART", org_id, genome_id,
            [org_id, genome_id, "HAS_PART", EDGE_PREDICATE["HAS_PART"]])

        # sequence hashes from genome package (data/<asm_acc>/protein.faa, rna.fna)
        rna_hash = {}
        for fa in glob.glob(f"{SRC}/genome_{gtx}/ncbi_dataset/data/*/rna.fna"):
            for rid, seq in fasta_iter(fa):
                rna_hash[rid] = (len(seq), md5_of(seq), gc_of(seq))
                comp_fasta_rna.write(f">{rid}\n{seq}\n")
        prot_hash = {}
        for fa in glob.glob(f"{SRC}/genome_{gtx}/ncbi_dataset/data/*/protein.faa"):
            for pid, seq in fasta_iter(fa):
                prot_hash[pid] = (len(seq), md5_of(seq), aa_comp(seq))
                comp_fasta_protein.write(f">{pid}\n{seq}\n")
        print(f"  {o['scientific_name']}: {len(rna_hash)} rna, {len(prot_hash)} protein sequences loaded")

        # --- parse gene data report ---
        local_genes = 0
        with open(dr_path) as f:
            for line in f:
                if not line.strip():
                    continue
                g = json.loads(line)
                gid = g.get("geneId")
                if not gid:
                    continue
                # filter: only keep genes annotated on the representative assembly
                repr_ann = None
                for ann in (g.get("annotations") or []):
                    if ann.get("assemblyAccession") == asm:
                        repr_ann = ann
                        break
                if repr_ann is None:
                    continue  # gene not on reference assembly
                gene_id = f"NCBIGene:{gid}"
                swiss = g.get("swissProtAccessions") or []
                add_node("Gene", gene_id,
                    [gene_id, safe(g.get("symbol")), safe(g.get("description")),
                     safe(g.get("type")), safe(g.get("orientation")),
                     arr(g.get("synonyms")),
                     safe((g.get("ensemblGeneIds") or [""])[0]),
                     arr(g.get("omimIds")), arr(swiss),
                     safe((g.get("summary") or [{}])[0].get("description","")) if g.get("summary") else "",
                     NODE_CATEGORY["Gene"], "Gene"])
                # direct gene -> organism taxon edge
                add_edge("IN_TAXON", gene_id, org_id,
                    [gene_id, org_id, "IN_TAXON", EDGE_PREDICATE["IN_TAXON"]])
                # genomic location on representative assembly
                for gl in (repr_ann.get("genomicLocations") or []):
                    chr_acc = gl.get("genomicAccessionVersion")
                    if not chr_acc:
                        continue
                    chr_id = f"RefSeq:{chr_acc}"
                    gr = gl.get("genomicRange") or {}
                    add_node("Chromosome", chr_id,
                        [chr_id, safe(gl.get("sequenceName")), chr_len.get(chr_acc, 0),
                         NODE_CATEGORY["Chromosome"], "Chromosome"])
                    add_edge("HAS_PART", genome_id, chr_id,
                        [genome_id, chr_id, "HAS_PART", EDGE_PREDICATE["HAS_PART"]])
                    add_edge("HAS_SEQUENCE_LOCATION", gene_id, chr_id,
                        [gene_id, chr_id, "HAS_SEQUENCE_LOCATION",
                         EDGE_PREDICATE["HAS_SEQUENCE_LOCATION"],
                         gr.get("begin",""), gr.get("end",""), safe(gr.get("orientation"))])
                    break  # primary location only
                # GO annotations
                go = g.get("geneOntology")
                if go:
                    assigned_by = safe(go.get("assignedBy"))
                    for aspect_key, aspect in [("molecularFunctions","molecular_function"),
                                               ("biologicalProcesses","biological_process"),
                                               ("cellularComponents","cellular_component")]:
                        for item in (go.get(aspect_key) or []):
                            goid = item.get("goId")
                            if not goid:
                                continue
                            goname = safe(item.get("name"))
                            go_terms[goid] = (goname, aspect)
                            qual = (item.get("qualifier") or "").strip()
                            # handle NOT prefix and effect suffixes
                            negated = qual.startswith("NOT ")
                            base_qual = qual[4:] if negated else qual
                            # strip _negative_effect / _positive_effect for predicate lookup
                            lookup_qual = base_qual
                            for suffix in ["_negative_effect", "_positive_effect"]:
                                if lookup_qual.endswith(suffix):
                                    lookup_qual = lookup_qual[:-len(suffix)]
                                    break
                            pred_type, pred_curie = GO_QUALIFIER_PRED.get(lookup_qual, DEFAULT_GO_PRED)
                            pmids = arr((item.get("reference") or {}).get("pmids"))
                            gw = go_writer(pred_type)
                            key = (pred_type, gene_id, goid, qual, pmids)
                            if key not in seen_edges[pred_type]:
                                seen_edges[pred_type].add(key)
                                gw.write([gene_id, goid, pred_type, pred_curie,
                                          safe(item.get("evidenceCode")), safe(qual),
                                          assigned_by, pmids, "true" if negated else "false"])
                # ortholog groups
                for gg in (g.get("geneGroups") or []):
                    if gg.get("method") == "NCBI Ortholog" and gg.get("id"):
                        ortho_groups[gg["id"]].append(gene_id)
                # save swissprot accessions for product report parsing
                gene_swiss[gid] = swiss
                local_genes += 1
                gene_count += 1

        # --- parse product report ---
        n_tx, n_pr = 0, 0
        if os.path.exists(pr_path):
            with open(pr_path) as f:
                for line in f:
                    if not line.strip():
                        continue
                    g = json.loads(line)
                    gid = g.get("geneId")
                    if not gid:
                        continue
                    gene_id = f"NCBIGene:{gid}"
                    swiss = gene_swiss.get(gid, [])
                    uniprot = swiss[0] if swiss else ""
                    for t in (g.get("transcripts") or []):
                        tacc = t.get("accessionVersion")
                        if not tacc:
                            continue
                        # only keep transcripts present in the reference genome FASTA
                        if tacc not in rna_hash:
                            continue
                        tid = f"RefSeq:{tacc}"
                        rh = rna_hash[tacc]
                        add_node("Transcript", tid,
                            [tid, safe(t.get("name")), rh[0],
                             rh[1], rh[2], safe(t.get("type")), safe(t.get("selectCategory")),
                             safe(t.get("ensemblTranscript")),
                             NODE_CATEGORY["Transcript"], "Transcript"])
                        add_edge("TRANSCRIBED_TO", gene_id, tid,
                            [gene_id, tid, "TRANSCRIBED_TO", EDGE_PREDICATE["TRANSCRIBED_TO"]])
                        n_tx += 1
                        pr = t.get("protein")
                        if pr and pr.get("accessionVersion"):
                            pacc = pr.get("accessionVersion")
                            # only keep proteins present in the reference genome FASTA
                            if pacc not in prot_hash:
                                continue
                            pid = f"RefSeq:{pacc}"
                            ph = prot_hash[pacc]
                            add_node("Protein", pid,
                                [pid, safe(pr.get("name")), ph[0],
                                 ph[1], ph[2], safe(pr.get("isoformName")),
                                 safe(pr.get("ensemblProtein")), uniprot,
                                 NODE_CATEGORY["Protein"], "Protein"])
                            cds = t.get("cds") or {}
                            cds_range = (cds.get("range") or [{}])[0]
                            add_edge("TRANSLATES_TO", tid, pid,
                                [tid, pid, "TRANSLATES_TO", EDGE_PREDICATE["TRANSLATES_TO"],
                                 cds_range.get("begin",""), cds_range.get("end","")])
                            add_edge("HAS_GENE_PRODUCT", gene_id, pid,
                                [gene_id, pid, "HAS_GENE_PRODUCT", EDGE_PREDICATE["HAS_GENE_PRODUCT"]])
                            n_pr += 1
        print(f"taxon {gtx} {o['scientific_name']}: {local_genes} genes, {n_tx} transcripts, {n_pr} proteins")

    comp_fasta_rna.close()
    comp_fasta_protein.close()
    # copy companion FASTA to results (use shell cp for S3 mount compatibility)
    import shutil
    try:
        shutil.copy(f"{IMPORT}/refseq_proteins.faa", f"{RESULTS}/refseq_proteins.faa")
    except Exception as e:
        print(f"WARNING: could not copy protein FASTA to results: {e}")
    # skip transcript FASTA copy — too large for S3 mount, copy separately later

    # --- write GO term nodes ---
    for goid, (goname, aspect) in go_terms.items():
        cat = GO_ASPECT_CATEGORY.get(aspect, NODE_CATEGORY["GOTerm"])
        add_node("GOTerm", goid,
            [goid, goname, aspect, cat, "GOTerm"])
    print(f"GO terms: {len(go_terms)}")

    # --- ortholog edges (within-graph, pairwise within group) ---
    n_ortho = 0
    for gid, genes in ortho_groups.items():
        genes = sorted(set(genes))
        for i in range(len(genes)):
            for j in range(i+1, len(genes)):
                add_edge("ORTHOLOGOUS_TO", genes[i], genes[j],
                    [genes[i], genes[j], "ORTHOLOGOUS_TO", EDGE_PREDICATE["ORTHOLOGOUS_TO"],
                     str(gid), "NCBI Ortholog"])
                n_ortho += 1
    print(f"ortholog groups: {len(ortho_groups)} groups, {n_ortho} edges")

    # --- close writers ---
    for w in nw.values(): w.close()
    for w in ew.values(): w.close()
    for w in go_ew.values(): w.close()

    # --- stats ---
    stats = {
        "nodes": {l: w.n for l, w in nw.items()},
        "edges_PART_OF": ew["PART_OF"].n,
        "edges_HAS_PART": ew["HAS_PART"].n,
        "edges_HAS_SEQUENCE_LOCATION": ew["HAS_SEQUENCE_LOCATION"].n,
        "edges_TRANSCRIBED_TO": ew["TRANSCRIBED_TO"].n,
        "edges_TRANSLATES_TO": ew["TRANSLATES_TO"].n,
        "edges_HAS_GENE_PRODUCT": ew["HAS_GENE_PRODUCT"].n,
        "edges_ORTHOLOGOUS_TO": ew["ORTHOLOGOUS_TO"].n,
        "edges_IN_TAXON": ew["IN_TAXON"].n,
        "edges_GO": {k: w.n for k, w in go_ew.items()},
        "total_genes": gene_count,
    }
    with open(f"{IMPORT}/build_stats.json", "w") as f:
        json.dump(stats, f, indent=2)
    print("\n=== BUILD STATS ===")
    print(json.dumps(stats, indent=2))

if __name__ == "__main__":
    main()
