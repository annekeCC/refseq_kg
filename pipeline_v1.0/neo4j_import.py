#!/usr/bin/env python3
"""
RefSeq KG Pipeline v1.0 — Neo4j import stage.

Imports node/edge CSVs into Neo4j using neo4j-admin database import full,
applies schema (constraints + indexes), runs verification queries, and
creates a database dump.

Uses the default 'neo4j' database (Community Edition supports only one DB).
Auth is disabled in the generated neo4j.conf for testing convenience.

Prerequisites:
  - Neo4j Community Edition 5.26+ installed
  - JDK 21+ installed
  - All node/edge CSVs in the import directory (from build + domains stages)

Usage:
    python neo4j_import.py --import-dir ./import --results-dir ./results \\
        --neo4j-home /opt/neo4j --java-home /opt/jdk-21
"""
import os, sys, subprocess, time, argparse, signal, glob

__version__ = "1.0"


def run(cmd, check=True, timeout=300):
    """Run a command, print it, return the CompletedProcess."""
    print(f"  $ {' '.join(cmd)}", flush=True)
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    if r.stdout:
        print(r.stdout, flush=True)
    if r.returncode != 0 and check:
        print(f"  STDERR: {r.stderr[-1000:]}", flush=True)
        if check:
            raise RuntimeError(f"Command failed: {' '.join(cmd)}")
    return r


def stop_neo4j(neo4j_home, timeout=120):
    """Stop Neo4j, with fallback to killing by PID if graceful stop times out."""
    print("=== Stopping Neo4j ===", flush=True)
    try:
        r = subprocess.run([f"{neo4j_home}/bin/neo4j", "stop"],
                           capture_output=True, text=True, timeout=timeout)
        print(r.stdout, flush=True)
        if r.returncode == 0:
            return True
    except subprocess.TimeoutExpired:
        pass

    # Fallback: find and kill the Neo4j Java process by PID file
    print("  Graceful stop failed, trying PID kill...", flush=True)
    pid_file = f"{neo4j_home}/run/neo4j.pid"
    if os.path.exists(pid_file):
        with open(pid_file) as f:
            pid = int(f.read().strip())
        try:
            os.kill(pid, signal.SIGTERM)
            time.sleep(10)
            # Check if still alive, force kill if needed
            try:
                os.kill(pid, 0)
                os.kill(pid, signal.SIGKILL)
                time.sleep(5)
            except ProcessLookupError:
                pass  # Already dead
            print(f"  Killed Neo4j process (pid {pid})", flush=True)
            return True
        except Exception as e:
            print(f"  PID kill failed: {e}", flush=True)

    # Last resort: pkill the specific Java process
    subprocess.run(["pkill", "-f", f"{neo4j_home}.*neo4j"],
                   capture_output=True, timeout=30)
    time.sleep(10)
    return True


def start_neo4j(neo4j_home):
    """Start Neo4j and wait for it to be ready."""
    print("=== Starting Neo4j ===", flush=True)
    r = subprocess.run([f"{neo4j_home}/bin/neo4j", "start"],
                       capture_output=True, text=True, timeout=60)
    print(r.stdout, flush=True)
    if r.returncode != 0:
        print(f"  STDERR: {r.stderr[-500:]}", flush=True)
        raise RuntimeError("Failed to start Neo4j")
    # Wait for server to be ready
    print("  Waiting for Neo4j to be ready...", flush=True)
    time.sleep(20)
    return True


def cypher_query(neo4j_home, query, database="neo4j"):
    """Run a Cypher query via cypher-shell."""
    r = subprocess.run([f"{neo4j_home}/bin/cypher-shell", "--format", "plain",
                        "--database", database, query],
                       capture_output=True, text=True, timeout=120)
    return r.stdout.strip()


