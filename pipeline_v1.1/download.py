#!/usr/bin/env python3
"""
RefSeq KG Pipeline v1.0 — Download stage.

Downloads gene metadata (product-report) and genome sequences (protein, rna,
seq-report) for all organisms in the manifest via the NCBI Datasets CLI.

Handles both reference genomes (--reference flag) and representative genomes
(downloaded by assembly accession, which is required for rat GRCr8 and
zebrafish GRCz12ab).

Usage:
    python download.py --src-dir ./refseq_src --datasets ./deps/datasets
"""
import json, os, subprocess, sys, time, argparse

__version__ = "1.0"


def run(cmd):
    """Run a command, print it, return success."""
    print(f"  $ {' '.join(cmd)}", flush=True)
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        print(f"  ERROR: {r.stderr[-500:]}", flush=True)
        return False
    return True


def download_organism(o, src_dir, datasets_cli):
    """Download gene metadata + genome sequences for one organism."""
    gtx = o["gene_taxid"]
    name = o["scientific_name"].replace(" ", "_")
    gene_dir = f"{src_dir}/gene_{gtx}"
    genome_dir = f"{src_dir}/genome_{gtx}"
    os.makedirs(gene_dir, exist_ok=True)
    os.makedirs(genome_dir, exist_ok=True)

    # --- 1. Gene metadata (product-report) ---
    gene_data = f"{gene_dir}/ncbi_dataset/data/data_report.jsonl"
    if not os.path.exists(gene_data):
        print(f"\n=== GENE metadata: {name} (taxon {gtx}) ===", flush=True)
        t0 = time.time()
        gene_zip = f"{gene_dir}/gene.zip"
        if run([datasets_cli, "download", "gene", "taxon", str(gtx),
                "--include", "product-report",
                "--filename", gene_zip, "--no-progressbar"]):
            subprocess.run(["unzip", "-o", "-q", gene_zip, "-d", gene_dir], check=True)
            os.remove(gene_zip)
            n = sum(1 for _ in open(gene_data))
            print(f"  data_report: {n} genes ({time.time()-t0:.0f}s)", flush=True)
        else:
            return False
    else:
        print(f"  GENE metadata: {name} already present", flush=True)

    # --- 2. Genome sequences ---
    genome_data = f"{genome_dir}/ncbi_dataset/data/dataset_catalog.json"
    if not os.path.exists(genome_data):
        print(f"\n=== GENOME sequences: {name} (taxon {gtx}) ===", flush=True)
        t0 = time.time()
        genome_zip = f"{genome_dir}/genome.zip"

        # Use --reference for reference genomes, --accession for representative ones
        is_reference = o.get("refseq_category", "") == "reference genome"
        if is_reference:
            cmd = [datasets_cli, "download", "genome", "taxon", str(gtx),
                   "--reference", "--assembly-source", "RefSeq",
                   "--include", "protein,rna,seq-report",
                   "--filename", genome_zip, "--no-progressbar"]
        else:
            # Representative genome: download by assembly accession
            asm_acc = o["assembly_accession"]
            cmd = [datasets_cli, "download", "genome", "accession", asm_acc,
                   "--include", "protein,rna,seq-report",
                   "--filename", genome_zip, "--no-progressbar"]

        if run(cmd):
            subprocess.run(["unzip", "-o", "-q", genome_zip, "-d", genome_dir], check=True)
            os.remove(genome_zip)
            print(f"  done ({time.time()-t0:.0f}s)", flush=True)
        else:
            return False
    else:
        print(f"  GENOME sequences: {name} already present", flush=True)

    return True


def main():
    ap = argparse.ArgumentParser(description="Download NCBI RefSeq data for KG build")
    ap.add_argument("--src-dir", default="./refseq_src", help="Source data directory")
    ap.add_argument("--datasets", default="datasets", help="Path to NCBI datasets CLI")
    ap.add_argument("--manifest", default=None, help="Path to manifest.json (default: <src-dir>/manifest.json)")
    args = ap.parse_args()

    manifest_path = args.manifest or f"{args.src_dir}/manifest.json"
    manifest = json.load(open(manifest_path))

    print(f"=== DOWNLOAD STAGE: {len(manifest['organisms'])} organisms ===", flush=True)
    failed = []
    for o in manifest["organisms"]:
        if not download_organism(o, args.src_dir, args.datasets):
            failed.append(o["scientific_name"])

    if failed:
        print(f"\n=== DOWNLOAD COMPLETE WITH ERRORS: {len(failed)} failed ===", flush=True)
        for f in failed:
            print(f"  FAILED: {f}", flush=True)
        sys.exit(1)
    else:
        print(f"\n=== ALL DOWNLOADS COMPLETE ===", flush=True)


if __name__ == "__main__":
    main()
