from __future__ import annotations

from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.const import CONF_NAME
from homeassistant.core import callback

from .const import (
    CONF_MOON_ENTITY, CONF_PERSON_ENTITY, CONF_USE_ONLINE_WEATHER,
    CONF_WEATHER_ENTITY, CONF_WATER_TEMP_URL, CONF_LATITUDE, CONF_LONGITUDE,
    CONF_PEGEL_UUID, CONF_PEGEL_NAME,
    DEFAULT_NAME, DOMAIN,
)


class FishingTrackerConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_user(self, user_input: dict[str, Any] | None = None):
        errors: dict[str, str] = {}

        if user_input is not None:
            await self.async_set_unique_id(DOMAIN)
            self._abort_if_unique_id_configured()
            return self.async_create_entry(
                title=user_input.get(CONF_NAME, DEFAULT_NAME),
                data=user_input,
            )

        schema = vol.Schema({
            vol.Required(CONF_NAME, default=DEFAULT_NAME): str,
            vol.Required(CONF_WEATHER_ENTITY, default="weather.home"): str,
            vol.Optional(CONF_PERSON_ENTITY, default=""): str,
            vol.Optional(CONF_MOON_ENTITY, default="sensor.moon_phase"): str,
            vol.Optional(CONF_USE_ONLINE_WEATHER, default=True): bool,
            vol.Optional(CONF_WATER_TEMP_URL, default=""): str,
            vol.Optional(CONF_LATITUDE, default=0.0): vol.Coerce(float),
            vol.Optional(CONF_LONGITUDE, default=0.0): vol.Coerce(float),
        })

        return self.async_show_form(
            step_id="user",
            data_schema=schema,
            errors=errors,
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        return FishingTrackerOptionsFlow()


class FishingTrackerOptionsFlow(config_entries.OptionsFlow):
    async def async_step_init(self, user_input: dict[str, Any] | None = None):
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        config_entry = self.config_entry
        data = {**config_entry.data, **config_entry.options}

        schema = vol.Schema({
            vol.Required(
                CONF_WEATHER_ENTITY,
                default=data.get(CONF_WEATHER_ENTITY, "weather.home"),
            ): str,
            vol.Optional(
                CONF_PERSON_ENTITY,
                default=data.get(CONF_PERSON_ENTITY, ""),
            ): str,
            vol.Optional(
                CONF_MOON_ENTITY,
                default=data.get(CONF_MOON_ENTITY, "sensor.moon_phase"),
            ): str,
            vol.Optional(
                CONF_USE_ONLINE_WEATHER,
                default=data.get(CONF_USE_ONLINE_WEATHER, True),
            ): bool,
            vol.Optional(
                CONF_WATER_TEMP_URL,
                default=data.get(CONF_WATER_TEMP_URL, ""),
                description={"suggested_value": "https://wassertemperatur.site/flusse/water-temp-in-dinkel"},
            ): str,
            vol.Optional(
                CONF_LATITUDE,
                default=data.get(CONF_LATITUDE, 0.0),
            ): vol.Coerce(float),
            vol.Optional(
                CONF_LONGITUDE,
                default=data.get(CONF_LONGITUDE, 0.0),
            ): vol.Coerce(float),
            vol.Optional(
                CONF_PEGEL_UUID,
                default=data.get(CONF_PEGEL_UUID, ""),
                description={"suggested_value": "UUID aus pegelonline.wsv.de/webservices/rest-api/v2/stations.json"},
            ): str,
            vol.Optional(
                CONF_PEGEL_NAME,
                default=data.get(CONF_PEGEL_NAME, ""),
            ): str,
        })

        return self.async_show_form(
            step_id="init",
            data_schema=schema,
        )
