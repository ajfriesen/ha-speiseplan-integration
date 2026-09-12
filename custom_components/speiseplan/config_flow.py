"""Config flow for SpeisePlan."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

import voluptuous as vol
from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.const import CONF_HOST, CONF_PORT, CONF_SSL, CONF_TOKEN
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import SpeisePlanAuthError, SpeisePlanError, async_probe
from .const import DEFAULT_NAME, DEFAULT_PORT, DOMAIN


def _schema(defaults: Mapping[str, Any] | None = None) -> vol.Schema:
    """Connection form, pre-filled when reconfiguring."""
    defaults = defaults or {}
    return vol.Schema(
        {
            vol.Required(
                CONF_HOST, default=defaults.get(CONF_HOST, vol.UNDEFINED)
            ): str,
            vol.Required(CONF_PORT, default=defaults.get(CONF_PORT, DEFAULT_PORT)): int,
            vol.Required(
                CONF_TOKEN, default=defaults.get(CONF_TOKEN, vol.UNDEFINED)
            ): str,
            vol.Required(CONF_SSL, default=defaults.get(CONF_SSL, False)): bool,
        }
    )


class SpeisePlanConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for SpeisePlan."""

    VERSION = 1

    async def _validate(
        self, user_input: Mapping[str, Any]
    ) -> tuple[dict[str, Any] | None, str | None]:
        """Return (info, error_code)."""
        session = async_get_clientsession(self.hass)
        try:
            info = await async_probe(
                session,
                user_input[CONF_HOST],
                user_input[CONF_PORT],
                user_input.get(CONF_SSL, False),
                user_input[CONF_TOKEN],
            )
        except SpeisePlanAuthError:
            return None, "invalid_auth"
        except SpeisePlanError:
            return None, "cannot_connect"
        if not info.get("instance_id"):
            return None, "unsupported_version"
        return info, None

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle a manually added SpeisePlan."""
        errors: dict[str, str] = {}
        if user_input is not None:
            info, error = await self._validate(user_input)
            if error:
                errors["base"] = error
            else:
                assert info is not None
                await self.async_set_unique_id(info["instance_id"])
                self._abort_if_unique_id_configured(
                    updates={
                        CONF_HOST: user_input[CONF_HOST],
                        CONF_PORT: user_input[CONF_PORT],
                    }
                )
                return self.async_create_entry(title=DEFAULT_NAME, data=user_input)

        return self.async_show_form(
            step_id="user", data_schema=_schema(user_input), errors=errors
        )

    async def async_step_reauth(
        self, entry_data: Mapping[str, Any]
    ) -> ConfigFlowResult:
        """Handle re-authentication when the API token stops working."""
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Collect a new token for an existing entry."""
        errors: dict[str, str] = {}
        reauth_entry = self._get_reauth_entry()
        if user_input is not None:
            info, error = await self._validate({**reauth_entry.data, **user_input})
            if error:
                errors["base"] = error
            else:
                assert info is not None
                await self.async_set_unique_id(info["instance_id"])
                self._abort_if_unique_id_mismatch(reason="wrong_instance")
                return self.async_update_reload_and_abort(
                    reauth_entry, data_updates={CONF_TOKEN: user_input[CONF_TOKEN]}
                )

        return self.async_show_form(
            step_id="reauth_confirm",
            data_schema=vol.Schema({vol.Required(CONF_TOKEN): str}),
            errors=errors,
        )

    async def async_step_reconfigure(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Change where SpeisePlan lives without losing the entity history."""
        errors: dict[str, str] = {}
        entry = self._get_reconfigure_entry()
        if user_input is not None:
            info, error = await self._validate(user_input)
            if error:
                errors["base"] = error
            else:
                assert info is not None
                await self.async_set_unique_id(info["instance_id"])
                self._abort_if_unique_id_mismatch(reason="wrong_instance")
                return self.async_update_reload_and_abort(
                    entry, data_updates=user_input
                )

        return self.async_show_form(
            step_id="reconfigure",
            data_schema=_schema(user_input or entry.data),
            errors=errors,
        )
