#!/usr/bin/env python3
import json, os, urllib.request
from datetime import date, datetime, timedelta, timezone
from html import escape
from pathlib import Path

USER=os.getenv("GITHUB_USERNAME","Daniel059")
TOKEN=os.getenv("GITHUB_TOKEN","")
OUT=Path("dist")
G="#39FF14"; BG="#0b1110"; PANEL="#171d23"; MUTED="#8b9bb0"; TEXT="#e6edf3"; GRID="#29323a"
QUERY='''query($login: String!, $from: DateTime!, $to: DateTime!) {
 user(login:$login) { contributionsCollection(from:$from,to:$to) {
 contributionCalendar { totalContributions weeks { contributionDays { contributionCount date } } }
 } }
}'''

def api_calendar(start,end):
    body=json.dumps({"query":QUERY,"variables":{"login":USER,
      "from":datetime.combine(start,datetime.min.time(),timezone.utc).isoformat(),
      "to":datetime.combine(end+timedelta(days=1),datetime.min.time(),timezone.utc).isoformat()}}).encode()
    req=urllib.request.Request("https://api.github.com/graphql",data=body,method="POST",
      headers={"Authorization":"Bearer "+TOKEN,"Content-Type":"application/json","User-Agent":"Daniel059-dashboard"})
    with urllib.request.urlopen(req,timeout=30) as r: obj=json.load(r)
    if obj.get("errors"): raise RuntimeError(json.dumps(obj["errors"]))
    if not obj.get("data",{}).get("user"): raise RuntimeError("GitHub user unavailable")
    return obj["data"]["user"]["contributionsCollection"]["contributionCalendar"]

def repos():
    req=urllib.request.Request("https://api.github.com/users/"+USER,headers={"User-Agent":"Daniel059-dashboard"})
    with urllib.request.urlopen(req,timeout=30) as r: return int(json.load(r)["public_repos"])

def esc(x): return escape(str(x),quote=True)

