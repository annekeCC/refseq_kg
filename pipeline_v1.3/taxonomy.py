#!/usr/bin/env python3
"""
RefSeq KG Pipeline v1.3 — Taxonomy stage.

Fetches NCBI taxonomy lineages for all organism gene_taxids in the manifest
via the NCBI Datasets CLI (datasets summary taxonomy taxon). Writes
lineage.json: {taxid: [{taxid, rank, name}, ...]} from root to organism.

v1.3 change: taxonomy data now comes from NCBI Datasets instead of EUtils.
The Datasets taxon report provides the full parent chain per taxon; ranks are
normalized to the same vocabulary the EUtils feed used (lowercase; taxa
without a rank in Datasets become "no rank"). The taxonomy root (taxid 1) is
dropped to match the EUtils LineageEx convention (chains start at
"cellular organisms", taxid 131567).

Requires: datasets CLI (installed by setup.sh).

Usage:
    python taxonomy.py --src-dir ./refseq_src
"""
import json, os, subprocess, argparse

__version__ = "1.3"

# Datasets omits the rank field for taxa NCBI Taxonomy calls "no rank"
# (e.g. Oryza sativa Japonica Group, taxid 39947).
DEFAULT_RANK = "no rank"

# EUtils LineageEx chains start at cellular organisms (131567); the Datasets
# parents list includes the taxonomy root (1), which we drop for equivalence.
TAXONOMY_ROOT = 1

# Ancestor lookups are batched to keep CLI invocations bounded.
BATCH_SIZE = 25


def run_datasets(taxids, datasets_bin="datasets"):
    """Run one batched `datasets summary taxonomy taxon` call, return reports."""
    cmd = [datasets_bin, "summary", "taxonomy", "taxon"] + [str(t) for t in taxids]
    cmd += ["--report", "taxonomy"]
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
    if r.returncode != 0:
        raise RuntimeError(f"datasets CLI failed (rc={r.returncode}): {r.stderr[:500]}")
    data = json.loads(r.stdout)
    reports = {}
    for rep in data.get("reports", []):
        t = rep.get("taxonomy", {})
        tid = str(t.get("tax_id"))
        reports[tid] = {
            "taxid": tid,
            "rank": (t.get("rank") or DEFAULT_RANK).lower().replace("_", " "),
            "name": t.get("current_scientific_name", {}).get("name", ""),
            "parents": [int(p) for p in t.get("parents", [])],
        }
    return reports


def fetch_taxonomy(taxids, datasets_bin="datasets"):
    """Fetch full lineage chains for a list of taxids via NCBI Datasets."""
    # 1. Self reports for all organisms in one batched call
    self_reports = run_datasets(taxids, datasets_bin)
    missing = [str(t) for t in taxids if str(t) not in self_reports]
    if missing:
        raise RuntimeError(f"Datasets returned no report for taxids: {missing}")

    # 2. Collect the union of ancestors (drop the taxonomy root) and batch-query
    ancestor_ids = sorted({p for r in self_reports.values()
                           for p in r["parents"] if p != TAXONOMY_ROOT})
    ancestors = {}
    for i in range(0, len(ancestor_ids), BATCH_SIZE):
        batch = ancestor_ids[i:i + BATCH_SIZE]
        ancestors.update(run_datasets(batch, datasets_bin))

    # 3. Assemble chains: parents (root-first) + self
    lineages = {}
    for tid in taxids:
        self_r = self_reports[str(tid)]
        chain = []
        for p in self_r["parents"]:
            if p == TAXONOMY_ROOT:
                continue
            a = ancestors.get(str(p))
            if a is None:
                raise RuntimeError(f"Missing ancestor report for taxid {p}")
            chain.append({"taxid": a["taxid"], "rank": a["rank"], "name": a["name"]})
        chain.append({"taxid": self_r["taxid"], "rank": self_r["rank"], "name": self_r["name"]})
        lineages[str(tid)] = chain

    return lineages


def main():
    ap = argparse.ArgumentParser(description="Fetch NCBI taxonomy lineages (NCBI Datasets)")
    ap.add_argument("--src-dir", default="./refseq_src", help="Source data directory")
    ap.add_argument("--manifest", default=None, help="Path to manifest.json")
    ap.add_argument("--datasets-bin", default=os.environ.get("DATASETS_BIN", "datasets"),
                    help="Path to the NCBI datasets CLI binary")
    args = ap.parse_args()

    manifest_path = args.manifest or f"{args.src_dir}/manifest.json"
    manifest = json.load(open(manifest_path))

    # Use gene_taxid (yeast genes are under 559292, not 4932)
    taxids = [int(o["gene_taxid"]) for o in manifest["organisms"]]
    print(f"=== TAXONOMY STAGE: fetching lineages for {len(taxids)} taxids via NCBI Datasets ===", flush=True)

    lineages = fetch_taxonomy(taxids, args.datasets_bin)
    for tid, lin in lineages.items():
        tail = " > ".join(n["name"] for n in lin[-4:])
        print(f"  taxid {tid}: {len(lin)} ranks -> {tail}", flush=True)

    out = f"{args.src_dir}/lineage.json"
    with open(out, "w") as f:
        json.dump(lineages, f, indent=2)
    print(f"\n=== TAXONOMY COMPLETE: wrote {out} ===", flush=True)


if __name__ == "__main__":
    main()
