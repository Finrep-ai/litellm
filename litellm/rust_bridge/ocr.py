"""Thin Python wrapper for the native Rust OCR bridge."""

from __future__ import annotations

from collections.abc import Awaitable, Generator
from contextlib import contextmanager
from typing import Final, Protocol, cast  # noqa: TID251  # native extension exposes dynamically typed callables

import httpx
from pydantic import TypeAdapter

from litellm.rust_bridge import configuration as _configuration
from litellm.rust_bridge.timeouts import timeout_to_seconds as _timeout_to_seconds

rust_ocr_enabled = _configuration.rust_ocr_enabled
use_litellm_rust = _configuration.use_litellm_rust


class _OcrProviderError(Exception):
    def __init__(self, status_code: int, message: str, request_url: str | None) -> None:
        super().__init__(message)
        self.status_code: Final = status_code
        request: Final = httpx.Request("POST", request_url) if request_url is not None else None
        self.response: Final = httpx.Response(status_code=status_code, request=request)


@contextmanager
def _map_ocr_errors(request_url: str | None) -> Generator[None]:
    from litellm.rust_bridge import get_native_bridge

    native_bridge: Final = get_native_bridge()
    error_type: Final = getattr(native_bridge, "RustUpstreamError", None)
    upstream_errors: Final[tuple[type[Exception], ...]] = (
        (error_type,) if isinstance(error_type, type) and issubclass(error_type, Exception) else ()
    )
    try:
        yield
    except upstream_errors as error:
        status, message = TypeAdapter(tuple[int, str]).validate_python(error.args, strict=True)
        raise _OcrProviderError(status or 500, message, request_url) from error


class RustOcr(Protocol):
    def __call__(
        self,
        model: str,
        document: dict[str, object],
        api_key: str | None,
        api_base: str | None,
        custom_llm_provider: str | None,
        extra_headers: dict[str, object] | None,
        optional_params: dict[str, object],
        timeout_seconds: float | None,
    ) -> dict[str, object]:
        raise NotImplementedError


class RustAocr(Protocol):
    def __call__(
        self,
        model: str,
        document: dict[str, object],
        api_key: str | None,
        api_base: str | None,
        custom_llm_provider: str | None,
        extra_headers: dict[str, object] | None,
        optional_params: dict[str, object],
        timeout_seconds: float | None,
    ) -> Awaitable[dict[str, object]]:
        raise NotImplementedError


class _Unset:
    pass


_UNSET: Final[_Unset] = _Unset()


_rust_ocr_impl: RustOcr | None = None
_rust_aocr_impl: RustAocr | None = None


def set_rust_ocr(
    *,
    ocr: RustOcr | None | _Unset = _UNSET,
    aocr: RustAocr | None | _Unset = _UNSET,
) -> None:
    global _rust_ocr_impl, _rust_aocr_impl
    if not isinstance(ocr, _Unset):
        _rust_ocr_impl = ocr
    if not isinstance(aocr, _Unset):
        _rust_aocr_impl = aocr


def load_rust_ocr() -> RustOcr | None:
    if _rust_ocr_impl is not None:
        return _rust_ocr_impl
    from litellm.rust_bridge import get_native_bridge

    native_bridge: Final = get_native_bridge()
    if native_bridge is None:
        return None
    return cast(RustOcr, native_bridge.ocr)


def load_rust_aocr() -> RustAocr | None:
    if _rust_aocr_impl is not None:
        return _rust_aocr_impl
    from litellm.rust_bridge import get_native_bridge

    native_bridge: Final = get_native_bridge()
    if native_bridge is None:
        return None
    return cast(RustAocr, getattr(native_bridge, "aocr", None))


def ocr(
    *,
    model: str,
    document: dict[str, object],
    api_key: str | None,
    api_base: str | None,
    custom_llm_provider: str | None,
    extra_headers: dict[str, object] | None,
    optional_params: dict[str, object],
    timeout: float | httpx.Timeout | None,
    request_url: str | None = None,
) -> dict[str, object] | None:
    rust_ocr: Final = load_rust_ocr()
    if rust_ocr is None:
        return None
    with _map_ocr_errors(request_url):
        return rust_ocr(
            model=model,
            document=document,
            api_key=api_key,
            api_base=api_base,
            custom_llm_provider=custom_llm_provider,
            extra_headers=extra_headers,
            optional_params=optional_params,
            timeout_seconds=_timeout_to_seconds(timeout),
        )


async def aocr(
    *,
    model: str,
    document: dict[str, object],
    api_key: str | None,
    api_base: str | None,
    custom_llm_provider: str | None,
    extra_headers: dict[str, object] | None,
    optional_params: dict[str, object],
    timeout: float | httpx.Timeout | None,
    request_url: str | None = None,
) -> dict[str, object] | None:
    rust_aocr: Final = load_rust_aocr()
    if rust_aocr is None:
        return None
    with _map_ocr_errors(request_url):
        return await rust_aocr(
            model=model,
            document=document,
            api_key=api_key,
            api_base=api_base,
            custom_llm_provider=custom_llm_provider,
            extra_headers=extra_headers,
            optional_params=optional_params,
            timeout_seconds=_timeout_to_seconds(timeout),
        )
