from __future__ import annotations
from pathlib import Path
from typing import Any
import csv
from homeassistant.core import HomeAssistant
from homeassistant.helpers.storage import Store
from .const import DEFAULT_SETTINGS, STORAGE_KEY, STORAGE_VERSION
class FishingStore:
    def __init__(self, hass: HomeAssistant) -> None:
        self.hass=hass; self._store=Store(hass, STORAGE_VERSION, STORAGE_KEY); self.data={"entries":[],"settings":dict(DEFAULT_SETTINGS)}
    async def async_load(self)->None:
        data=await self._store.async_load()
        if isinstance(data,dict): self.data=data
        self.data.setdefault("entries",[]); self.data.setdefault("settings",{})
        for k,v in DEFAULT_SETTINGS.items(): self.data["settings"].setdefault(k,v)
    async def async_save(self)->None: await self._store.async_save(self.data)
    @property
    def entries(self): return self.data.setdefault("entries",[])
    @property
    def settings(self):
        self.data.setdefault("settings",{})
        for k,v in DEFAULT_SETTINGS.items(): self.data["settings"].setdefault(k,v)
        return self.data["settings"]
    async def async_set_setting(self,k,v): self.settings[k]=v; await self.async_save()
    async def async_add_entry(self,e): self.entries.append(e); await self.async_save()
    async def async_import_csv(self,path):
        fp=Path(path); imported=0
        if not fp.exists(): return 0
        with fp.open(newline='',encoding='utf-8') as f:
            for r in csv.reader(f):
                if len(r)<13: continue
                self.entries.append({"timestamp":r[0],"angler":r[1],"latitude":_none(r[2]),"longitude":_none(r[3]),"fish_type":r[4],"caught":_to_int(r[5]),"spot":r[6],"bait":r[7],"chance":_to_float(r[8]),"pressure":_to_float(r[9],1015),"pressure_trend":_to_float(r[10]),"wind_speed":_to_float(r[11]),"temperature":_to_float(r[12]),"length_cm":r[13] if len(r)>=14 else "Unbekannt","source":"csv_import"}); imported+=1
        await self.async_save(); return imported
    async def async_export_csv(self,path):
        fp=Path(path); fp.parent.mkdir(parents=True,exist_ok=True)
        with fp.open('w',newline='',encoding='utf-8') as f:
            wr=csv.writer(f)
            for e in self.entries: wr.writerow([e.get('timestamp',''),e.get('angler',''),e.get('latitude',''),e.get('longitude',''),e.get('fish_type',''),e.get('caught',0),e.get('spot',''),e.get('bait',''),e.get('chance',''),e.get('pressure',''),e.get('pressure_trend',''),e.get('wind_speed',''),e.get('temperature',''),e.get('length_cm','Unbekannt')])
        return len(self.entries)
def _none(v): return None if v in ('None','',None) else v
def _to_float(v,d=0.0):
    try: return d if v in ('None','',None) else float(v)
    except Exception: return d
def _to_int(v,d=0):
    try: return int(float(v))
    except Exception: return d
