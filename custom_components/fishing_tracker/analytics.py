from __future__ import annotations
from collections import defaultdict
from datetime import datetime
from typing import Any
def _safe_int(v,d=0):
    try: return int(float(v))
    except Exception: return d
def parse_hour(v):
    try:
        if isinstance(v,str): return datetime.fromisoformat(v.replace('Z','+00:00')).hour
    except Exception: return None
    return None
def normalize_length(v):
    if v in (None,'','Unbekannt','unknown','unavailable'): return None
    try: return int(float(str(v).replace('cm','').strip()))
    except Exception: return None
def success(e): return _safe_int(e.get('caught',e.get('anzahl',0)))>=1
def calculate_rate(entries): return round(sum(1 for e in entries if success(e))/len(entries)*100,1) if entries else 0.0
def confidence_label(total): return 'sehr hoch' if total>=100 else 'hoch' if total>=50 else 'mittel' if total>=20 else 'niedrig' if total>=5 else 'sehr niedrig'
def weighted_rate(fang,total,prior=50.0,strength=8): return prior if total<=0 else round(((fang*100)+(prior*strength))/(total+strength),1)
def best_by(entries,key,minimum=2):
    groups=defaultdict(lambda:{'fang':0,'gesamt':0})
    for e in entries:
        val=e.get(key) or 'Unbekannt'; groups[str(val)]['gesamt']+=1; groups[str(val)]['fang']+=1 if success(e) else 0
    best={'name':'Keine Daten','rate':0.0,'count':0,'raw_rate':0.0}
    for name,it in groups.items():
        if it['gesamt']<minimum: continue
        raw=round(it['fang']/it['gesamt']*100,1); sm=weighted_rate(it['fang'],it['gesamt']); rank=sm*min(1.0,it['gesamt']/12); cur=best['rate']*min(1.0,max(best['count'],1)/12)
        if rank>cur: best={'name':name,'rate':sm,'raw_rate':raw,'count':it['gesamt']}
    return best
def combo_key(e): return f"{e.get('spot') or 'Unbekannt'} + {e.get('bait') or e.get('koeder') or 'Unbekannt'}"
def stats(entries):
    total=len(entries); caught=sum(1 for e in entries if success(e)); rate=calculate_rate(entries); norm=[]
    for e in entries:
        n=dict(e); n.setdefault('bait',n.get('koeder')); n.setdefault('fish_type',n.get('fischart')); n.setdefault('hour',parse_hour(n.get('timestamp') or n.get('datum'))); n['combo']=combo_key(n); norm.append(n)
    lengths=[normalize_length(e.get('length_cm') or e.get('laenge')) for e in norm if success(e)]; lengths=[x for x in lengths if x is not None]
    hist=50.0 if total<5 else round((rate*0.5)+25,1) if total<20 else rate
    return {'total':total,'total_catches':caught,'total_no_catch':total-caught,'success_rate':rate,'history_score':hist,'confidence':confidence_label(total),'top_spot':best_by(norm,'spot'),'top_bait':best_by(norm,'bait'),'top_fish':best_by(norm,'fish_type'),'top_hour':best_by(norm,'hour'),'top_combo':best_by(norm,'combo'),'avg_length_cm':round(sum(lengths)/len(lengths),1) if lengths else None,'max_length_cm':max(lengths) if lengths else None}
def current_weather_score(temperature,wind_speed,pressure,cloud_coverage,precipitation,pressure_trend,hour,month,moon_phase=None,history_score=50.0):
    water=temperature*.65+5; score=45.0
    score += 14 if 5<=hour<=9 else 18 if 18<=hour<=22 else -14 if 11<=hour<=15 and month in [6,7,8] else -5 if 11<=hour<=15 else 2
    score += 18 if 12<=water<=19 else 8 if 8<=water<12 else 5 if 19<water<=23 else -18 if water<6 or water>25 else -6
    score += 12 if 5<=wind_speed<=18 else 4 if 18<wind_speed<=28 else -10 if wind_speed<3 else -16
    score += 9 if 1008<=pressure<=1022 else 2 if 1000<=pressure<1008 or 1022<pressure<=1030 else -10
    score += 10 if -3<=pressure_trend<=-0.5 else 5 if -0.5<pressure_trend<=1.5 else -15 if pressure_trend<-6 or pressure_trend>5 else -5
    score += 8 if 40<=cloud_coverage<=85 else -10 if cloud_coverage<20 and 11<=hour<=16 else -3 if cloud_coverage>95 else 0
    score += 6 if 0.1<=precipitation<=2 else -14 if precipitation>8 else -5 if precipitation>3 else 0
    score += 3 if moon_phase in ('new_moon','full_moon') else -1 if moon_phase in ('first_quarter','last_quarter') else 0
    score += 6 if month in [5,6,7,8,9] else 2 if month in [3,4,10] else -8
    return int(max(10,min(96,round(score*.75+history_score*.25))))
def recommendation(entries):
    s=stats(entries)
    if s['total']<5: return 'Noch zu wenig Daten. Speichere Fang und Kein-Fang konsequent, damit die Analyse lernen kann.'
    c=s['top_combo']; sp=s['top_spot']; b=s['top_bait']
    return f"Beste Kombi bisher: {c['name']} ({c['raw_rate']} %, {c['count']} Versuche). Top Spot: {sp['name']}. Top Köder: {b['name']}. Sicherheit: {s['confidence']}."
