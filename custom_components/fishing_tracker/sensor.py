from __future__ import annotations
from datetime import datetime, timedelta
from typing import Any
from homeassistant.components.sensor import SensorEntity, SensorDeviceClass
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import PERCENTAGE, UnitOfTemperature
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from .analytics import current_weather_score, recommendation, stats
from .const import CONF_WEATHER_ENTITY, DOMAIN, SIGNAL_UPDATED
async def async_setup_entry(hass:HomeAssistant, entry:ConfigEntry, async_add_entities:AddEntitiesCallback)->None:
    store=hass.data[DOMAIN][entry.entry_id]['store']; async_add_entities([BiteChanceSensor(hass,entry,store),BestTimeSensor(hass,entry,store),StatsSensor(entry,store),RecommendationSensor(entry,store),WaterTemperatureSensor(hass,entry),MapDataSensor(entry,store)],True)
class FishingBaseSensor(SensorEntity):
    _attr_has_entity_name=True
    def __init__(self,entry,store,key,name): self.entry=entry; self.store=store; self._attr_unique_id=f'{entry.entry_id}_{key}'; self._attr_name=name; self._attr_should_poll=True; self._state=None; self._attrs={}
    @property
    def native_value(self): return self._state
    @property
    def extra_state_attributes(self): return self._attrs
    async def async_added_to_hass(self): self.async_on_remove(async_dispatcher_connect(self.hass,SIGNAL_UPDATED,self._handle_update))
    @callback
    def _handle_update(self): self.async_schedule_update_ha_state(True)
class BiteChanceSensor(FishingBaseSensor):
    _attr_native_unit_of_measurement=PERCENTAGE; _attr_icon='mdi:fish'
    def __init__(self,hass,entry,store): super().__init__(entry,store,'bite_chance','Beißchance Weißfisch'); self.hass=hass
    async def async_update(self): self._state,self._attrs=_calculate_now(self.hass,self.entry,self.store.entries)
class BestTimeSensor(FishingBaseSensor):
    _attr_icon='mdi:clock-outline'
    def __init__(self,hass,entry,store): super().__init__(entry,store,'best_time_today','Beste Angelzeit heute'); self.hass=hass
    async def async_update(self): r=_calculate_best_time(self.hass,self.entry,self.store.entries); self._state=r['zeitfenster']; self._attrs=r
class StatsSensor(FishingBaseSensor):
    _attr_native_unit_of_measurement=PERCENTAGE; _attr_icon='mdi:chart-box'
    def __init__(self,entry,store): super().__init__(entry,store,'statistics','Statistik')
    async def async_update(self): s=stats(self.store.entries); self._state=s.get('history_score',50); self._attrs=s
class RecommendationSensor(FishingBaseSensor):
    _attr_icon='mdi:lightbulb-on-outline'
    def __init__(self,entry,store): super().__init__(entry,store,'recommendation','Angel KI Empfehlung')
    async def async_update(self): self._state=recommendation(self.store.entries)[:255]; self._attrs=stats(self.store.entries)
class WaterTemperatureSensor(SensorEntity):
    _attr_has_entity_name=True; _attr_name='Wassertemperatur geschätzt'; _attr_native_unit_of_measurement=UnitOfTemperature.CELSIUS; _attr_device_class=SensorDeviceClass.TEMPERATURE; _attr_icon='mdi:thermometer-water'
    def __init__(self,hass,entry): self.hass=hass; self.entry=entry; self._attr_unique_id=f'{entry.entry_id}_estimated_water_temperature'; self._state=None
    @property
    def native_value(self): return self._state
    async def async_update(self):
        we=self.entry.options.get(CONF_WEATHER_ENTITY) or self.entry.data.get(CONF_WEATHER_ENTITY); w=self.hass.states.get(we); temp=_float(w.attributes.get('temperature') if w else None,12); self._state=round(temp*.65+5,1)
