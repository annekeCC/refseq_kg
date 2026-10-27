#!/usr/bin/env python3
"""
Fetch GenPept records from NCBI EUtils efetch and extract protein features.
Parallelized with 10 concurrent workers.
"""
import os, sys, time, json, csv, gzip, io, threading
import urllib.request, urllib.parse
from concurrent.futures import ThreadPoolExecutor, as_completed

API_KEY = os.environ.get('NCBI_API_KEY', '67a42d6e33ded3f5440281823ee758663c08')
EUTILS_URL = 'https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi'
BATCH_SIZE = 500
MAX_WORKERS = 10
CHECKPOINT_FILE = '/mnt/shared-workspace/shared/genpept_checkpoint.json'
RAW_DIR = '/workspace/genpept_raw'
OUTPUT_DIR = '/workspace/genpept_output'
PROTEIN_CSV = '/mnt/results/refseq_kg/import/nodes_Protein.csv'
CDDID_LOCAL = '/workspace/cddid.tbl'

os.makedirs(RAW_DIR, exist_ok=True)
os.makedirs(OUTPUT_DIR, exist_ok=True)
data_lock = threading.Lock()
stats_lock = threading.Lock()


def download_cddid():
    if os.path.exists(CDDID_LOCAL):
        return
    print("  Downloading cddid.tbl.gz...", flush=True)
    req = urllib.request.Request('https://ftp.ncbi.nlm.nih.gov/pub/mmdb/cdd/cddid.tbl.gz')
    resp = urllib.request.urlopen(req, timeout=60)
    with gzip.open(io.BytesIO(resp.read()), 'rt') as f:
        with open(CDDID_LOCAL, 'w') as out:
            out.write(f.read())
    print(f"  cddid.tbl saved ({os.path.getsize(CDDID_LOCAL)} bytes)", flush=True)


def load_cddid():
    mapping = {}
    if not os.path.exists(CDDID_LOCAL):
        return mapping
    with open(CDDID_LOCAL) as f:
        for line in f:
            parts = line.strip().split('\t')
            if len(parts) >= 4:
                pssm_id, accession, short_name = parts[0], parts[1], parts[2]
                acc_lower = accession.lower()
                if acc_lower.startswith('pfam') or acc_lower.startswith('pf'):
                    source_db = 'Pfam'
                elif acc_lower.startswith('smart'):
                    source_db = 'SMART'
                elif acc_lower.startswith('cog'):
                    source_db = 'COG'
                elif acc_lower.startswith('prk'):
                    source_db = 'PRK'
                elif acc_lower.startswith('tigr'):
                    source_db = 'TIGR'
                elif acc_lower.startswith('chl'):
                    source_db = 'CHL'
                elif acc_lower.startswith('kog'):
                    source_db = 'KOG'
                else:
                    source_db = 'CDD'
                mapping[pssm_id] = {'short_name': short_name, 'sourceDb': source_db}
    return mapping


def read_protein_accessions():
    accessions = []
    with open(PROTEIN_CSV) as f:
        reader = csv.DictReader(f)
        for row in reader:
            accessions.append(row['id:ID'].replace('RefSeq:', ''))
    return accessions


def parse_genpept(text):
    records = []
    for chunk in text.split('\n//\n'):
        chunk = chunk.strip()
        if not chunk:
            continue
        acc = None
        for line in chunk.split('\n'):
            if line.startswith('VERSION'):
                parts = line.split()
                if len(parts) >= 2:
                    acc = parts[1]
                break
        if not acc:
            continue
        features = []
        in_features = False
        cur_type = None
        cur_loc = None
        cur_quals = {}
        for line in chunk.split('\n'):
            if line.startswith('FEATURES'):
                in_features = True
                continue
            if line.startswith('ORIGIN') or line.startswith('//'):
                if cur_type:
                    features.append((cur_type, cur_loc, cur_quals))
                in_features = False
                cur_type = cur_loc = None
                cur_quals = {}
                break
            if not in_features:
                continue
            if line.startswith('     ') and not line.startswith('                     '):
                if cur_type:
                    features.append((cur_type, cur_loc, cur_quals))
                stripped = line.strip()
                parts = stripped.split(None, 1)
                cur_type = parts[0] if parts else None
                cur_loc = parts[1] if len(parts) > 1 else ''
                cur_quals = {}
            elif line.startswith('                     /'):
                ql = line.strip()
                if ql.startswith('/'):
                    if '=' in ql:
                        qn, qv = ql[1:].split('=', 1)
                        cur_quals[qn] = cur_quals.get(qn, '') + ' ' + qv if qn in cur_quals else qv
                    else:
                        cur_quals[ql[1:]] = 'true'
            elif line.startswith('                     ') and cur_quals:
                last_key = list(cur_quals.keys())[-1]
                cur_quals[last_key] += ' ' + line.strip()
        if cur_type:
            features.append((cur_type, cur_loc, cur_quals))
        records.append({'accession': acc, 'features': features})
    return records


