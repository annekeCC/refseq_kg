#!/usr/bin/env python3
"""
RefSeq Knowledge Graph Pipeline v1.1 — CLI orchestrator.

Builds a BioLink-conformant Neo4j property graph from NCBI RefSeq data
for 22 model organisms. Produces import-ready CSVs, companion FASTA files,
and a restorable Neo4j database dump.

Usage:
    python run.py --version              Print version
    python run.py setup                  Install dependencies
    python run.py download               Download gene + genome data from NCBI
    python run.py taxonomy               Fetch taxonomy lineages from EUtils
    python run.py build                  Build graph CSVs + companion FASTA
    python run.py domains                Run RPS-BLAST domain annotation
    python run.py import                 Import into Neo4j + apply schema + verify
    python run.py dump                   Create Neo4j database dump
    python run.py all                    Run all stages in sequence
    python run.py all --skip-domains     Full pipeline minus RPS-BLAST

Global options:
    --src-dir DIR        Source data directory (default: ./refseq_src)
    --import-dir DIR     Import CSV directory (default: ./import)
    --results-dir DIR    Results/output directory (default: ./results)
    --threads N          CPU threads for RPS-BLAST (default: 8)
    --neo4j-home DIR     Neo4j installation (default: ./deps/neo4j)
    --java-home DIR      JDK installation (default: auto-detect)
    --datasets PATH      NCBI datasets CLI path (default: auto-detect)
    --cdd-db PATH        CDD RPS-BLAST database (default: <src-dir>/cdd/cdd_db)
    --manifest PATH      manifest.json path (default: <src-dir>/manifest.json)
"""
import os, sys, subprocess, argparse, time

__version__ = "1.1"

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))


def run_stage(stage_name, module_name, extra_args=None):
    """Run a pipeline stage as a subprocess."""
    module_path = os.path.join(SCRIPT_DIR, f"{module_name}.py")
    cmd = [sys.executable, module_path] + (extra_args or [])
    print(f"\n{'='*60}", flush=True)
    print(f"  STAGE: {stage_name}", flush=True)
    print(f"{'='*60}\n", flush=True)
    t0 = time.time()
    r = subprocess.run(cmd)
    elapsed = time.time() - t0
    if r.returncode != 0:
        print(f"\n  STAGE FAILED: {stage_name} ({elapsed:.0f}s)", flush=True)
        sys.exit(1)
    print(f"\n  STAGE COMPLETE: {stage_name} ({elapsed:.0f}s)", flush=True)
    return True


