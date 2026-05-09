from __future__ import annotations
from typing import Any
import voluptuous as vol
from homeassistant import config_entries
from homeassistant.const import CONF_NAME
from homeassistant.core import callback
from .const import CONF_PERSON_ENTITY, CONF_WEATHER_ENTITY, DEFAULT_NAME, DOMAIN
class FishingTrackerConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION=1
    async def async_step_user(self,user_input:dict[str,Any]|None=None):
        if user_input is not None:
            await self.async_set_unique_id(DOMAIN); self._abort_if_unique_id_configured(); return self.async_create_entry(title=user_input.get(CONF_NAME,DEFAULT_NAME),data=user_input)
        return self.async_show_form(step_id='user',data_schema=vol.Schema({vol.Required(CONF_NAME,default=DEFAULT_NAME):str,vol.Required(CONF_WEATHER_ENTITY,default='weather.home'):str,vol.Optional(CONF_PERSON_ENTITY,default=''):str}),errors={})
    @staticmethod
    @callback
    def async_get_options_flow(config_entry): return FishingTrackerOptionsFlow(config_entry)
class FishingTrackerOptionsFlow(config_entries.OptionsFlow):
    def __init__(self,config_entry): self.config_entry=config_entry
    async def async_step_init(self,user_input:dict[str,Any]|None=None):
        if user_input is not None: return self.async_create_entry(title='',data=user_input)
        data={**self.config_entry.data,**self.config_entry.options}; return self.async_show_form(step_id='init',data_schema=vol.Schema({vol.Required(CONF_WEATHER_ENTITY,default=data.get(CONF_WEATHER_ENTITY,'weather.home')):str,vol.Optional(CONF_PERSON_ENTITY,default=data.get(CONF_PERSON_ENTITY,'')):str}))