def main():
    ap = argparse.ArgumentParser(description="Import CSVs into Neo4j and create dump")
    ap.add_argument("--import-dir", default="./import", help="Directory with node/edge CSVs")
    ap.add_argument("--results-dir", default="./results", help="Output directory for dump")
    ap.add_argument("--neo4j-home", default="./neo4j", help="Neo4j installation directory")
    ap.add_argument("--java-home", default=None, help="JDK installation directory")
    ap.add_argument("--schema-file", default=None, help="schema.cypher path (default: <pipeline-dir>/schema.cypher)")
    ap.add_argument("--skip-dump", action="store_true", help="Skip dump creation")
    args = ap.parse_args()

    IMPORT = args.import_dir
    RESULTS = args.results_dir
    NEO4J_HOME = args.neo4j_home

    # Set JAVA_HOME if provided
    env = os.environ.copy()
    if args.java_home:
        env["JAVA_HOME"] = args.java_home
        env["PATH"] = f"{args.java_home}/bin:" + env.get("PATH", "")

    # Schema file
    schema_file = args.schema_file
    if not schema_file:
        # Try same directory as this script
        script_dir = os.path.dirname(os.path.abspath(__file__))
        schema_file = f"{script_dir}/schema.cypher"
    if not os.path.exists(schema_file):
        print(f"WARNING: schema.cypher not found at {schema_file}", flush=True)

    # --- Stop Neo4j if running ---
    stop_neo4j(NEO4J_HOME)
    time.sleep(5)

    # --- Build node and relationship file lists ---
    node_files = sorted(glob.glob(f"{IMPORT}/nodes_*.csv"))
    edge_files = sorted(glob.glob(f"{IMPORT}/edges_*.csv"))

    if not node_files:
        print(f"ERROR: No node CSVs found in {IMPORT}", flush=True)
        sys.exit(1)

    print(f"=== Running neo4j-admin import ===", flush=True)
    print(f"  Node files: {len(node_files)}", flush=True)
    print(f"  Edge files: {len(edge_files)}", flush=True)

    import_cmd = [
        f"{NEO4J_HOME}/bin/neo4j-admin", "database", "import", "full", "neo4j",
        "--overwrite-destination=true",
        "--skip-bad-relationships=true",
        "--skip-duplicate-nodes=true",
        f"--report-file={IMPORT}/import_report.txt",
    ]
    for nf in node_files:
        import_cmd.append(f"--nodes={nf}")
    for ef in edge_files:
        import_cmd.append(f"--relationships={ef}")

    r = subprocess.run(import_cmd, capture_output=True, text=True, timeout=600, env=env)
    print(r.stdout, flush=True)
    if r.returncode != 0:
        print(f"  STDERR: {r.stderr[-2000:]}", flush=True)
        sys.exit(1)

    # --- Start Neo4j ---
    start_neo4j(NEO4J_HOME)

    # --- Apply schema ---
    if os.path.exists(schema_file):
        print("\n=== Applying schema ===", flush=True)
        subprocess.run([f"{NEO4J_HOME}/bin/cypher-shell", "--file", schema_file],
                       capture_output=True, text=True, timeout=120, env=env)
        time.sleep(5)

    # --- Verification queries ---
    print("\n=== Verification ===", flush=True)

    print("\n--- Node counts ---", flush=True)
    print(cypher_query(NEO4J_HOME,
        "MATCH (n) RETURN labels(n)[0] AS label, count(*) AS count ORDER BY count DESC;"))

    print("\n--- Edge counts ---", flush=True)
    print(cypher_query(NEO4J_HOME,
        "MATCH ()-[r]->() RETURN type(r) AS type, count(*) AS count ORDER BY count DESC;"))

    print("\n--- TP53 traversal ---", flush=True)
    print(cypher_query(NEO4J_HOME,
        "MATCH (g:Gene {symbol: 'TP53'})-[:TRANSCRIBED_TO]->(t:Transcript)"
        "-[:TRANSLATES_TO]->(p:Protein) "
        "RETURN g.symbol, g.id, t.id, p.id, p.uniprotAccession LIMIT 5;"))

    print("\n--- Missing category ---", flush=True)
    print(cypher_query(NEO4J_HOME,
        "MATCH (n) WHERE n.category IS NULL RETURN count(*) AS missing_category;"))

    print("\n--- Missing predicate ---", flush=True)
    print(cypher_query(NEO4J_HOME,
        "MATCH ()-[r]->() WHERE r.predicate IS NULL RETURN count(*) AS missing_predicate;"))

    print("\n--- Species count ---", flush=True)
    print(cypher_query(NEO4J_HOME,
        "MATCH (o:OrganismTaxon {rank: 'species'}) RETURN count(*) AS species_count;"))

    # --- Create dump ---
    if not args.skip_dump:
        print("\n=== Creating dump ===", flush=True)
        stop_neo4j(NEO4J_HOME)
        time.sleep(10)

        dump_cmd = [f"{NEO4J_HOME}/bin/neo4j-admin", "database", "dump", "neo4j",
                     f"--to-path={RESULTS}"]
        r = subprocess.run(dump_cmd, capture_output=True, text=True, timeout=300, env=env)
        print(r.stdout, flush=True)
        if r.returncode != 0:
            print(f"  STDERR: {r.stderr[-500:]}", flush=True)
            sys.exit(1)

        dump_file = f"{RESULTS}/neo4j.dump"
        if os.path.exists(dump_file):
            size_mb = os.path.getsize(dump_file) / (1024 * 1024)
            print(f"  Dump created: {dump_file} ({size_mb:.0f} MB)", flush=True)
        else:
            print(f"  WARNING: dump file not found at {dump_file}", flush=True)

    print("\n=== IMPORT STAGE COMPLETE ===", flush=True)


if __name__ == "__main__":
    main()
