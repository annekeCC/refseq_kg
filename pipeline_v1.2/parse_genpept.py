#!/usr/bin/env python3
"""
Parse all GenPept batch files and generate CSVs.
Also fetches any missing batches first.
Sequential — no threading issues.
"""
import os, sys, time, json, csv, io, urllib.request, urllib.parse

API_KEY = os.environ.get('NCBI_API_KEY', '67a42d6e33ded3f5440281823ee758663c08')
EUTILS_URL = 'https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi'
BATCH_SIZE = 500
RAW_DIR = '/workspace/genpept_raw'
OUTPUT_DIR = '/workspace/genpept_output'
PROTEIN_CSV = '/mnt/results/refseq_kg/import/nodes_Protein.csv'
CDDID_LOCAL = '/workspace/cddid.tbl'

os.makedirs(OUTPUT_DIR, exist_ok=True)


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


def fetch_missing_batch(batch_idx, batch_accs):
    """Fetch a single missing batch."""
    post_data = urllib.parse.urlencode({
        'db': 'protein', 'id': ','.join(batch_accs),
        'rettype': 'gp', 'retmode': 'text', 'api_key': API_KEY
    }).encode()
    for attempt in range(3):
        try:
            req = urllib.request.Request(EUTILS_URL, data=post_data)
            resp = urllib.request.urlopen(req, timeout=120)
            raw_text = resp.read().decode('utf-8', errors='replace')
            raw_file = os.path.join(RAW_DIR, f'batch_{batch_idx:05d}.txt')
            with open(raw_file, 'w') as f:
                f.write(raw_text)
            return True
        except Exception as e:
            print(f"  Retry {attempt+1} for batch {batch_idx}: {e}", flush=True)
            time.sleep(5 * (attempt + 1))
    return False


