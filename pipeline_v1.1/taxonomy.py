#!/usr/bin/env python3
"""
RefSeq KG Pipeline v1.0 — Taxonomy stage.

Fetches NCBI taxonomy lineages for all organism gene_taxids in the manifest
via the NCBI EUtils API. Writes lineage.json: {taxid: [{taxid, rank, name}, ...]}
from root to organism.

Usage:
    python taxonomy.py --src-dir ./refseq_src
"""
import json, os, urllib.request, argparse
import xml.etree.ElementTree as ET

__version__ = "1.0"

EUTILS = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"


def fetch_taxonomy(taxids):
    """Fetch full lineage chains for a list of taxids via EUtils efetch."""
    url = f"{EUTILS}/efetch.fcgi?db=taxonomy&id={','.join(map(str, taxids))}&rettype=xml"
    req = urllib.request.Request(url, headers={"User-Agent": "RefSeqKG/1.0"})
    with urllib.request.urlopen(req, timeout=60) as r:
        data = r.read()

    root = ET.fromstring(data)
    lineages = {}
    for taxon in root.findall("Taxon"):
        tid = taxon.findtext("TaxId")
        name = taxon.findtext("ScientificName")
        rank = taxon.findtext("Rank")

        lineage = []
        lex = taxon.find("LineageEx")
        if lex is not None:
            for lt in lex.findall("Taxon"):
                lineage.append({
                    "taxid": lt.findtext("TaxId"),
                    "rank": lt.findtext("Rank") or "no rank",
                    "name": lt.findtext("ScientificName"),
                })
        # Append the organism itself as the leaf
        lineage.append({"taxid": tid, "rank": rank or "no rank", "name": name})
        lineages[tid] = lineage

    return lineages


def main():
    ap = argparse.ArgumentParser(description="Fetch NCBI taxonomy lineages")
    ap.add_argument("--src-dir", default="./refseq_src", help="Source data directory")
    ap.add_argument("--manifest", default=None, help="Path to manifest.json")
    args = ap.parse_args()

    manifest_path = args.manifest or f"{args.src_dir}/manifest.json"
    manifest = json.load(open(manifest_path))

    # Use gene_taxid (yeast genes are under 559292, not 4932)
    taxids = [int(o["gene_taxid"]) for o in manifest["organisms"]]
    print(f"=== TAXONOMY STAGE: fetching lineages for {len(taxids)} taxids ===", flush=True)

    lineages = fetch_taxonomy(taxids)
    for tid, lin in lineages.items():
        tail = " > ".join(n["name"] for n in lin[-4:])
        print(f"  taxid {tid}: {len(lin)} ranks -> {tail}", flush=True)

    out = f"{args.src_dir}/lineage.json"
    with open(out, "w") as f:
        json.dump(lineages, f, indent=2)
    print(f"\n=== TAXONOMY COMPLETE: wrote {out} ===", flush=True)


if __name__ == "__main__":
    main()