def make_svg(d,period=30,full=True):
    W,H=1160,(780 if full else 390); days=d["days"][-period:]; vals=[x["count"] for x in days]; mx=max([1]+vals)
    s=[f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="100%" role="img" aria-labelledby="t desc">',
       '<title id="t">GitHub activity dashboard</title><desc id="desc">Contribution metrics, activity chart, and contribution calendar.</desc>',
       f'<rect x="1" y="1" width="{W-2}" height="{H-2}" rx="22" fill="{BG}" stroke="{GRID}" stroke-width="1.5"/>',
       f'<text x="36" y="58" font-family="Arial,sans-serif" font-size="28" font-weight="700" fill="{TEXT}">GitHub activity</text>',
       f'<text x="36" y="86" font-family="Arial,sans-serif" font-size="16" fill="{MUTED}">@{esc(d["username"])} · updated {esc(d["updated"])}</text>',
       f'<circle cx="{W-44}" cy="52" r="7" fill="{G}"/>']
    cards=[("CONTRIBUTIONS",d["total30"],"last 30 days"),("ACTIVE DAYS",f'{d["active30"]}/30',"days with activity"),
           ("CURRENT STREAK",d["streak"],"days in a row"),("PUBLIC REPOS",d["public_repos"],f'{d["total_year"]} contributions / year')]
    cw=(W-126)//4
    for i,(label,val,sub) in enumerate(cards):
        x=36+i*(cw+18)
        s += [f'<rect x="{x}" y="108" width="{cw}" height="108" rx="17" fill="{PANEL}" stroke="{GRID}"/>',
              f'<rect x="{x}" y="124" width="4" height="76" rx="2" fill="{G}"/>',
              f'<text x="{x+24}" y="142" font-family="Arial,sans-serif" font-size="14" letter-spacing="1" fill="{MUTED}">{esc(label)}</text>',
              f'<text x="{x+24}" y="182" font-family="Arial,sans-serif" font-size="40" font-weight="700" fill="{G}">{esc(val)}</text>',
              f'<text x="{x+24}" y="205" font-family="Arial,sans-serif" font-size="14" fill="{MUTED}">{esc(sub)}</text>']
    if full:
        s += [f'<text x="36" y="255" font-family="Arial,sans-serif" font-size="19" font-weight="700" fill="{TEXT}">Activity over time</text>',
              f'<text x="{W-36}" y="255" text-anchor="end" font-family="Arial,sans-serif" font-size="14" fill="{MUTED}">last 30 days · line = 7-day average</text>']
        top,bottom=286,442
    else:
        s.append(f'<text x="36" y="255" font-family="Arial,sans-serif" font-size="19" font-weight="700" fill="{TEXT}">Activity over time · last {period} days</text>')
        top,bottom=275,H-56
    left,right=68,W-42; ch=bottom-top; step=(right-left)/max(1,len(days)); pts=[]
    for f in (0,.33,.66,1):
        y=bottom-f*ch
        s += [f'<path d="M{left} {y:.1f}H{right}" stroke="{GRID}" stroke-dasharray="4 6"/>',
              f'<text x="{left-12}" y="{y+5:.1f}" text-anchor="end" font-family="Arial,sans-serif" font-size="12" fill="{MUTED}">{round(mx*f)}</text>']
    for i,d0 in enumerate(days):
        x=left+i*step+step*.18; h=d0["count"]/mx*ch; y=bottom-h
        s.append(f'<rect x="{x:.2f}" y="{y:.2f}" width="{max(2,step*.62):.2f}" height="{max(2,h):.2f}" rx="3" fill="{G}" opacity="{.96 if d0["count"] else .12}"><title>{esc(d0["date"])}: {d0["count"]} contributions</title></rect>')
        avg=sum(vals[max(0,i-6):i+1])/len(vals[max(0,i-6):i+1])
        pts.append((left+i*step+step/2,bottom-avg/mx*ch))
    path=" ".join(f'{"M" if i==0 else "L"}{x:.2f},{y:.2f}' for i,(x,y) in enumerate(pts))
    s.append(f'<path d="{path}" fill="none" stroke="{G}" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"/>')
    if full:
        s += [f'<text x="36" y="488" font-family="Arial,sans-serif" font-size="19" font-weight="700" fill="{TEXT}">Contribution calendar</text>',
              f'<text x="{W-36}" y="488" text-anchor="end" font-family="Arial,sans-serif" font-size="14" fill="{MUTED}">{d["total_year"]} contributions in the last year</text>']
        start=date.fromisoformat(d["days"][0]["date"]); monday=start-timedelta(days=start.weekday()); cell,gap,x0,y0=15,4,76,535
        maxheat=max([1]+[x["count"] for x in d["days"]]); lastmonth=None
        for col in range(54):
            month=monday+timedelta(days=col*7)
            if month.month!=lastmonth:
                s.append(f'<text x="{x0+col*(cell+gap)}" y="523" font-family="Arial,sans-serif" font-size="12" fill="{MUTED}">{month.strftime("%b")}</text>')
                lastmonth=month.month
        for item in d["days"]:
            dt=date.fromisoformat(item["date"]); col=(dt-monday).days//7; row=dt.weekday(); v=item["count"]/maxheat
            fill="#191f25" if not item["count"] else "#0d4b19" if v<.25 else "#118523" if v<.5 else "#20c82b" if v<.75 else G
            s.append(f'<rect x="{x0+col*(cell+gap)}" y="{y0+row*(cell+gap)}" width="{cell}" height="{cell}" rx="4" fill="{fill}"><title>{esc(item["date"])}: {item["count"]} contributions</title></rect>')
        for lab,row in (("Mon",0),("Wed",2),("Fri",4)):
            s.append(f'<text x="64" y="{y0+row*(cell+gap)+12}" text-anchor="end" font-family="Arial,sans-serif" font-size="11" fill="{MUTED}">{lab}</text>')
        s.append(f'<text x="36" y="756" font-family="Arial,sans-serif" font-size="13" fill="{MUTED}">Best day (30d): {max(vals) if vals else 0} · auto-updated daily by GitHub Actions</text>')
        s.append(f'<text x="{W-36}" y="756" text-anchor="end" font-family="Arial,sans-serif" font-size="13" fill="{MUTED}">Less  ▪ ▪ ▪ ▪  More</text>')
    else:
        s.append(f'<text x="36" y="{H-22}" font-family="Arial,sans-serif" font-size="12" fill="{MUTED}">Daily contributions · rolling 7-day average · interactive report has range controls</text>')
    return "\\n".join(s+["</svg>"])