def main():
    print("=== RefSeq KG v1.2: Parse GenPept Batches ===", flush=True)

    cddid = load_cddid()
    print(f"  cddid.tbl: {len(cddid)} entries", flush=True)

    accessions = read_protein_accessions()
    total_batches = (len(accessions) + BATCH_SIZE - 1) // BATCH_SIZE
    print(f"  Proteins: {len(accessions):,}, Batches: {total_batches}", flush=True)

    # Step 1: Find and fetch missing batches
    existing = set(f for f in os.listdir(RAW_DIR) if f.startswith('batch_'))
    missing = []
    for i in range(total_batches):
        fname = f'batch_{i:05d}.txt'
        if fname not in existing:
            s = i * BATCH_SIZE
            e = min(s + BATCH_SIZE, len(accessions))
            missing.append((i, accessions[s:e]))

    if missing:
        print(f"  Fetching {len(missing)} missing batches...", flush=True)
        for idx, (batch_idx, batch_accs) in enumerate(missing):
            ok = fetch_missing_batch(batch_idx, batch_accs)
            if ok:
                print(f"    [{idx+1}/{len(missing)}] batch {batch_idx} fetched", flush=True)
            else:
                print(f"    [{idx+1}/{len(missing)}] batch {batch_idx} FAILED", flush=True)
            time.sleep(0.2)  # rate limit

    # Step 2: Parse all batch files
    print(f"\n  Parsing batch files...", flush=True)

    domain_nodes = {}
    domain_edges = []
    site_nodes = {}
    site_edges = []
    region_nodes = {}
    region_edges = []
    stats = {'total_records': 0, 'records_with_features': 0,
             'cdd_regions': 0, 'cdd_sites': 0, 'refseq_regions': 0, 'refseq_sites': 0,
             'skipped_uniprot': 0, 'not_found': 0, 'parse_errors': 0}

    # Get set of valid protein IDs for edge filtering
    valid_protein_ids = set()
    with open(PROTEIN_CSV) as f:
        reader = csv.DictReader(f)
        for row in reader:
            valid_protein_ids.add(row['id:ID'])

    for batch_idx in range(total_batches):
        raw_file = os.path.join(RAW_DIR, f'batch_{batch_idx:05d}.txt')
        if not os.path.exists(raw_file):
            stats['not_found'] += BATCH_SIZE
            continue

        with open(raw_file) as f:
            raw_text = f.read()

        try:
            records = parse_genpept(raw_text)
        except Exception as e:
            stats['parse_errors'] += 1
            continue

        for rec in records:
            acc = rec['accession']
            pid = f'RefSeq:{acc}'
            if pid not in valid_protein_ids:
                continue
            stats['total_records'] += 1
            has_feat = False

            for ft, loc, quals in rec['features']:
                if ft not in ('Region', 'Site'):
                    continue
                try:
                    if 'propagated from UniProtKB' in quals.get('note', ''):
                        stats['skipped_uniprot'] += 1
                        continue
                    cdd_id = None
                    dbxref = quals.get('db_xref', '')
                    if 'CDD:' in dbxref:
                        cdd_id = dbxref.split('CDD:')[1].strip('"').strip()
                    begin, end = extract_location_bounds(loc)

                    if ft == 'Region' and cdd_id:
                        stats['cdd_regions'] += 1
                        has_feat = True
                        did = f'CDD:{cdd_id}'
                        if did not in domain_nodes:
                            rn = quals.get('region_name', '')
                            ci = cddid.get(cdd_id, {})
                            domain_nodes[did] = {'name': ci.get('short_name', rn), 'sourceDb': ci.get('sourceDb', 'CDD')}
                        if begin is not None:
                            domain_edges.append({'start': pid, 'end_id': did, 'begin': begin, 'end_pos': end})
                    elif ft == 'Region' and not cdd_id:
                        stats['refseq_regions'] += 1
                        has_feat = True
                        rn = quals.get('region_name', 'unnamed')
                        rid = f"ProteinRegion:{acc}:{rn}:{begin}:{end}"
                        if rid not in region_nodes:
                            region_nodes[rid] = {'name': rn, 'source': 'RefSeq'}
                        if begin is not None:
                            region_edges.append({'start': pid, 'end_id': rid, 'begin': begin, 'end_pos': end})
                    elif ft == 'Site':
                        st = quals.get('site_type', 'other')
                        note = ' '.join(quals.get('note', '').split())
                        if cdd_id:
                            stats['cdd_sites'] += 1
                        else:
                            stats['refseq_sites'] += 1
                        has_feat = True
                        src = 'CDD' if cdd_id else 'RefSeq'
                        dx = f'CDD:{cdd_id}' if cdd_id else ''
                        sid = f"ProteinSite:{acc}:{st}:{loc}"
                        if sid not in site_nodes:
                            site_nodes[sid] = {'siteType': st, 'name': note if note else st,
                                               'source': src, 'dbXref': dx, 'location': loc}
                        site_edges.append({'start': pid, 'end': sid, 'location': loc})
                except Exception:
                    pass

            if has_feat:
                stats['records_with_features'] += 1

        if (batch_idx + 1) % 500 == 0 or batch_idx + 1 == total_batches:
            print(f"  [{batch_idx+1}/{total_batches}] "
                  f"rec={stats['total_records']:,} dom={stats['cdd_regions']:,} "
                  f"site={stats['cdd_sites']:,} rreg={stats['refseq_regions']:,} "
                  f"rsite={stats['refseq_sites']:,} skip={stats['skipped_uniprot']:,}", flush=True)

    # Step 3: Write CSVs
    print(f"\n=== Writing CSVs ===", flush=True)

    with open(os.path.join(OUTPUT_DIR, 'nodes_Domain.csv'), 'w', newline='') as f:
        w = csv.writer(f)
        w.writerow(['id:ID', 'name', 'sourceDb', 'category', ':LABEL'])
        for did, info in sorted(domain_nodes.items()):
            w.writerow([did, info['name'], info['sourceDb'], 'biolink:ProteinDomain', 'Domain'])
    print(f"  nodes_Domain.csv: {len(domain_nodes):,} domains", flush=True)

    with open(os.path.join(OUTPUT_DIR, 'edges_HAS_DOMAIN.csv'), 'w', newline='') as f:
        w = csv.writer(f)
        w.writerow([':START_ID', ':END_ID', ':TYPE', 'begin:int', 'end:int'])
        for e in domain_edges:
            w.writerow([e['start'], e['end_id'], 'HAS_DOMAIN', e['begin'], e['end_pos']])
    print(f"  edges_HAS_DOMAIN.csv: {len(domain_edges):,} edges", flush=True)

    with open(os.path.join(OUTPUT_DIR, 'nodes_ProteinSite.csv'), 'w', newline='') as f:
        w = csv.writer(f)
        w.writerow(['id:ID', 'siteType', 'name', 'source', 'dbXref', 'location', 'category', ':LABEL'])
        for sid, info in sorted(site_nodes.items()):
            w.writerow([sid, info['siteType'], info['name'], info['source'], info['dbXref'], info['location'], 'biolink:ProteinSite', 'ProteinSite'])
    print(f"  nodes_ProteinSite.csv: {len(site_nodes):,} sites", flush=True)

    with open(os.path.join(OUTPUT_DIR, 'edges_HAS_SITE.csv'), 'w', newline='') as f:
        w = csv.writer(f)
        w.writerow([':START_ID', ':END_ID', ':TYPE', 'location'])
        for e in site_edges:
            w.writerow([e['start'], e['end'], 'HAS_SITE', e['location']])
    print(f"  edges_HAS_SITE.csv: {len(site_edges):,} edges", flush=True)

    with open(os.path.join(OUTPUT_DIR, 'nodes_ProteinRegion.csv'), 'w', newline='') as f:
        w = csv.writer(f)
        w.writerow(['id:ID', 'name', 'source', 'category', ':LABEL'])
        for rid, info in sorted(region_nodes.items()):
            w.writerow([rid, info['name'], info['source'], 'biolink:ProteinRegion', 'ProteinRegion'])
    print(f"  nodes_ProteinRegion.csv: {len(region_nodes):,} regions", flush=True)

    with open(os.path.join(OUTPUT_DIR, 'edges_HAS_REGION.csv'), 'w', newline='') as f:
        w = csv.writer(f)
        w.writerow([':START_ID', ':END_ID', ':TYPE', 'begin:int', 'end:int'])
        for e in region_edges:
            w.writerow([e['start'], e['end_id'], 'HAS_REGION', e['begin'], e['end_pos']])
    print(f"  edges_HAS_REGION.csv: {len(region_edges):,} edges", flush=True)

    print(f"\n=== Final Stats ===", flush=True)
    for k, v in sorted(stats.items()):
        print(f"  {k}: {v:,}", flush=True)
    print("\nDone!", flush=True)


if __name__ == '__main__':
    main()