def extract_location_bounds(loc_str):
    if not loc_str or not loc_str.strip():
        return None, None
    clean = loc_str.strip().replace('<', '').replace('>', '')
    while True:
        for prefix in ('order(', 'join(', 'complement(', 'one-of('):
            if clean.startswith(prefix) and clean.endswith(')'):
                clean = clean[len(prefix):-1]
                break
        else:
            break
    positions = []
    for part in clean.split(','):
        part = part.strip()
        if not part:
            continue
        if '..' in part:
            for s in part.split('..'):
                s = s.strip()
                if s.isdigit():
                    positions.append(int(s))
        elif part.isdigit():
            positions.append(int(part))
    return (min(positions), max(positions)) if positions else (None, None)


def process_batch(batch_idx, batch_accs, cddid, shared_data, shared_stats):
    post_data = urllib.parse.urlencode({
        'db': 'protein', 'id': ','.join(batch_accs),
        'rettype': 'gp', 'retmode': 'text', 'api_key': API_KEY
    }).encode()
    try:
        req = urllib.request.Request(EUTILS_URL, data=post_data)
        resp = urllib.request.urlopen(req, timeout=120)
        raw_text = resp.read().decode('utf-8', errors='replace')
    except Exception as e:
        return batch_idx, False, str(e), batch_accs

    with open(os.path.join(RAW_DIR, f'batch_{batch_idx:05d}.txt'), 'w') as f:
        f.write(raw_text)

    records = parse_genpept(raw_text)
    ls = {'total_records': 0, 'records_with_features': 0,
          'cdd_regions': 0, 'cdd_sites': 0, 'refseq_regions': 0, 'refseq_sites': 0,
          'skipped_uniprot': 0, 'not_found': 0}
    ld, lde, ls_, lse, lr, lre = {}, [], {}, [], {}, []
    found_accs = set(r['accession'] for r in records)
    ls['not_found'] = len(set(batch_accs) - found_accs)

    for rec in records:
        acc = rec['accession']
        pid = f'RefSeq:{acc}'
        ls['total_records'] += 1
        has_feat = False
        for ft, loc, quals in rec['features']:
            if ft not in ('Region', 'Site'):
                continue
            try:
                if 'propagated from UniProtKB' in quals.get('note', ''):
                    ls['skipped_uniprot'] += 1
                    continue
                cdd_id = None
                dbxref = quals.get('db_xref', '')
                if 'CDD:' in dbxref:
                    cdd_id = dbxref.split('CDD:')[1].strip('"').strip()
                begin, end = extract_location_bounds(loc)

                if ft == 'Region' and cdd_id:
                    ls['cdd_regions'] += 1
                    has_feat = True
                    did = f'CDD:{cdd_id}'
                    if did not in ld:
                        rn = quals.get('region_name', '')
                        ci = cddid.get(cdd_id, {})
                        ld[did] = {'name': ci.get('short_name', rn), 'sourceDb': ci.get('sourceDb', 'CDD')}
                    if begin is not None:
                        lde.append({'start': pid, 'end': did, 'begin': begin, 'end': end})
                elif ft == 'Region' and not cdd_id:
                    ls['refseq_regions'] += 1
                    has_feat = True
                    rn = quals.get('region_name', 'unnamed')
                    rid = f"ProteinRegion:{acc}:{rn}:{begin}:{end}"
                    if rid not in lr:
                        lr[rid] = {'name': rn, 'source': 'RefSeq'}
                    if begin is not None:
                        lre.append({'start': pid, 'end': rid, 'begin': begin, 'end': end})
                elif ft == 'Site':
                    st = quals.get('site_type', 'other')
                    note = ' '.join(quals.get('note', '').split())
                    if cdd_id:
                        ls['cdd_sites'] += 1
                    else:
                        ls['refseq_sites'] += 1
                    has_feat = True
                    src = 'CDD' if cdd_id else 'RefSeq'
                    dx = f'CDD:{cdd_id}' if cdd_id else ''
                    sid = f"ProteinSite:{acc}:{st}:{loc}"
                    if sid not in ls_:
                        ls_[sid] = {'siteType': st, 'name': note if note else st,
                                    'source': src, 'dbXref': dx, 'location': loc}
                    lse.append({'start': pid, 'end': sid, 'location': loc})
            except Exception:
                pass
        if has_feat:
            ls['records_with_features'] += 1

    with data_lock:
        for did, info in ld.items():
            if did not in shared_data['domain_nodes']:
                shared_data['domain_nodes'][did] = info
        shared_data['domain_edges'].extend(lde)
        for sid, info in ls_.items():
            if sid not in shared_data['site_nodes']:
                shared_data['site_nodes'][sid] = info
        shared_data['site_edges'].extend(lse)
        for rid, info in lr.items():
            if rid not in shared_data['region_nodes']:
                shared_data['region_nodes'][rid] = info
        shared_data['region_edges'].extend(lre)
    with stats_lock:
        for k, v in ls.items():
            shared_stats[k] = shared_stats.get(k, 0) + v
    return batch_idx, True, None, []