def make_html(d):
    payload=json.dumps(d,separators=(",",":")).replace("</","<\\\\/")
    page=r'''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>GitHub activity dashboard</title><style>
:root{--bg:#0b1110;--panel:#171d23;--text:#e6edf3;--muted:#8b9bb0;--green:#39FF14;--grid:#29323a}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--text);font:16px/1.5 Inter,system-ui,Segoe UI,Arial,sans-serif;padding:clamp(12px,3vw,36px)}main{max-width:1200px;margin:auto}h1{font-size:clamp(1.5rem,4vw,2rem);margin:0}.muted{color:var(--muted)}
.cards{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:14px;margin:24px 0}.card{background:var(--panel);border:1px solid var(--grid);border-radius:16px;padding:18px;border-left:4px solid var(--green);min-width:0}.label{font-size:.78rem;letter-spacing:.08em;color:var(--muted)}.value{font-size:clamp(1.5rem,4vw,2.4rem);font-weight:800;color:var(--green);line-height:1.3;overflow-wrap:anywhere}
.controls{display:flex;gap:8px;flex-wrap:wrap;margin:14px 0}button{border:1px solid var(--grid);background:var(--panel);color:var(--text);border-radius:9px;padding:9px 16px;cursor:pointer}button[aria-pressed=true]{background:var(--green);color:#081008;border-color:var(--green);font-weight:700}.chartbox{border:1px solid var(--grid);border-radius:16px;padding:12px;overflow:hidden}svg{display:block;width:100%;height:auto}.tip{min-height:24px;color:var(--muted);font-size:.9rem}
@media(max-width:760px){.cards{grid-template-columns:repeat(2,minmax(0,1fr));gap:9px}.card{padding:12px}}@media(max-width:380px){.cards{grid-template-columns:1fr}}
</style></head><body><main><h1>GitHub activity</h1><div class="muted" id="subtitle"></div><section class="cards" id="cards"></section>
<h2>Activity over time</h2><div class="controls"><button data-days="30" aria-pressed="true">30 days</button><button data-days="90" aria-pressed="false">90 days</button><button data-days="365" aria-pressed="false">365 days</button></div>
<div class="chartbox" id="chart"></div><div class="tip" id="tip" aria-live="polite">Hover or focus a bar to see its date and contribution count.</div><h2>Contribution calendar</h2><div class="chartbox" id="heatmap"></div>
<p class="muted">Data comes from GitHub's contribution calendar and updates when the daily workflow succeeds.</p></main><script>
const D=__DATA__,G="#39FF14",GRID="#29323a",MUTED="#8b9bb0";
document.getElementById('subtitle').textContent='@'+D.username+' · updated '+D.updated;
document.getElementById('cards').innerHTML=[['CONTRIBUTIONS',D.total30,'last 30 days'],['ACTIVE DAYS',D.active30+'/30','days with activity'],['CURRENT STREAK',D.streak,'days in a row'],['PUBLIC REPOS',D.public_repos,D.total_year+' contributions / year']].map(c=>'<div class="card"><div class="label">'+c[0]+'</div><div class="value">'+c[1]+'</div><div class="muted">'+c[2]+'</div></div>').join('');
function chart(n){let a=D.days.slice(-n),W=1100,H=330,L=48,R=18,T=18,B=44,ph=H-T-B,max=Math.max(1,...a.map(x=>x.count)),step=(W-L-R)/a.length,o=[`<svg viewBox="0 0 ${W} ${H}" role="img" aria-label="Contribution activity chart">`],pts=[];
for(let j=0;j<4;j++){let y=T+ph*j/3;o.push(`<path d="M${L} ${y}H${W-R}" stroke="${GRID}" stroke-dasharray="4 6"/><text x="${L-10}" y="${y+4}" text-anchor="end" font-size="12" fill="${MUTED}">${Math.round(max*(1-j/3))}</text>`)}
a.forEach((d,i)=>{let x=L+i*step+step*.18,h=d.count/max*ph,y=T+ph-h;o.push(`<rect x="${x}" y="${y}" width="${Math.max(1,step*.64)}" height="${Math.max(2,h)}" rx="2" fill="${G}" opacity="${d.count?.9:.12}" tabindex="0" data-date="${d.date}" data-count="${d.count}"><title>${d.date}: ${d.count} contributions</title></rect>`);let v=a.slice(Math.max(0,i-6),i+1),avg=v.reduce((s,x)=>s+x.count,0)/v.length;pts.push([L+i*step+step/2,T+ph-avg/max*ph])});
o.push(`<path d="${pts.map((p,i)=>(i?'L':'M')+p[0]+','+p[1]).join(' ')}" fill="none" stroke="${G}" stroke-width="2.5" stroke-linecap="round"/>`);
o.push(`<text x="${L}" y="${H-12}" fill="${MUTED}" font-size="12">${a[0].date}</text><text x="${W-R}" y="${H-12}" text-anchor="end" fill="${MUTED}" font-size="12">${a[a.length-1].date}</text></svg>`);return o.join('')}
function heatmap(){let a=D.days,cell=13,gap=4,first=new Date(a[0].date+'T00:00:00Z'),off=(first.getUTCDay()+6)%7,cols=Math.ceil((a.length+off)/7),W=40+cols*(cell+gap),H=18+7*(cell+gap),max=Math.max(1,...a.map(x=>x.count)),o=[`<svg viewBox="0 0 ${W} ${H}" role="img" aria-label="Contribution calendar">`];a.forEach((d,i)=>{let dt=new Date(d.date+'T00:00:00Z'),col=Math.floor((i+off)/7),row=(dt.getUTCDay()+6)%7,v=d.count/max,fill=!d.count?'#191f25':v<.25?'#0d4b19':v<.5?'#118523':v<.75?'#20c82b':G;o.push(`<rect x="${40+col*(cell+gap)}" y="${18+row*(cell+gap)}" width="${cell}" height="${cell}" rx="3" fill="${fill}" tabindex="0"><title>${d.date}: ${d.count} contributions</title></rect>`)});return o.join('')+'</svg>'}
function show(n){document.querySelectorAll('[data-days]').forEach(b=>b.setAttribute('aria-pressed',String(+b.dataset.days===n)));document.getElementById('chart').innerHTML=chart(n);document.querySelectorAll('#chart rect[data-date]').forEach(r=>{let f=()=>document.getElementById('tip').textContent=r.dataset.date+' · '+r.dataset.count+' contributions';r.addEventListener('mouseenter',f);r.addEventListener('focus',f);r.addEventListener('click',f)})}
document.querySelectorAll('[data-days]').forEach(b=>b.addEventListener('click',()=>show(+b.dataset.days)));show(30);document.getElementById('heatmap').innerHTML=heatmap();
</script></body></html>'''
    return page.replace("__DATA__",payload)

