#!/bin/bash
# Parallel RPS-BLAST: split proteins into N chunks, run rpsblast in parallel
# Then merge results and parse into Domain nodes + edges

set -e
export PATH=/workspace/bin:$PATH

IMPORT=/workspace/import
CDD_DB=/workspace/refseq_src/cdd/cdd_db
PROT_FASTA=$IMPORT/refseq_proteins.faa
NCHUNKS=4
THREADS=2  # per process (NCHUNKS * THREADS = 8 total)

echo "=== Step 0: Preload CDD database into page cache ==="
cat /workspace/refseq_src/cdd/cdd_db.*.rps > /dev/null 2>&1 &
cat /workspace/refseq_src/cdd/cdd_db.*.freq > /dev/null 2>&1 &
cat /workspace/refseq_src/cdd/cdd_db.*.pin > /dev/null 2>&1 &
cat /workspace/refseq_src/cdd/cdd_db.*.phr > /dev/null 2>&1 &
cat /workspace/refseq_src/cdd/cdd_db.*.pdb > /dev/null 2>&1 &
wait
echo "  Database preloaded into page cache"
free -h

echo "=== Step 1: Split protein FASTA into $NCHUNKS chunks ==="
TOTAL=$(grep -c "^>" $PROT_FASTA)
echo "  Total proteins: $TOTAL"
CHUNK_SIZE=$(( (TOTAL + NCHUNKS - 1) / NCHUNKS ))
echo "  Proteins per chunk: ~$CHUNK_SIZE"

awk -v chunk=$CHUNK_SIZE -v nchunks=$NCHUNKS -v prefix="$IMPORT/chunk_" '
BEGIN { file_idx=1; count=0 }
/^>/ {
    if (count >= chunk && file_idx < nchunks) {
        file_idx++
        count=0
    }
    count++
}
{ print > prefix file_idx ".faa" }
' $PROT_FASTA

for i in $(seq 1 $NCHUNKS); do
    n=$(grep -c "^>" $IMPORT/chunk_$i.faa)
    echo "  chunk_$i.faa: $n proteins"
done

echo "=== Step 2: Run $NCHUNKS parallel rpsblast processes ==="
PIDS=""
for i in $(seq 1 $NCHUNKS); do
    echo "  Starting rpsblast chunk $i ($THREADS threads)..."
    rpsblast \
        -query $IMPORT/chunk_$i.faa \
        -db $CDD_DB \
        -evalue 1e-3 \
        -num_threads $THREADS \
        -outfmt "6 qaccver saccver pident evalue bitscore qstart qend" \
        -out $IMPORT/hits_chunk_$i.tsv \
        -max_target_seqs 5 &
    PIDS="$PIDS $!"
done

echo "  Waiting for all rpsblast processes to complete..."
wait $PIDS
echo "  All rpsblast processes complete"

echo "=== Step 3: Merge hit files ==="
> $IMPORT/domain_hits.tsv
for i in $(seq 1 $NCHUNKS); do
    if [ -f $IMPORT/hits_chunk_$i.tsv ]; then
        cat $IMPORT/hits_chunk_$i.tsv >> $IMPORT/domain_hits.tsv
        n=$(wc -l < $IMPORT/hits_chunk_$i.tsv)
        echo "  hits_chunk_$i.tsv: $n lines"
    fi
done
TOTAL_HITS=$(wc -l < $IMPORT/domain_hits.tsv)
echo "  Total merged hits: $TOTAL_HITS lines"

echo "=== Step 4: Clean up chunk files ==="
rm -f $IMPORT/chunk_*.faa $IMPORT/hits_chunk_*.tsv
echo "  Chunk files removed"

echo "=== Step 5: Parse hits into Domain nodes + edges ==="
python3 /workspace/run_rpsblast.py 2>&1

echo "=== RPS-BLAST pipeline complete ==="
