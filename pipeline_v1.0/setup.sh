#!/bin/bash
#
# RefSeq KG Pipeline v1.0 — Dependency Setup
#
# Installs all external dependencies into ./deps/ (or a custom prefix):
#   - NCBI Datasets CLI v18.36.0
#   - BLAST+ 2.16.0+ (rpsblast, blastdbcmd, makeprofiledb)
#   - Temurin JDK 21
#   - Neo4j Community Edition 5.26.0
#
# Also downloads and formats the CDD PSSM database for RPS-BLAST.
#
# Usage:
#   bash setup.sh [prefix]
#   bash setup.sh /opt/refseq-kg  # install to custom location
#
set -euo pipefail

PREFIX="${1:-$(dirname "$0")/deps}"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
mkdir -p "$PREFIX"

echo "============================================"
echo "  RefSeq KG Pipeline v1.0 — Setup"
echo "  Install prefix: $PREFIX"
echo "============================================"
echo ""

# ---------- helper ----------
check_or_install() {
    local name="$1"
    local check_path="$2"
    if [ -e "$check_path" ]; then
        echo "  [SKIP] $name already installed at $check_path"
        return 0
    fi
    return 1
}

# ---------- 1. NCBI Datasets CLI ----------
echo "=== [1/5] NCBI Datasets CLI ==="
DATASETS_VERSION="18.36.0"
DATASETS_URL="https://github.com/ncbi/datasets/releases/download/v${DATASETS_VERSION}/datasets-linux-amd64"
if ! check_or_install "Datasets CLI" "$PREFIX/bin/datasets"; then
    echo "  Downloading datasets CLI v${DATASETS_VERSION}..."
    mkdir -p "$PREFIX/bin"
    curl -L -o "$PREFIX/bin/datasets" "$DATASETS_URL"
    chmod +x "$PREFIX/bin/datasets"
    # Also get dataformat (comes in same release)
    curl -L -o "$PREFIX/bin/dataformat" \
        "https://github.com/ncbi/datasets/releases/download/v${DATASETS_VERSION}/dataformat-linux-amd64"
    chmod +x "$PREFIX/bin/dataformat"
    echo "  [OK] Datasets CLI installed"
fi
echo ""

# ---------- 2. BLAST+ ----------
echo "=== [2/5] BLAST+ (rpsblast, blastdbcmd) ==="
BLAST_VERSION="2.16.0"
BLAST_URL="https://ftp.ncbi.nlm.nih.gov/blast/executables/blast+/${BLAST_VERSION}/ncbi-blast-${BLAST_VERSION}+-x64-linux.tar.gz"
BLAST_DIR="$PREFIX/ncbi-blast-${BLAST_VERSION}+"
if ! check_or_install "BLAST+" "$BLAST_DIR/bin/rpsblast"; then
    echo "  Downloading BLAST+ ${BLAST_VERSION}..."
    TMPFILE=$(mktemp /tmp/blast.XXXXXX.tar.gz)
    curl -L -o "$TMPFILE" "$BLAST_URL"
    tar xzf "$TMPFILE" -C "$PREFIX"
    rm "$TMPFILE"
    # Symlink binaries into PREFIX/bin
    for bin in rpsblast blastdbcmd makeprofiledb blastn blastp blastx tblastn; do
        ln -sf "$BLAST_DIR/bin/$bin" "$PREFIX/bin/$bin" 2>/dev/null || true
    done
    echo "  [OK] BLAST+ installed"
fi
echo ""

# ---------- 3. JDK 21 ----------
echo "=== [3/5] Temurin JDK 21 ==="
JDK_VERSION="21.0.5"
JDK_BUILD="11"
JDK_DIR="$PREFIX/jdk-${JDK_VERSION}+${JDK_BUILD}"
JDK_URL="https://github.com/adoptium/temurin21-binaries/releases/download/jdk-${JDK_VERSION}%2B${JDK_BUILD}/OpenJDK21U-jdk_x64_linux_hotspot_${JDK_VERSION}_${JDK_BUILD}.tar.gz"
if ! check_or_install "JDK 21" "$JDK_DIR/bin/java"; then
    echo "  Downloading Temurin JDK ${JDK_VERSION}+${JDK_BUILD}..."
    TMPFILE=$(mktemp /tmp/jdk.XXXXXX.tar.gz)
    curl -L -o "$TMPFILE" "$JDK_URL"
    tar xzf "$TMPFILE" -C "$PREFIX"
    rm "$TMPFILE"
    echo "  [OK] JDK 21 installed"