def main():
    # Handle --version before argparse requires stage
    if "--version" in sys.argv:
        print(f"refseq_kg {__version__}")
        return

    ap = argparse.ArgumentParser(
        description="RefSeq Knowledge Graph Pipeline v1.0",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    ap.add_argument("stage", choices=[
        "all", "setup", "download", "taxonomy", "build", "domains", "import", "dump"
    ], help="Pipeline stage to run")
    ap.add_argument("--version", action="store_true", help="Print version and exit")
    ap.add_argument("--src-dir", default="./refseq_src", help="Source data directory")
    ap.add_argument("--import-dir", default="./import", help="Import CSV directory")
    ap.add_argument("--results-dir", default="./results", help="Results directory")
    ap.add_argument("--threads", type=int, default=8, help="CPU threads")
    ap.add_argument("--neo4j-home", default="./deps/neo4j", help="Neo4j installation")
    ap.add_argument("--java-home", default=None, help="JDK installation")
    ap.add_argument("--datasets", default=None, help="NCBI datasets CLI path")
    ap.add_argument("--cdd-db", default=None, help="CDD RPS-BLAST database path")
    ap.add_argument("--manifest", default=None, help="manifest.json path")
    ap.add_argument("--skip-domains", action="store_true",
                    help="Skip RPS-BLAST domain annotation (for 'all' stage)")
    ap.add_argument("--skip-dump", action="store_true",
                    help="Skip dump creation (for 'import' stage)")
    args = ap.parse_args()

    if args.version:
        print(f"refseq_kg {__version__}")
        return

    # Build common args for all stages
    common = []
    if args.src_dir:
        common += ["--src-dir", args.src_dir]
    if args.import_dir:
        common += ["--import-dir", args.import_dir]
    if args.results_dir:
        common += ["--results-dir", args.results_dir]
    if args.manifest:
        common += ["--manifest", args.manifest]

    # Auto-detect datasets CLI
    datasets_cli = args.datasets
    if not datasets_cli:
        for candidate in [f"{SCRIPT_DIR}/deps/datasets", "datasets"]:
            if os.path.exists(candidate) or subprocess.run(
                ["which", candidate], capture_output=True).returncode == 0:
                datasets_cli = candidate
                break
        else:
            datasets_cli = "datasets"

    # Auto-detect CDD database
    cdd_db = args.cdd_db or f"{args.src_dir}/cdd/cdd_db"

    # Auto-detect Java
    java_home = args.java_home
    if not java_home:
        for candidate in [f"{SCRIPT_DIR}/deps/jdk-21", os.environ.get("JAVA_HOME")]:
            if candidate and os.path.exists(candidate):
                java_home = candidate
                break

    print(f"refseq_kg v{__version__}", flush=True)
    print(f"  src-dir:    {args.src_dir}", flush=True)
    print(f"  import-dir: {args.import_dir}", flush=True)
    print(f"  results-dir: {args.results_dir}", flush=True)
    print(f"  threads:    {args.threads}", flush=True)
    print(f"  neo4j-home: {args.neo4j_home}", flush=True)
    print(f"  java-home:  {java_home or '(auto)'}", flush=True)
    print(f"  datasets:   {datasets_cli}", flush=True)
    print(f"  cdd-db:     {cdd_db}", flush=True)

    if args.stage == "setup":
        setup_script = os.path.join(SCRIPT_DIR, "setup.sh")
        print(f"\n=== Running setup.sh ===", flush=True)
        r = subprocess.run(["bash", setup_script], cwd=SCRIPT_DIR)
        sys.exit(r.returncode)

    if args.stage == "download":
        run_stage("Download", "download",
                  common + ["--datasets", datasets_cli])
        return

    if args.stage == "taxonomy":
        run_stage("Taxonomy", "taxonomy", common)
        return

    if args.stage == "build":
        run_stage("Build Graph", "build_graph", common)
        return

    if args.stage == "domains":
        run_stage("Domain Annotation", "domains",
                  ["--import-dir", args.import_dir,
                   "--cdd-db", cdd_db,
                   "--threads", str(args.threads)])
        return

    if args.stage == "import":
        import_args = ["--import-dir", args.import_dir,
                       "--results-dir", args.results_dir,
                       "--neo4j-home", args.neo4j_home]
        if java_home:
            import_args += ["--java-home", java_home]
        if args.skip_dump:
            import_args += ["--skip-dump"]
        run_stage("Neo4j Import", "neo4j_import", import_args)
        return

    if args.stage == "dump":
        # dump is part of import stage; run import with dump only
        import_args = ["--import-dir", args.import_dir,
                       "--results-dir", args.results_dir,
                       "--neo4j-home", args.neo4j_home]
        if java_home:
            import_args += ["--java-home", java_home]
        # For dump-only, we'd need to skip the import and just dump.
        # For simplicity, redirect to import stage.
        print("Note: dump is performed as part of the import stage.", flush=True)
        print("Run 'python run.py import' to import + dump.", flush=True)
        return

    if args.stage == "all":
        t_total = time.time()
        print(f"\n{'#'*60}", flush=True)
        print(f"  FULL PIPELINE: ALL STAGES", flush=True)
        print(f"{'#'*60}", flush=True)

        # 1. Download
        run_stage("Download", "download",
                  common + ["--datasets", datasets_cli])

        # 2. Taxonomy
        run_stage("Taxonomy", "taxonomy", common)

        # 3. Build graph
        run_stage("Build Graph", "build_graph", common)

        # 4. Domains (optional)
        if not args.skip_domains:
            run_stage("Domain Annotation", "domains",
                      ["--import-dir", args.import_dir,
                       "--cdd-db", cdd_db,
                       "--threads", str(args.threads)])
        else:
            print("\n  SKIPPING: Domain Annotation (--skip-domains)", flush=True)

        # 5. Neo4j import + dump
        import_args = ["--import-dir", args.import_dir,
                       "--results-dir", args.results_dir,
                       "--neo4j-home", args.neo4j_home]
        if java_home:
            import_args += ["--java-home", java_home]
        run_stage("Neo4j Import + Dump", "neo4j_import", import_args)

        elapsed_total = time.time() - t_total
        print(f"\n{'#'*60}", flush=True)
        print(f"  PIPELINE COMPLETE ({elapsed_total/60:.1f} min)", flush=True)
        print(f"{'#'*60}", flush=True)
        return


if __name__ == "__main__":
    main()
