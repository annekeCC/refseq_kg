#!/usr/bin/env python3
"""
RefSeq KG Pipeline v1.0 — Domain annotation stage.

Runs RPS-BLAST of all RefSeq proteins against the CDD (Conserved Domain
Database) PSSM database, parses hits into Domain nodes + HAS_DOMAIN edges
for neo4j-admin import.

Domain node IDs are CDD:<PSSM_ID> (e.g., CDD:239227), sourced from the
RPS-BLAST subject accession. Domain names are extracted via blastdbcmd
to get the PSSM-ID-to-title mapping (NOT from .smp file parsing, which
was buggy in earlier versions).

Prerequisites:
  - rpsblast and blastdbcmd from BLAST+ must be on PATH
  - CDD PSSM database must be formatted (run setup.sh or makeprofiledb)
  - Companion protein FASTA must exist from the build stage

Usage:
    python domains.py --import-dir ./import --cdd-db ./refseq_src/cdd/cdd_db --threads 8
"""
import json, os, sys, csv, subprocess, glob, argparse
from collections import defaultdict

__version__ = "1.0"


def run_rpsblast(protein_fasta, cdd_db, hits_tsv, evalue, threads):
    """Run RPS-BLAST if hits file doesn't already exist."""
    if os.path.exists(hits_tsv) and os.path.getsize(hits_tsv) > 0:
        print(f"  domain_hits.tsv already exists, skipping RPS-BLAST", flush=True)
        return True

    print(f"=== Running RPS-BLAST: {protein_fasta} vs {cdd_db} ===", flush=True)
    cmd = [
        "rpsblast",
        "-query", protein_fasta,
        "-db", cdd_db,
        "-evalue", str(evalue),
        "-num_threads", str(threads),
        "-outfmt", "6 qaccver saccver pident evalue bitscore qstart qend",
        "-out", hits_tsv,
        "-max_target_seqs", "5",
    ]
    print(f"  $ {' '.join(cmd)}", flush=True)
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        print(f"  RPS-BLAST ERROR: {r.stderr[-1000:]}", flush=True)
        return False
    print(f"  RPS-BLAST complete: {hits_tsv}", flush=True)
    return True


def extract_cdd_names(cdd_db):
    """Extract PSSM-ID-to-title mapping via blastdbcmd.

    blastdbcmd outputs literal \\t (backslash-t) as separator in some versions,
    so we handle both literal \\t and actual tab.
    """
    print(f"=== Extracting CDD domain names via blastdbcmd ===", flush=True)
    cmd = ["blastdbcmd", "-db", cdd_db, "-entry", "all",
           "-outfmt", "%a\t%t"]
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
            acc, title = parts
            # Determine source database from accession prefix
            acc_lower = acc.lower()
            if acc.startswith("cd"):
                db = "CDD"
            elif acc_lower.startswith("pfam") or acc.startswith("PF"):
                db = "Pfam"
            elif acc_lower.startswith("smart") or acc.startswith("SM"):
                db = "SMART"
            elif acc.startswith("COG"):
                db = "COG"
            elif acc.startswith("KOG"):
                db = "KOG"
            elif acc.startswith("PRK"):
                db = "PRK"
            elif acc.startswith("TIGR"):
                db = "TIGR"
            elif acc.startswith("CHL"):
                db = "CHL"
            else:
                db = "CDD"
            cdd_names[acc] = (title.strip(), db)

    print(f"  extracted {len(cdd_names)} CDD domain names", flush=True)
    return cdd_names


def parse_hits(hits_tsv):
    """Parse RPS-BLAST hits, keeping best hit per (protein, domain) pair."""
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
    return best_hit


def main():
    ap = argparse.ArgumentParser(description="RPS-BLAST domain annotation")
    ap.add_argument("--import-dir", default="./import", help="Import CSV directory")
    ap.add_argument("--cdd-db", default="./refseq_src/cdd/cdd_db", help="CDD RPS-BLAST database path")
    ap.add_argument("--threads", type=int, default=8, help="RPS-BLAST threads")
    ap.add_argument("--evalue", type=float, default=1e-3, help="E-value threshold")
    args = ap.parse_args()

    IMPORT = args.import_dir
    PROT_FASTA = f"{IMPORT}/refseq_proteins.faa"
    CDD_DB = args.cdd_db
    hits_tsv = f"{IMPORT}/domain_hits.tsv"

    if not os.path.exists(PROT_FASTA):
        print(f"ERROR: {PROT_FASTA} not found. Run build stage first.", flush=True)
        sys.exit(1)

    # Step 1: Run RPS-BLAST
    if not run_rpsblast(PROT_FASTA, CDD_DB, hits_tsv, args.evalue, args.threads):
        sys.exit(1)

    # Step 2: Extract CDD domain names via blastdbcmd
    cdd_names = extract_cdd_names(CDD_DB)

    # Step 3: Parse hits
    print(f"=== Parsing hits -> Domain nodes + HAS_DOMAIN edges ===", flush=True)
    best_hit = parse_hits(hits_tsv)

    # Step 4: Write Domain nodes
    domain_nodes = open(f"{IMPORT}/nodes_Domain.csv", "w", newline="")
    dw = csv.writer(domain_nodes)
    dw.writerow(["id:ID", "name", "sourceDb", "category", ":LABEL"])

    seen_domains = set()
    n_domains = 0
    for (qacc, sacc), (eval_f, qstart, qend) in best_hit.items():
        if sacc not in seen_domains:
            seen_domains.add(sacc)
            name, db = cdd_names.get(sacc, (sacc, "CDD"))
            dw.writerow([f"CDD:{sacc}", name, db, "biolink:ProteinDomain", "Domain"])
            n_domains += 1

    # Step 5: Write HAS_DOMAIN edges
    # NOTE: Edge type is "HAS_DOMAIN" (not "HAS_PART") to avoid header collision
    # in neo4j-admin import. Predicate is still biolink:has_part.
    edge_file = open(f"{IMPORT}/edges_HAS_PART_domain.csv", "w", newline="")
    ew = csv.writer(edge_file)
    ew.writerow([":START_ID", ":END_ID", ":TYPE", "predicate", "begin:int", "end:int", "evalue:double"])

    n_edges = 0
    for (qacc, sacc), (eval_f, qstart, qend) in best_hit.items():
        ew.writerow([f"RefSeq:{qacc}", f"CDD:{sacc}", "HAS_DOMAIN",
                     "biolink:has_part", qstart, qend, eval_f])
        n_edges += 1

    domain_nodes.close()
    edge_file.close()
    print(f"  Domain nodes: {n_domains}", flush=True)
    print(f"  HAS_DOMAIN edges: {n_edges}", flush=True)
    print(f"\n=== DOMAIN ANNOTATION COMPLETE ===", flush=True)


if __name__ == "__main__":
    main()
