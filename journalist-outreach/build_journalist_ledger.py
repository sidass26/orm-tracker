#!/usr/bin/env python3
"""
Build journalist-outreach/index.html for the orm-tracker GitHub Pages site.

Reads ~/headout-pr-outreach/ledger.json and renders a dark, data-driven
dashboard (matching orm-tracker's style) of journalist outreach requests:
status, source, reporter, category, deadline, score, tier, question.

Usage:
  python3 build_journalist_ledger.py [--repo ~/vibecoding/orm-tracker]
                                     [--ledger ~/headout-pr-outreach/ledger.json]
                                     [--limit N]   # cap entries in the page (0 = all)
"""
import json, os, re, sys, argparse
from datetime import datetime, date

def clean(s, n=300):
    s = (s or '').strip()
    s = re.sub(r'\s+', ' ', s)
    return s if len(s) <= n else s[:n-1] + '…'

def last_status(e):
    tl = e.get('timeline') or []
    return tl[-1]['status'] if tl else e.get('status', '')

def first_or_last(e, key):
    tl = e.get(key) or []
    return tl[-1] if tl else None

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--repo', default=os.path.expanduser('~/vibecoding/orm-tracker'))
    ap.add_argument('--ledger', default=os.path.expanduser('~/headout-pr-outreach/ledger.json'))
    ap.add_argument('--limit', type=int, default=0)
    args = ap.parse_args()

    d = json.load(open(args.ledger))
    entries = d['entries']
    rows = []
    for k, e in entries.items():
        tl = e.get('timeline') or []
        st = last_status(e)
        rows.append({
            'source': (e.get('source') or '—'),
            'reporter': (e.get('reporter') or '—'),
            'category': (e.get('haro_category') or e.get('section') or '—'),
            'deadline': (e.get('deadline') or '—'),
            'score': e.get('score'),
            'tier': e.get('tier'),
            'status': st,
            'question': clean(e.get('question'), 260),
            'draft_subject': clean(e.get('draft_subject'), 120),
            'update': (str(tl[-1].get('at'))[:16].replace('T',' ') if tl else ''),
            'outlet_url': (e.get('outlet_url') or '')[:60],
            'link': (e.get('link') or '')[:80],
        })
    # sort: newest update first, then status order
    order = {'SENT':0,'DRAFTED':1,'SCORED':2,'DROPPED':3,'REJECTED':4,'REPLIED':5}
    rows.sort(key=lambda r: (order.get(r['status'],9), r['update']), reverse=False)
    rows.sort(key=lambda r: r['update'], reverse=True)
    if args.limit:
        rows = rows[:args.limit]

    TOTAL = len(entries)
    def cnt(s): return sum(1 for r in rows if r['status']==s)
    from collections import Counter
    c = Counter(r['status'] for r in rows)
    stats = [
        ('Total requests', TOTAL, ''),
        ('SENT', c.get('SENT',0), '▲ pitches mailed'),
        ('DRAFTED', c.get('DRAFTED',0), '▲ awaiting approval'),
        ('SCORED', c.get('SCORED',0), '▲ not yet pitched'),
        ('DROPPED', c.get('DROPPED',0), '▼ off-topic / no fit'),
    ]

    data_json = json.dumps(rows)
    stats_json = json.dumps(stats)

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Journalist Outreach · tracker</title>
<style>
  :root{{--bg:#0f1115;--card:#171b22;--card2:#1d222c;--fg:#e8ecf1;--muted:#8b93a3;--border:#262c38;
    --accent:#4f8cff;--green:#3ecf8e;--red:#ff5d5d;--amber:#f5a742;--purple:#a78bfa;--cyan:#35d0dc;}}
  *{{box-sizing:border-box;margin:0;padding:0}}
  body{{background:var(--bg);color:var(--fg);font:14px/1.5 -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Helvetica,Arial,sans-serif;padding:24px 20px 48px}}
  .wrap{{max-width:1120px;margin:0 auto}}
  header{{display:flex;align-items:center;gap:12px;flex-wrap:wrap;padding-bottom:6px}}
  .logo{{width:38px;height:38px;border-radius:10px;display:grid;place-items:center;background:linear-gradient(135deg,var(--accent),var(--purple));font-weight:800;color:#fff;font-size:18px}}
  h1{{font-size:20px;font-weight:800;letter-spacing:-.01em}}
  .sub{{color:var(--muted);font-size:12.5px}}
  .pill{{font:inherit;padding:4px 9px;border-radius:999px;font-size:11px;font-weight:600;display:inline-flex;align-items:center;gap:5px}}
  .pill::before{{content:"";width:7px;height:7px;border-radius:50%;background:currentColor}}
  .pill.live{{color:var(--green);background:rgba(62,207,142,.14)}}
  .pill.wk{{color:var(--amber);background:rgba(245,167,66,.14)}}
  .cardsum{{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:12px;margin-top:16px}}
  .stat{{background:var(--card2);border:1px solid var(--border);border-radius:12px;padding:12px 14px}}
  .stat .k{{font-size:11px;color:var(--muted);text-transform:uppercase;letter-spacing:.04em}}
  .stat .v{{font-size:23px;font-weight:800;line-height:1.15}}
  .stat .chg{{font-size:11px;color:var(--muted)}}
  .controls{{display:flex;gap:8px;flex-wrap:wrap;align-items:center;margin:16px 0 4px}}
  .fbtn{{font:inherit;font-size:12px;padding:5px 12px;border-radius:999px;border:1px solid var(--border);background:var(--card);color:var(--muted);cursor:pointer}}
  .fbtn.on{{color:#fff;background:var(--accent);border-color:var(--accent)}}
  .card{{background:var(--card);border:1px solid var(--border);border-radius:14px;overflow:hidden;margin-top:10px}}
  .row{{display:flex;flex-wrap:wrap;gap:8px 14px;align-items:flex-start;padding:11px 14px;border-bottom:1px solid rgba(38,44,56,.5);background:var(--card2)}}
  .row:last-child{{border-bottom:none}}
  .st{{font-size:10.5px;font-weight:700;padding:3px 8px;border-radius:999px;min-width:58px;text-align:center;flex:0 0 auto}}
  .st.SENT{{color:var(--green);background:rgba(62,207,142,.15)}}
  .st.DRAFTED{{color:var(--amber);background:rgba(245,167,66,.15)}}
  .st.SCORED{{color:var(--accent);background:rgba(79,140,255,.15)}}
  .st.DROPPED,.st.REJECTED{{color:var(--red);background:rgba(255,93,93,.12)}}
  .st.REPLIED{{color:var(--purple);background:rgba(167,139,250,.15)}}
  .core{{flex:1;min-width:240px}}
  .core .src{{font-weight:700;font-size:13px}}
  .core .q{{color:var(--muted);font-size:12.5px;margin-top:2px}}
  .core .meta{{display:flex;gap:10px;flex-wrap:wrap;color:var(--muted);font-size:11.5px;margin-top:4px}}
  .sc{{font-family:ui-monospace,Menlo,Consolas,monospace;font-size:11px;color:var(--muted);background:var(--card);border:1px solid var(--border);padding:2px 7px;border-radius:7px;flex:0 0 auto}}
  footer{{color:var(--muted);font-size:11.5px;margin-top:22px;line-height:1.7}}
  .empty{{color:var(--muted);padding:24px;text-align:center}}
</style>
</head>
<body>
<div class="wrap">
  <header>
    <div class="logo">J</div>
    <div>
      <h1>Journalist Outreach</h1>
      <div class="sub">HARO + Connectively requests · scored &amp; pitched by the Headout PR pipeline</div>
    </div>
    <span class="pill live">Live</span>
    <span class="pill wk">Weekly refresh</span>
  </header>
  <div class="cardsum" id="sum"></div>
  <div class="controls" id="filters"></div>
  <div class="card" id="list"></div>
  <footer>
    Journalist Outreach tracker · generated {date.today().isoformat()} from the Headout PR outreach ledger.
    Requests fetched from Connectively + HARO digests, scored 0-30, and (never auto-sent) human-approved.
  </footer>
</div>
<script>
/* ---- DATA: regenerated by build_journalist_ledger.py ---- */
var LEDGER = {data_json};
/* ---- render ---- */
(function(){{
  var order={{'SENT':0,'DRAFTED':1,'SCORED':2,'DROPPED':3,'REJECTED':4,'REPLIED':5}};
  var all=LEDGER.slice().sort(function(a,b){{return order[a.status]-order[b.status] || b.update.localeCompare(a.update);}});
  var statuses=['ALL','SENT','DRAFTED','SCORED','DROPPED'];
  var f='ALL';
  var sumEl=document.getElementById('sum');
  var stats={stats_json};
  sumEl.innerHTML=stats.map(function(s){{
    return '<div class="stat"><div class="k">'+s[0]+'</div><div class="v">'+s[1]+'</div><div class="chg">'+s[2]+'</div></div>';
  }}).join('');
  var filt=document.getElementById('filters');
  filt.innerHTML=statuses.map(function(s){{
    var n = s==='ALL' ? all.length : all.filter(r=>r.status===s).length;
    return '<button class="fbtn'+(f===s?' on':'')+'" data-f="'+s+'">'+s+' ('+n+')</button>';
  }}).join('');
  function esc(s){{return (s||'').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');}}
  function render(){{
    var rows = f==='ALL' ? all : all.filter(r=>r.status===f);
    var el=document.getElementById('list');
    if(!rows.length){{el.innerHTML='<div class="empty">No requests in this state.</div>';return;}}
    el.innerHTML=rows.map(function(r){{
      var meta='';
      if(r.reporter&&r.reporter!=='—') meta+='👤 '+esc(r.reporter)+' · ';
      meta+=esc(r.category)+' · due '+esc(r.deadline);
      if(r.update) meta+=' · '+esc(r.update);
      var m2='';
      if(r.draft_subject) m2+='Pitch: '+esc(r.draft_subject);
      return '<div class="row"><span class="st '+esc(r.status)+'">'+esc(r.status)+'</span>'+
        '<div class="core"><div class="src">'+esc(r.source)+'</div>'+
        '<div class="q">'+esc(r.question)+'</div>'+
        '<div class="meta"><span>'+meta+'</span>'+ (m2?'<span>'+m2+'</span>':'') +'</div></div>'+
        (r.score!=null?'<span class="sc">'+r.score+'/30 '+esc(r.tier)+'</span>':'')+
      '</div>';
    }}).join('');
  }}
  filt.addEventListener('click',function(e){{
    var b=e.target.closest('.fbtn'); if(!b) return;
    f=b.getAttribute('data-f');
    filt.querySelectorAll('.fbtn').forEach(x=>x.classList.toggle('on',x===b));
    render();
  }});
  render();
}})();
</script>
</body>
</html>
"""
    out_dir = os.path.join(args.repo, 'journalist-outreach')
    os.makedirs(out_dir, exist_ok=True)
    out = os.path.join(out_dir, 'index.html')
    with open(out, 'w') as f:
        f.write(html)
    print(f"Wrote {out} ({os.path.getsize(out)//1024} KB, {len(rows)} rows)")

if __name__ == '__main__':
    main()
