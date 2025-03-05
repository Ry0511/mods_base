from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from typing import TYPE_CHECKING, TypedDict

from . import MODS_DIR

if TYPE_CHECKING:
    from .mod import Mod
    from .options import BaseOption

type JSON = Mapping[str, JSON] | Sequence[JSON] | str | int | float | bool | None

SETTINGS_DIR = MODS_DIR / "settings"
SETTINGS_DIR.mkdir(parents=True, exist_ok=True)


class BasicModSettings(TypedDict, total=False):
    enabled: bool
    options: dict[str, JSON]
    keybinds: dict[str, str | None]


def load_options_dict(
    options: Sequence[BaseOption],
    settings: Mapping[str, JSON],
) -> None:
    """
    Recursively loads options from their settings dict.

    Args:
        options: The list of options to load.
        settings: The settings dict.
    """
    for option in options:
        if option.identifier not in settings:
            continue

        value = settings[option.identifier]

        option._from_json(value)  # type: ignore


def default_load_mod_settings(self: Mod) -> None:
    """Default implementation for Mod.load_settings."""
    if self.settings_file is None:
        return

    settings: BasicModSettings
    try:
        with self.settings_file.open() as file:
            settings = json.load(file)
    except (FileNotFoundError, json.JSONDecodeError):
        return

    # No sense doing this if not defined
    if "options" in settings:
        load_options_dict(self.options, settings["options"])

    if "keybinds" in settings:
        saved_keybinds = settings["keybinds"]
        for keybind in self.keybinds:
            if keybind.identifier in saved_keybinds:
                key = saved_keybinds[keybind.identifier]
                if key is None:
                    keybind.key = None
                else:
                    keybind.key = str(key)

    if self.auto_enable and settings.get("enabled", False):
        self.enable()


def create_options_dict(options: Sequence[BaseOption]) -> dict[str, JSON]:
    """
    Creates an options dict from a list of options.

    Args:
        options: The list of options to save.
    Returns:
        The options' values in dict form.
    """
    return {
        option.identifier: child_json
        for option in options
        if (child_json := option._to_json()) is not ...  # pyright: ignore[reportPrivateUsage]
    }


def default_save_mod_settings(self: Mod) -> None:
    """Default implementation for Mod.save_settings."""
    if self.settings_file is None:
        return

    settings: BasicModSettings = {}

    if len(self.options) > 0:
        option_settings = create_options_dict(self.options)
        if len(option_settings) > 0:
            settings["options"] = option_settings

    if len(self.keybinds) > 0:
        keybind_settings: dict[str, str | None] = {}
        for keybind in self.keybinds:
            if not keybind.is_rebindable:
                continue
            keybind_settings[keybind.identifier] = keybind.key

        if len(keybind_settings) > 0:
            settings["keybinds"] = keybind_settings

    if self.auto_enable:
        settings["enabled"] = self.is_enabled

    if len(settings) == 0:
        self.settings_file.unlink(missing_ok=True)
        return

    with self.settings_file.open("w") as file:
        json.dump(settings, file, indent=4)