class MapDataSensor(FishingBaseSensor):
    _attr_icon='mdi:map-marker-radius'
    def __init__(self,entry,store): super().__init__(entry,store,'map_data','Karten Daten')
    async def async_update(self):
        catches=[]; heatmap=[]; spot_groups={}
        for item in self.store.entries:
            lat=_float(item.get('latitude'),None); lon=_float(item.get('longitude'),None)
            if lat is None or lon is None: continue
            catches.append({'lat':lat,'lon':lon,'timestamp':item.get('timestamp'),'fish_type':item.get('fish_type'),'spot':item.get('spot'),'bait':item.get('bait'),'length_cm':item.get('length_cm'),'caught':item.get('caught',0),'chance':item.get('chance')})
            if int(item.get('caught',0))>=1: heatmap.append([lat,lon,0.8])
            spot=item.get('spot') or 'Unbekannt'; g=spot_groups.setdefault(spot,{'spot':spot,'lat':lat,'lon':lon,'total':0,'catches':0}); g['total']+=1; g['catches']+=1 if int(item.get('caught',0))>=1 else 0
        spots=[]
        for g in spot_groups.values(): g['success_rate']=round(g['catches']/g['total']*100,1) if g['total'] else 0; spots.append(g)
        self._state=len(catches); self._attrs={'catches':catches[-200:],'heatmap':heatmap[-200:],'spots':spots}
def _calculate_best_time(hass,entry,entries):
    we=entry.options.get(CONF_WEATHER_ENTITY) or entry.data.get(CONF_WEATHER_ENTITY); w=hass.states.get(we); attrs=w.attributes if w else {}; now=datetime.now().astimezone(); best_score=0; best_time='--:--'; best_dt=now; points=[]
    for i in range(24):
        ts=now.replace(minute=0,second=0,microsecond=0)+timedelta(hours=i); score=_score_for_hour(hass,entry,entries,attrs,ts); points.append({'x':int(ts.timestamp()*1000),'y':score})
        if ts.date()==now.date() and score>best_score: best_score=score; best_time=ts.strftime('%H:%M'); best_dt=ts
    start=best_dt-timedelta(hours=1); end=best_dt+timedelta(hours=2); zeitfenster=f"{start.strftime('%H:%M')} – {end.strftime('%H:%M')}"
    if best_score>=85: akt='Sehr hoch'; emp='Top-Phase nutzen: fein fischen und regelmäßig sparsam füttern.'
    elif best_score>=70: akt='Hoch'; emp='Gute Bedingungen: Windkante, Kanten und bewährte Köder testen.'
    elif best_score>=50: akt='Mittel'; emp='Solide Phase: klein starten und bei Bedarf Spot wechseln.'
    else: akt='Niedrig'; emp='Schwache Phase: sehr fein fischen oder später erneut probieren.'
    s=stats(entries); return {'score':best_score,'beste_uhrzeit':best_time,'zeitfenster':zeitfenster,'aktivitaet':akt,'empfehlung':emp,'tagesprognose':points,'history_score':s.get('history_score',50),'confidence':s.get('confidence'),'total_entries':s.get('total')}
def _calculate_now(hass,entry,entries):
    we=entry.options.get(CONF_WEATHER_ENTITY) or entry.data.get(CONF_WEATHER_ENTITY); w=hass.states.get(we); attrs=w.attributes if w else {}; now=datetime.now().astimezone(); score=_score_for_hour(hass,entry,entries,attrs,now); s=stats(entries)
    return score, {'weather_entity':we,'temperature':_float(attrs.get('temperature'),12),'pressure':_float(attrs.get('pressure'),1015),'wind_speed':_float(attrs.get('wind_speed'),10),'cloud_coverage':_float(attrs.get('cloud_coverage'),50),'precipitation':_float(attrs.get('precipitation'),0),'history_score':s.get('history_score',50),'confidence':s.get('confidence'),'total_entries':s.get('total'),'top_combo':s.get('top_combo'),'recommendation':recommendation(entries)}
def _score_for_hour(hass,entry,entries,attrs,ts):
    s=stats(entries); moon=hass.states.get('sensor.moon')
    return current_weather_score(_float(attrs.get('temperature'),12),_float(attrs.get('wind_speed'),10),_float(attrs.get('pressure'),1015),_float(attrs.get('cloud_coverage'),50),_float(attrs.get('precipitation'),0),0,ts.hour,ts.month,moon.state if moon else None,s.get('history_score',50))
def _float(value,default=0.0):
    try: return default if value in (None,'','unknown','unavailable') else float(value)
    except Exception: return default


class FishingHistorySensor(FishingBaseSensor):
    _attr_icon = "mdi:chart-timeline-variant"

    def __init__(self, entry: ConfigEntry, store) -> None:
        super().__init__(entry, store, "history_summary", "Fanghistorie")

    async def async_update(self) -> None:
        s = stats(self.store.entries)
        total = s.get("total", 0)
        score = s.get("history_score", 50)

        self._state = f"{total} Einträge"
        self._attrs = {
            "gesamt_eintraege": total,
            "historischer_score": score,
            "empfehlung": recommendation(self.store.entries),
        }
