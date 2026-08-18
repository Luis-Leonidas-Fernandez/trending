"""Registro cooperativo de cancelación para trabajo activo del pipeline.

FastAPI puede recibir que el cliente cortó la request, pero una llamada HTTP
sincrónica ya iniciada hacia Spartan/OpenAI no se interrumpe sola. Esta capa
mantiene cierres asociados al run_id activo para que `/pipeline/cancel` pueda
cerrar sockets HTTP en vuelo y propagar la desconexión upstream.
"""

from __future__ import annotations

from contextlib import contextmanager
from contextvars import ContextVar
from threading import RLock
from typing import Callable, Iterator

_current_run_id: ContextVar[str | None] = ContextVar("pipeline_current_run_id", default=None)
_lock = RLock()
_active_closers: dict[str, list[Callable[[], None]]] = {}


@contextmanager
def pipeline_run_scope(run_id: str | None) -> Iterator[None]:
    """Expone el run_id actual a servicios internos durante una fase."""

    token = _current_run_id.set(run_id)
    try:
        yield
    finally:
        _current_run_id.reset(token)


def current_run_id() -> str | None:
    """Devuelve el run_id activo en el contexto de ejecución actual."""

    return _current_run_id.get()


@contextmanager
def registered_closer(closer: Callable[[], None], *, run_id: str | None = None) -> Iterator[None]:
    """Registra temporalmente un recurso cancelable para el run_id activo."""

    active_run_id = run_id or current_run_id()
    if not active_run_id:
        yield
        return

    with _lock:
        _active_closers.setdefault(active_run_id, []).append(closer)
    try:
        yield
    finally:
        with _lock:
            closers = _active_closers.get(active_run_id, [])
            try:
                closers.remove(closer)
            except ValueError:
                pass
            if not closers:
                _active_closers.pop(active_run_id, None)


def cancel_active_run(run_id: str | None) -> int:
    """Cierra los recursos registrados de una ejecución y devuelve cuántos intentó cerrar."""

    if not run_id:
        return 0

    with _lock:
        closers = list(_active_closers.pop(run_id, []))

    closed = 0
    for closer in closers:
        try:
            closer()
            closed += 1
        except Exception:  # noqa: BLE001 - cancelar debe ser best-effort.
            continue
    return closed
