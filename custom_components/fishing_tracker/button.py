from __future__ import annotations
from homeassistant.components.button import ButtonEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from . import async_log_entry
async def async_setup_entry(hass:HomeAssistant, entry:ConfigEntry, async_add_entities:AddEntitiesCallback)->None:
    async_add_entities([LogCatchButton(hass,entry),LogNoCatchButton(hass,entry)],True)
class FishingButton(ButtonEntity):
    _attr_has_entity_name=True
    def __init__(self,hass,entry,key,name,icon,caught): self.hass=hass; self.entry=entry; self.caught=caught; self._attr_unique_id=f'{entry.entry_id}_{key}'; self._attr_name=name; self._attr_icon=icon
    async def async_press(self): await async_log_entry(self.hass,self.entry,self.caught,{})
class LogCatchButton(FishingButton):
    def __init__(self,hass,entry): super().__init__(hass,entry,'log_catch_button','Fang speichern','mdi:fish',1)
class LogNoCatchButton(FishingButton):
    def __init__(self,hass,entry): super().__init__(hass,entry,'log_no_catch_button','Kein Fang speichern','mdi:close',0)
