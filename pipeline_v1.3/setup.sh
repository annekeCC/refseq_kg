#!/bin/bash
#
# RefSeq KG Pipeline v1.1 — Dependency Setup
#
# Installs all external dependencies into ./deps/ (or a custom prefix):
#   - NCBI Datasets CLI v18.36.0
#   - Temurin JDK 21
#   - Neo4j Community Edition 5.26.0
#
# Also downloads the small cddid.tbl mapping (no BLAST+ or PSSM database needed in v1.2).
# CDD download is ~3GB compressed; formatted database is ~36GB.
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
echo "  RefSeq KG Pipeline v1.1 — Setup"
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

# ---------- 2. JDK 21 ----------
# (v1.2: BLAST+ is no longer needed — domains come from NCBI's pre-computed
#  GenPept annotations via EUtils efetch, not local RPS-BLAST)
echo "=== [2/4] Temurin JDK 21 ==="
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

# ---------- 3. Neo4j Community Edition ----------
echo "=== [3/4] Neo4j Community Edition 5.26.0 ==="
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

# ---------- 4. CDD domain name mapping (small, needed by parse_genpept.py) ----------
echo "=== [4/4] CDD PSSM-ID mapping table ==="
# v1.2: only the small cddid.tbl (PSSM_ID -> accession/name mapping, ~5MB) is
# needed to resolve Domain names. The 36GB formatted PSSM database is NOT
# required — domain hits come pre-computed in GenPept records.
CDD_DIR="${SRC_DIR:-$SCRIPT_DIR/refseq_src}/cdd"
CDDID_URL="https://ftp.ncbi.nlm.nih.gov/pub/mmdb/cdd/cddid.tbl.gz"
if [ ! -f "$CDD_DIR/cddid.tbl" ]; then
    mkdir -p "$CDD_DIR"
    echo "  Downloading cddid.tbl (~5MB compressed)..."
    curl -L -o "$CDD_DIR/cddid.tbl.gz" "$CDDID_URL"
    gunzip -f "$CDD_DIR/cddid.tbl.gz"
    echo "  [OK] cddid.tbl downloaded"
else
    echo "  [SKIP] cddid.tbl already present"
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
