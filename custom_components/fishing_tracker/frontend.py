from __future__ import annotations

from pathlib import Path
import shutil

from homeassistant.core import HomeAssistant

from .const import WWW_FILES


async def async_install_frontend_files(hass: HomeAssistant) -> None:
    """Copy bundled HTML frontend files to /config/www automatically."""
    await hass.async_add_executor_job(_install_frontend_files, hass)


def _install_frontend_files(hass: HomeAssistant) -> None:
    component_dir = Path(__file__).parent
    source_dir = component_dir / "www"
    target_dir = Path(hass.config.path("www"))
    target_dir.mkdir(parents=True, exist_ok=True)

    for filename in WWW_FILES:
        source = source_dir / filename
        target = target_dir / filename

        if not source.exists():
            continue

        # Always overwrite, so HACS updates refresh the frontend automatically.
        shutil.copyfile(source, target)