def main():
    if not TOKEN: raise RuntimeError("GITHUB_TOKEN is missing")
    today=datetime.now(timezone.utc).date(); start=today-timedelta(days=364)
    cal=api_calendar(start,today)
    days=[{"date":x["date"],"count":int(x["contributionCount"])} for w in cal["weeks"] for x in w["contributionDays"] if start.isoformat()<=x["date"]<=today.isoformat()]
    last=days[-30:]; by={x["date"]:x["count"] for x in days}; streak=0; cur=today
    while cur>=start and by.get(cur.isoformat(),0)>0: streak+=1;cur-=timedelta(days=1)
    if streak==0:
        cur=today-timedelta(days=1)
        while cur>=start and by.get(cur.isoformat(),0)>0: streak+=1;cur-=timedelta(days=1)
    data={"username":USER,"updated":today.strftime("%d %b %Y"),"days":days,"total_year":int(cal["totalContributions"]),
          "total30":sum(x["count"] for x in last),"active30":sum(x["count"]>0 for x in last),"streak":streak,"public_repos":repos()}
    OUT.mkdir(exist_ok=True); (OUT/"data.json").write_text(json.dumps(data,separators=(",",":")))
    (OUT/"dashboard.svg").write_text(make_svg(data))
    for n in (30,90,365): (OUT/f"activity-{n}d.svg").write_text(make_svg(data,n,False))
    (OUT/"index.html").write_text(make_html(data))
    print("Dashboard generated:",data["total30"],"contributions in the last 30 days")

if __name__=="__main__": main()
