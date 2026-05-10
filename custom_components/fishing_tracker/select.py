from __future__ import annotations

from homeassistant.components.select import SelectEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import BAITS, DOMAIN, FISH_TYPES, SIGNAL_UPDATED, SPOTS


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    store = hass.data[DOMAIN][entry.entry_id]["store"]

    async_add_entities([
        FishingSelect(entry, store, "fish_type", "Fischart", FISH_TYPES, "mdi:fish"),
        FishingSelect(entry, store, "spot", "Spot", SPOTS, "mdi:map-marker"),
        FishingSelect(entry, store, "bait", "Köder", BAITS, "mdi:hook"),
    ], True)


class FishingSelect(SelectEntity):
    _attr_has_entity_name = True

    def __init__(self, entry: ConfigEntry, store, key: str, name: str, options: list[str], icon: str) -> None:
        self.entry = entry
        self.store = store
        self.key = key
        self._attr_name = name
        self._attr_unique_id = f"{entry.entry_id}_{key}"
        self._attr_options = options
        self._attr_icon = icon

    @property
    def current_option(self):
        return self.store.settings.get(self.key)

    async def async_select_option(self, option: str) -> None:
        await self.store.async_set_setting(self.key, option)
        self.async_write_ha_state()

    async def async_added_to_hass(self) -> None:
        self.async_on_remove(
            async_dispatcher_connect(self.hass, SIGNAL_UPDATED, self._handle_update)
        )

    @callback
    def _handle_update(self) -> None:
        self.async_write_ha_state()
