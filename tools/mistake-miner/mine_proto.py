"""Prototype miner: extract candidate mistake-events + their preceding state from a transcript."""
import json, re, sys, collections

# Signals that a mistake was surfaced. Deliberately broad at this stage: recall over
# precision, because a model classifies afterwards and a missed event is unrecoverable.
SIGNALS = [
 ('self_correction',  r'\b(CORRECT(ED|ION)|I was wrong|I invented|struck from|that claim was (false|wrong))\b'),
 ('nonexistent_ref',  r'\b(does not exist|DOES NOT EXIST|no such (function|file|symbol))\b'),
 ('stale_fact',       r'\b(stale|out of date|no longer true|was already (fixed|landed|done))\b'),
 ('undercount',       r'\b(undercount|under-?enumerat|missed \d+|only counted|actually \d+)\b'),
 ('adversary_verdict',r'Verdict:\s*(DRIFT|ISLANDS|BAND-AID|MIXED|GAPS|HOLLOW|SILENT|UNSAFE|EXPOSED|STRANDED|REFUTED|UNDERSPECIFIED)'),
 ('refuted_claim',    r'\bREFUTED\b|\brefuted\b'),
 ('vacuous_test',     r'\bvacuous\b|\bcannot fail\b|\bhardcoded (True|pass)\b'),
 ('wrong_threshold',  r'\bthreshold\b.{0,60}\b(arbitrary|unnecessary|wrong|barely)\b'),
]

def load(path):
    recs=[]
    for line in open(path, errors='replace'):
        try: recs.append(json.loads(line))
        except: pass
    return recs

def text_of(rec):
    msg = rec.get('message') or {}
    c = msg.get('content')
    if isinstance(c, str): return c
    if isinstance(c, list):
        return ' '.join(b.get('text','') for b in c if isinstance(b,dict) and b.get('type')=='text')
    return ''

def tools_of(rec):
    msg = rec.get('message') or {}
    c = msg.get('content')
    out=[]
    if isinstance(c,list):
        for b in c:
            if isinstance(b,dict) and b.get('type')=='tool_use':
                inp=b.get('input') or {}
                target = inp.get('file_path') or inp.get('path') or (inp.get('command','')[:60] if isinstance(inp.get('command'),str) else '')
                out.append((b.get('name','?'), target))
    return out

def main(path):
    recs = load(path)
    events=[]
    recent_tools=collections.deque(maxlen=6)   # the STATE just before the mistake surfaced
    for i,r in enumerate(recs):
        for t in tools_of(r): recent_tools.append(t)
        if r.get('type')!='assistant': continue
        txt = text_of(r)
        if not txt.strip(): continue
        hits=[name for name,pat in SIGNALS if re.search(pat, txt, re.I)]
        if not hits: continue
        # the sentence carrying the signal = the label evidence
        sents=[s.strip() for s in re.split(r'(?<=[.!?])\s+', txt) if any(re.search(p,s,re.I) for _,p in SIGNALS)]
        events.append({
            'record_index': i,
            'signals': hits,
            'evidence': (sents[0][:220] if sents else txt[:220]),
            'preceding_tools': list(recent_tools),
        })
    print(f'transcript records: {len(recs)}')
    print(f'candidate mistake-events extracted: {len(events)}\n')
    tally=collections.Counter(s for e in events for s in e['signals'])
    print('signal tally:')
    for k,v in tally.most_common(): print(f'   {k:20s} {v}')
    print('\nsample events (evidence + the state just before):')
    for e in events[:6]:
        print(f'\n  [{e["record_index"]}] signals={e["signals"]}')
        print(f'      evidence: {e["evidence"][:150]}')
        print(f'      preceding: {[t[0] for t in e["preceding_tools"]]}')
    json.dump(events, open('mined_events.json','w'), indent=1)
    print(f'\nwrote mined_events.json ({len(events)} events)')

main(sys.argv[1])
