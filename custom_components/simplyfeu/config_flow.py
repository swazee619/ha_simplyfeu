"""Configuration par l'interface de Home Assistant."""

from __future__ import annotations

from typing import Any
from urllib.parse import urlsplit, urlunsplit

import voluptuous as vol

from homeassistant.config_entries import (
    ConfigEntry,
    ConfigFlow,
    ConfigFlowResult,
    OptionsFlow,
)
from homeassistant.const import CONF_NAME
from homeassistant.core import callback
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.selector import (
    NumberSelector,
    NumberSelectorConfig,
    NumberSelectorMode,
    TextSelector,
    TextSelectorConfig,
    TextSelectorType,
)

from .api import SimplyFeuClient, SimplyFeuConnectionError
from .const import (
    CONF_COOKIE,
    CONF_PRICE_REGEX,
    CONF_SCAN_INTERVAL,
    CONF_URL,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
    LOGGER,
    MAX_SCAN_INTERVAL,
    MIN_SCAN_INTERVAL,
)
from .parser import PriceNotFoundError, is_valid_price_regex

_TEXT = TextSelector()
_MULTILINE = TextSelector(TextSelectorConfig(multiline=True))

USER_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_URL): TextSelector(TextSelectorConfig(type=TextSelectorType.URL)),
        vol.Optional(CONF_NAME): _TEXT,
        vol.Optional(CONF_PRICE_REGEX): _TEXT,
        vol.Optional(CONF_COOKIE): _MULTILINE,
    }
)

OPTIONS_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_SCAN_INTERVAL, default=DEFAULT_SCAN_INTERVAL): NumberSelector(
            NumberSelectorConfig(
                min=MIN_SCAN_INTERVAL,
                max=MAX_SCAN_INTERVAL,
                step=1,
                mode=NumberSelectorMode.BOX,
                unit_of_measurement="h",
            )
        ),
        vol.Optional(CONF_PRICE_REGEX): _TEXT,
        vol.Optional(CONF_COOKIE): _MULTILINE,
    }
)


def _normalize_url(url: str) -> str:
    parts = urlsplit(url.strip())
    return urlunsplit(
        (parts.scheme.lower(), parts.netloc.lower(), parts.path.rstrip("/"), parts.query, "")
    )


async def _async_validate(
    flow: ConfigFlow | OptionsFlow, url: str, data: dict[str, Any]
) -> tuple[dict[str, str], str | None]:
    """Teste l'extraction ; renvoie (erreurs, nom du produit)."""
    errors: dict[str, str] = {}
    regex = data.get(CONF_PRICE_REGEX)
    if regex and not is_valid_price_regex(regex):
        return {CONF_PRICE_REGEX: "invalid_regex"}, None

    client = SimplyFeuClient(
        async_get_clientsession(flow.hass),
        url,
        cookie=data.get(CONF_COOKIE),
        price_regex=regex,
    )
    try:
        info = await client.async_fetch()
    except SimplyFeuConnectionError:
        errors["base"] = "cannot_connect"
    except PriceNotFoundError:
        errors["base"] = "price_not_found"
    except Exception:  # noqa: BLE001
        LOGGER.exception("Erreur inattendue lors de la validation")
        errors["base"] = "unknown"
    else:
        return errors, info.name
    return errors, None


class SimplyFeuConfigFlow(ConfigFlow, domain=DOMAIN):
    """Ajout d'un produit à suivre."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        errors: dict[str, str] = {}

        if user_input is not None:
            url = user_input[CONF_URL].strip()
            if not url.startswith(("http://", "https://")):
                errors[CONF_URL] = "invalid_url"
            else:
                await self.async_set_unique_id(_normalize_url(url))
                self._abort_if_unique_id_configured()

                errors, product_name = await _async_validate(self, url, user_input)
                if not errors:
                    options = {CONF_SCAN_INTERVAL: DEFAULT_SCAN_INTERVAL}
                    for key in (CONF_PRICE_REGEX, CONF_COOKIE):
                        if user_input.get(key):
                            options[key] = user_input[key]
                    return self.async_create_entry(
                        title=user_input.get(CONF_NAME) or product_name or "SimplyFeu",
                        data={CONF_URL: url},
                        options=options,
                    )

        return self.async_show_form(
            step_id="user",
            data_schema=self.add_suggested_values_to_schema(USER_SCHEMA, user_input),
            errors=errors,
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> SimplyFeuOptionsFlow:
        return SimplyFeuOptionsFlow()


class SimplyFeuOptionsFlow(OptionsFlow):
    """Modification de la fréquence, de la regex ou du cookie."""

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        errors: dict[str, str] = {}

        if user_input is not None:
            errors, _ = await _async_validate(
                self, self.config_entry.data[CONF_URL], user_input
            )
            if not errors:
                user_input[CONF_SCAN_INTERVAL] = int(user_input[CONF_SCAN_INTERVAL])
                return self.async_create_entry(data=user_input)

        return self.async_show_form(
            step_id="init",
            data_schema=self.add_suggested_values_to_schema(
                OPTIONS_SCHEMA, user_input or dict(self.config_entry.options)
            ),
            errors=errors,
        )