def main():
    print("=== RefSeq KG v1.3: GenPept Fetch + Parse (Parallel) ===", flush=True)
    print(f"  Workers: {MAX_WORKERS}, Batch size: {BATCH_SIZE}", flush=True)
    download_cddid()
    cddid = load_cddid()
    print(f"  cddid.tbl: {len(cddid)} entries", flush=True)
    accessions = read_protein_accessions()
    print(f"  Proteins: {len(accessions):,}", flush=True)
    total_batches = (len(accessions) + BATCH_SIZE - 1) // BATCH_SIZE
    print(f"  Batches: {total_batches:,}", flush=True)

    checkpoint = {'completed_batches': 0, 'failed_accessions': []}
    if os.path.exists(CHECKPOINT_FILE):
        with open(CHECKPOINT_FILE) as f:
            checkpoint = json.load(f)
        print(f"  Resuming from batch {checkpoint['completed_batches']}", flush=True)

    shared_data = {
        'domain_nodes': {}, 'domain_edges': [],
        'site_nodes': {}, 'site_edges': [],
        'region_nodes': {}, 'region_edges': []
    }
    shared_stats = {'total_records': 0, 'records_with_features': 0,
                    'cdd_regions': 0, 'cdd_sites': 0, 'refseq_regions': 0, 'refseq_sites': 0,
                    'skipped_uniprot': 0, 'not_found': 0}

    if checkpoint['completed_batches'] > 0:
        print("  Loading cached data...", flush=True)
        for name in ['domain_nodes', 'site_nodes', 'region_nodes', 'domain_edges', 'site_edges', 'region_edges']:
            cf = os.path.join(OUTPUT_DIR, f'{name}_cache.json')
            if os.path.exists(cf):
                with open(cf) as f:
                    shared_data[name] = json.load(f)
        if 'stats' in checkpoint:
            shared_stats = checkpoint['stats']
        print(f"  Loaded: {len(shared_data['domain_nodes']):,} domains, "
              f"{len(shared_data['site_nodes']):,} sites, "
              f"{len(shared_data['region_nodes']):,} regions", flush=True)

    start_batch = checkpoint['completed_batches']
    completed = start_batch
    failed_accs = checkpoint.get('failed_accessions', [])
    t0 = time.time()

    batches = []
    for bi in range(start_batch, total_batches):
        s = bi * BATCH_SIZE
        e = min(s + BATCH_SIZE, len(accessions))
        batches.append((bi, accessions[s:e]))

    print(f"  Processing {len(batches)} batches...", flush=True)

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = {}
        for bi, ba in batches:
            fut = executor.submit(process_batch, bi, ba, cddid, shared_data, shared_stats)
            futures[fut] = bi

        for fut in as_completed(futures):
            bi = futures[fut]
            try:
                idx, ok, err, nf = fut.result()
                if not ok:
                    failed_accs.extend(nf)
            except Exception as e:
                s = bi * BATCH_SIZE
                e2 = min(s + BATCH_SIZE, len(accessions))
                failed_accs.extend(accessions[s:e2])

            completed += 1
            if completed % 100 == 0 or completed == total_batches:
                elapsed = time.time() - t0
                rate = (completed - start_batch) / elapsed if elapsed > 0 else 0
                remaining = (total_batches - completed) / rate if rate > 0 else 0
                print(f"  [{completed}/{total_batches}] "
                      f"rec={shared_stats['total_records']:,} "
                      f"dom={shared_stats['cdd_regions']:,} "
                      f"site={shared_stats['cdd_sites']:,} "
                      f"rreg={shared_stats['refseq_regions']:,} "
                      f"rsite={shared_stats['refseq_sites']:,} "
                      f"skip={shared_stats['skipped_uniprot']:,} "
                      f"nf={shared_stats['not_found']:,} "
                      f"({rate:.1f}/s, ~{remaining/60:.0f}min)", flush=True)
                checkpoint['completed_batches'] = completed
                checkpoint['failed_accessions'] = failed_accs
                checkpoint['stats'] = shared_stats
                with open(CHECKPOINT_FILE, 'w') as f:
                    json.dump(checkpoint, f, indent=2)
                for name in ['domain_nodes', 'site_nodes', 'region_nodes', 'domain_edges', 'site_edges', 'region_edges']:
                    with open(os.path.join(OUTPUT_DIR, f'{name}_cache.json'), 'w') as f:
                        json.dump(shared_data[name], f)

    # Write CSVs
    print("\n=== Writing CSVs ===", flush=True)
    with open(os.path.join(OUTPUT_DIR, 'nodes_Domain.csv'), 'w', newline='') as f:
        w = csv.writer(f)
        w.writerow(['id:ID', 'name', 'sourceDb', 'category', ':LABEL'])
        for did, info in sorted(shared_data['domain_nodes'].items()):
            w.writerow([did, info['name'], info['sourceDb'], 'biolink:ProteinDomain', 'Domain'])
    print(f"  nodes_Domain.csv: {len(shared_data['domain_nodes']):,}", flush=True)

    with open(os.path.join(OUTPUT_DIR, 'edges_HAS_DOMAIN.csv'), 'w', newline='') as f:
        w = csv.writer(f)
        w.writerow([':START_ID', ':END_ID', ':TYPE', 'begin:int', 'end:int'])
        for e in shared_data['domain_edges']:
            w.writerow([e['start'], e['end'], 'HAS_DOMAIN', e['begin'], e['end']])
    print(f"  edges_HAS_DOMAIN.csv: {len(shared_data['domain_edges']):,}", flush=True)

    with open(os.path.join(OUTPUT_DIR, 'nodes_ProteinSite.csv'), 'w', newline='') as f:
        w = csv.writer(f)
        w.writerow(['id:ID', 'siteType', 'name', 'source', 'dbXref', 'location', 'category', ':LABEL'])
        for sid, info in sorted(shared_data['site_nodes'].items()):
            w.writerow([sid, info['siteType'], info['name'], info['source'], info['dbXref'], info['location'], 'biolink:ProteinSite', 'ProteinSite'])
    print(f"  nodes_ProteinSite.csv: {len(shared_data['site_nodes']):,}", flush=True)

    with open(os.path.join(OUTPUT_DIR, 'edges_HAS_SITE.csv'), 'w', newline='') as f:
        w = csv.writer(f)
        w.writerow([':START_ID', ':END_ID', ':TYPE', 'location'])
        for e in shared_data['site_edges']:
            w.writerow([e['start'], e['end'], 'HAS_SITE', e['location']])
    print(f"  edges_HAS_SITE.csv: {len(shared_data['site_edges']):,}", flush=True)

    with open(os.path.join(OUTPUT_DIR, 'nodes_ProteinRegion.csv'), 'w', newline='') as f:
        w = csv.writer(f)
        w.writerow(['id:ID', 'name', 'source', 'category', ':LABEL'])
        for rid, info in sorted(shared_data['region_nodes'].items()):
            w.writerow([rid, info['name'], info['source'], 'biolink:ProteinRegion', 'ProteinRegion'])
    print(f"  nodes_ProteinRegion.csv: {len(shared_data['region_nodes']):,}", flush=True)

    with open(os.path.join(OUTPUT_DIR, 'edges_HAS_REGION.csv'), 'w', newline='') as f:
        w = csv.writer(f)
        w.writerow([':START_ID', ':END_ID', ':TYPE', 'begin:int', 'end:int'])
        for e in shared_data['region_edges']:
            w.writerow([e['start'], e['end'], 'HAS_REGION', e['begin'], e['end']])
    print(f"  edges_HAS_REGION.csv: {len(shared_data['region_edges']):,}", flush=True)

    print(f"\n=== Final Stats ===", flush=True)
    for k, v in sorted(shared_stats.items()):
        print(f"  {k}: {v:,}", flush=True)
    print(f"  failed_accessions: {len(failed_accs):,}", flush=True)

    checkpoint['completed_batches'] = completed
    checkpoint['failed_accessions'] = failed_accs
    checkpoint['stats'] = shared_stats
    with open(CHECKPOINT_FILE, 'w') as f:
        json.dump(checkpoint, f, indent=2)
    print("\nDone!", flush=True)


if __name__ == '__main__':
    main()
