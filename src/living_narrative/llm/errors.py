"""Typed LLM provider errors."""


def scrub_secret(text: object, secrets: list[str | None] | None = None) -> str:
    value = str(text)
    for secret in secrets or []:
        if secret:
            value = value.replace(secret, "[REDACTED]")
    return value


class ProviderRegistryError(ValueError):
    pass


class StructuredOutputError(RuntimeError):
    def __init__(
        self,
        *,
        provider_name: str,
        model: str,
        schema_name: str,
        last_error: object,
        secrets: list[str | None] | None = None,
    ) -> None:
        self.provider_name = provider_name
        self.model = model
        self.schema_name = schema_name
        self.last_error = scrub_secret(last_error, secrets)
        super().__init__(
            f"{provider_name} model {model} failed to produce {schema_name}: {self.last_error}"
        )


class FixtureResponseError(StructuredOutputError):
    pass


class ProviderConnectionError(RuntimeError):
    def __init__(
        self,
        *,
        provider_name: str,
        model: str,
        error: object,
        secrets: list[str | None] | None = None,
    ) -> None:
        self.provider_name = provider_name
        self.model = model
        self.error = scrub_secret(error, secrets)
        super().__init__(f"{provider_name} model {model} request failed: {self.error}")
