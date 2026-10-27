#!/usr/bin/env python3
"""
Run RPS-BLAST of all RefSeq proteins vs CDD, parse hits into
Domain nodes + HAS_DOMAIN edges (protein -> domain) for neo4j-admin import.

Domain node IDs are CDD:<PSSM_ID> (e.g., CDD:239227), sourced directly from
the RPS-BLAST subject accession (saccver). Domain names and sourceDb are
extracted via blastdbcmd (NOT from .smp files, which are cleaned up after
makeprofiledb formatting).

Usage: python run_rpsblast.py
Expects: /workspace/import/refseq_proteins.faa (companion FASTA from build stage)
         /workspace/refseq_src/cdd/cdd_db.* (formatted RPS-BLAST db)
Outputs: /workspace/import/nodes_Domain.csv
         /workspace/import/edges_HAS_PART_domain.csv
         /workspace/import/domain_hits.tsv (raw RPS-BLAST output)
"""
import json, os, sys, csv, subprocess
from collections import defaultdict

SRC = "/workspace/refseq_src"
IMPORT = "/workspace/import"
PROT_FASTA = f"{IMPORT}/refseq_proteins.faa"
CDD_DB = f"{SRC}/cdd/cdd_db"
RPSBLAST = "rpsblast"
BLASTDBCMD = "blastdbcmd"
EVALUE = 1e-3
THREADS = 8

os.makedirs(IMPORT, exist_ok=True)


def determine_sourcedb(acc):
    """Determine source database from CDD accession prefix."""
    acc_lower = acc.lower()
    if acc.startswith("cd"):
        return "CDD"
    elif acc_lower.startswith("pfam") or acc.startswith("PF"):
        return "Pfam"
    elif acc_lower.startswith("smart") or acc.startswith("SM"):
        return "SMART"
    elif acc.startswith("COG"):
        return "COG"
    elif acc.startswith("KOG"):
        return "KOG"
    elif acc.startswith("PRK"):
        return "PRK"
    elif acc.startswith("TIGR"):
        return "TIGR"
    elif acc.startswith("CHL"):
        return "CHL"
    else:
        return "CDD"


def extract_cdd_names(cdd_db):
    """Extract PSSM-ID-to-(name, sourceDb) mapping via blastdbcmd.

    blastdbcmd outputs literal \\t (backslash-t) as separator in some versions,
    so we handle both literal \\t and actual tab.

    Output format: CDD:<PSSM_ID>\\t<accession>, <name>, <description>
    Example:       CDD:239227\\tcd02897, A2M_2, Proteins similar to alpha2-macroglobulin...
    """
    print("=== Extracting CDD domain names via blastdbcmd ===", flush=True)
    cmd = [BLASTDBCMD, "-db", cdd_db, "-entry", "all", "-outfmt", "%a\\t%t"]
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        print(f"  blastdbcmd ERROR: {r.stderr[-500:]}", flush=True)
        return {}

    cdd_names = {}
    for line in r.stdout.strip().split("\n"):
        if not line.strip():
            continue
        # Handle both literal \t and actual tab
        if "\\t" in line:
            parts = line.split("\\t", 1)
        else:
            parts = line.split("\t", 1)
        if len(parts) == 2:
            pssm_id, title = parts
            title = title.strip()
            # Parse title: "<accession>, <name>, <description>"
            # Extract actual accession from title for sourceDb detection
            title_parts = title.split(", ", 2)
            if len(title_parts) >= 2:
                real_acc = title_parts[0]
                domain_name = title_parts[1]
            else:
                real_acc = title
                domain_name = title

            db = determine_sourcedb(real_acc)
            cdd_names[pssm_id] = (domain_name, db)

    print(f"  extracted {len(cdd_names)} CDD domain names", flush=True)
    return cdd_names


# --- Step 1: Run RPS-BLAST ---
hits_tsv = f"{IMPORT}/domain_hits.tsv"

if not os.path.exists(hits_tsv):
    print(f"=== Running RPS-BLAST: {PROT_FASTA} vs {CDD_DB} ===", flush=True)
    cmd = [
        RPSBLAST,
        "-query", PROT_FASTA,
        "-db", CDD_DB,
        "-evalue", str(EVALUE),
        "-num_threads", str(THREADS),
        "-outfmt", "6 qaccver saccver pident evalue bitscore qstart qend",
        "-out", hits_tsv,
        "-max_target_seqs", "5",
    ]
    print(f"  $ {' '.join(cmd)}", flush=True)
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        print(f"RPS-BLAST ERROR: {r.stderr[-1000:]}", flush=True)
        sys.exit(1)
    print(f"  RPS-BLAST complete: {hits_tsv}", flush=True)
else:
    print(f"=== domain_hits.tsv already exists, skipping RPS-BLAST ===", flush=True)

# --- Step 2: Extract CDD domain names via blastdbcmd ---
cdd_names = extract_cdd_names(CDD_DB)

# --- Step 3: Parse hits and emit CSVs ---
print("=== Parsing hits -> Domain nodes + HAS_DOMAIN edges ===", flush=True)
# Read all hits, keep best hit per (protein, domain) pair
best_hit = {}  # (protein_acc, domain_acc) -> (evalue, qstart, qend)
with open(hits_tsv) as f:
    for line in f:
        parts = line.strip().split("\t")
        if len(parts) < 7:
            continue
        qacc, sacc, pident, eval_str, bitscore, qstart, qend = parts[:7]
        key = (qacc, sacc)
        eval_f = float(eval_str)
        if key not in best_hit or eval_f < best_hit[key][0]:
            best_hit[key] = (eval_f, int(qstart), int(qend))

print(f"  {len(best_hit)} unique protein-domain hits", flush=True)

# Domain nodes — sacc is already CDD:<PSSM_ID> (e.g., CDD:239227)
domain_nodes = open(f"{IMPORT}/nodes_Domain.csv", "w", newline="")
dw = csv.writer(domain_nodes)
dw.writerow(["id:ID", "name", "sourceDb", "category", ":LABEL"])

seen_domains = set()
n_domains = 0
for (qacc, sacc), (eval_f, qstart, qend) in best_hit.items():
    if sacc not in seen_domains:
        seen_domains.add(sacc)
        name, db = cdd_names.get(sacc, (sacc, "CDD"))
        dw.writerow([sacc, name, db, "biolink:ProteinDomain", "Domain"])
        n_domains += 1

# HAS_DOMAIN edges (protein -> domain)
# Edge type is "HAS_DOMAIN" (not "HAS_PART") to avoid header collision
# in neo4j-admin import. Predicate is biolink:has_part.
edge_file = open(f"{IMPORT}/edges_HAS_PART_domain.csv", "w", newline="")
ew = csv.writer(edge_file)
ew.writerow([":START_ID", ":END_ID", ":TYPE", "predicate", "begin:int", "end:int", "evalue:double"])

n_edges = 0
for (qacc, sacc), (eval_f, qstart, qend) in best_hit.items():
    ew.writerow([f"RefSeq:{qacc}", sacc, "HAS_DOMAIN",
                 "biolink:has_part", qstart, qend, eval_f])
    n_edges += 1

domain_nodes.close()
edge_file.close()
print(f"  Domain nodes: {n_domains}", flush=True)
print(f"  HAS_DOMAIN edges: {n_edges}", flush=True)
print("=== RPSBLAST DOMAIN ANNOTATION COMPLETE ===", flush=True)
