from __future__ import annotations
from homeassistant.components.number import NumberEntity, NumberMode
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfLength
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from .const import DOMAIN, SIGNAL_UPDATED
async def async_setup_entry(hass:HomeAssistant, entry:ConfigEntry, async_add_entities:AddEntitiesCallback)->None:
    async_add_entities([FishLengthNumber(entry,hass.data[DOMAIN][entry.entry_id]['store'])],True)
class FishLengthNumber(NumberEntity):
    _attr_has_entity_name=True; _attr_name='Fischlänge'; _attr_icon='mdi:ruler'; _attr_native_min_value=0; _attr_native_max_value=150; _attr_native_step=1; _attr_native_unit_of_measurement=UnitOfLength.CENTIMETERS; _attr_mode=NumberMode.BOX
    def __init__(self,entry,store): self.entry=entry; self.store=store; self._attr_unique_id=f'{entry.entry_id}_length_cm'
    @property
    def native_value(self):
        try: return float(self.store.settings.get('length_cm',0))
        except Exception: return 0
    async def async_set_native_value(self,value): await self.store.async_set_setting('length_cm',int(value)); self.async_write_ha_state()
    async def async_added_to_hass(self): self.async_on_remove(async_dispatcher_connect(self.hass,SIGNAL_UPDATED,self._handle_update))
    @callback
    def _handle_update(self): self.async_write_ha_state()