fi
echo ""

# ---------- 4. Neo4j Community Edition ----------
echo "=== [4/5] Neo4j Community Edition 5.26.0 ==="
NEO4J_VERSION="5.26.0"
NEO4J_DIR="$PREFIX/neo4j-community-${NEO4J_VERSION}"
NEO4J_URL="https://dist.neo4j.org/neo4j-community-${NEO4J_VERSION}-unix.tar.gz"
if ! check_or_install "Neo4j" "$NEO4J_DIR/bin/neo4j"; then
    echo "  Downloading Neo4j Community ${NEO4J_VERSION}..."
    TMPFILE=$(mktemp /tmp/neo4j.XXXXXX.tar.gz)
    curl -L -o "$TMPFILE" "$NEO4J_URL"
    tar xzf "$TMPFILE" -C "$PREFIX"
    rm "$TMPFILE"
    # Disable auth for convenience
    echo "dbms.security.auth_enabled=false" >> "$NEO4J_DIR/conf/neo4j.conf"
    echo "  [OK] Neo4j installed (auth disabled)"
fi
echo ""

# ---------- 5. CDD Database ----------
echo "=== [5/5] CDD PSSM Database ==="
CDD_DIR="${SRC_DIR:-$SCRIPT_DIR/refseq_src}/cdd"
CDD_URL="https://ftp.ncbi.nlm.nih.gov/pub/mmdb/cdd/cdd.tar.gz"
if ! check_or_install "CDD database" "$CDD_DIR/cdd_db.p*"; then
    mkdir -p "$CDD_DIR"
    if [ ! -f "$CDD_DIR/cdd.tar.gz" ]; then
        echo "  Downloading CDD database (~3GB)..."
        curl -L -o "$CDD_DIR/cdd.tar.gz" "$CDD_URL"
    fi
    echo "  Extracting CDD .smp files..."
    tar xzf "$CDD_DIR/cdd.tar.gz" -C "$CDD_DIR" --wildcards "*.smp" 2>/dev/null || true

    # Format the PSSM database with makeprofiledb
    RPSBLAST_BIN="$BLAST_DIR/bin"
    if [ -x "$RPSBLAST_BIN/makeprofiledb" ]; then
        echo "  Formatting CDD PSSM database with makeprofiledb..."
        cd "$CDD_DIR"
        # Create the input file list
        ls *.smp > pssm.list 2>/dev/null || true
        if [ -s pssm.list ]; then
            "$RPSBLAST_BIN/makeprofiledb" -title cdd_db -in pssm.list -dbtype rps -threshold 9.82 -scale 100.0 -index true
            echo "  [OK] CDD database formatted"
        else
            echo "  [WARN] No .smp files found. CDD database not formatted."
            echo "         You may need to download and extract CDD manually."
        fi
        cd "$SCRIPT_DIR"
    else
        echo "  [WARN] makeprofiledb not found. CDD database not formatted."
        echo "         BLAST+ must be installed first. Run setup.sh again."
    fi
else
    echo "  [SKIP] CDD database already formatted"
fi
echo ""

# ---------- Summary ----------
echo "============================================"
echo "  SETUP COMPLETE"
echo "============================================"
echo ""
echo "  Installed to: $PREFIX"
echo ""
echo "  Add to PATH:"
echo "    export PATH=$PREFIX/bin:\$PATH"
if [ -d "$JDK_DIR" ]; then
    echo "    export JAVA_HOME=$JDK_DIR"
    echo "    export PATH=\$JAVA_HOME/bin:\$PATH"
fi
if [ -d "$NEO4J_DIR" ]; then
    echo "    export NEO4J_HOME=$NEO4J_DIR"
fi
echo ""
echo "  Then run the pipeline:"
echo "    python run.py all"
echo ""
