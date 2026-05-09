from __future__ import annotations
from typing import Any
from .analytics import weighted_rate, success
def feature_bucket(entry: dict[str, Any]) -> tuple[str,...]:
    def bucket_num(value,step,default=0):
        try: v=float(value)
        except Exception: v=default
        return str(int(v//step*step))
    return (str(entry.get('fish_type') or entry.get('fischart') or 'any'),str(entry.get('spot') or 'any'),str(entry.get('bait') or entry.get('koeder') or 'any'),bucket_num(entry.get('temperature') or entry.get('temp'),5,15),bucket_num(entry.get('wind_speed') or entry.get('wind'),5,10),bucket_num(entry.get('pressure') or entry.get('druck'),10,1010))
def similar_history_score(entries,target):
    if not entries: return {'score':50.0,'matches':0,'note':'Keine historischen Daten'}
    tb=feature_bucket(target); matches=[e for e in entries if feature_bucket(e)==tb]
    if len(matches)<3: matches=[e for e in entries if e.get('spot')==target.get('spot') or (e.get('bait') or e.get('koeder'))==(target.get('bait') or target.get('koeder'))]
    if not matches: return {'score':50.0,'matches':0,'note':'Keine ähnlichen Bedingungen'}
    caught=sum(1 for e in matches if success(e)); return {'score':weighted_rate(caught,len(matches)),'matches':len(matches),'note':f'{caught} Fänge bei {len(matches)} ähnlichen Einträgen'}
