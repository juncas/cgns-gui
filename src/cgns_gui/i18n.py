"""Localization utilities for the CGNS GUI."""

from __future__ import annotations

from pathlib import Path
from typing import Iterable

from PySide6.QtCore import QLibraryInfo, QLocale, QTranslator


def install_translators(app, locale: str | None = None) -> list[QTranslator]:  # noqa: ANN001
    """Install Qt translators for the requested locale.

    The function attempts to load both Qt base translations and the
    application-specific catalog from ``src/cgns_gui/translations``.
    When no translation catalog is available the UI text remains in English.
    """

    target_locale = QLocale(locale) if locale is not None else QLocale.system()
    candidates = _candidate_locales(target_locale)
    translators: list[QTranslator] = []

    qt_path = _qt_translations_path()
    translators.extend(_load_catalogs(app, qt_path, "qtbase", candidates))

    app_translations = Path(__file__).resolve().parent / "translations"
    translators.extend(_load_catalogs(app, app_translations, "cgns_gui", candidates))

    return translators


def _candidate_locales(locale: QLocale) -> list[str]:
    name = locale.name()
    candidates = [name]
    if "_" in name:
        candidates.append(name.split("_", 1)[0])
    # Fallback to English if no translation is found
    if "en" not in candidates:
        candidates.append("en")
    # Ensure uniqueness while preserving order
    seen: set[str] = set()
    ordered: list[str] = []
    for value in candidates:
        if value and value not in seen:
            ordered.append(value)
            seen.add(value)
    return ordered


def _load_catalogs(
    app,
    base_path: Path,
    prefix: str,
    candidates: Iterable[str],
) -> list[QTranslator]:  # noqa: ANN001
    translators: list[QTranslator] = []
    if not base_path.exists():
        return translators

    for candidate in candidates:
        translator = QTranslator(app)
        filename = f"{prefix}_{candidate}.qm"
        if translator.load(filename, str(base_path)):
            app.installTranslator(translator)
            translators.append(translator)
    return translators


def _qt_translations_path() -> Path:
    try:
        return Path(QLibraryInfo.path(QLibraryInfo.LibraryPath.TranslationsPath))
    except AttributeError:  # pragma: no cover - compatibility fallback
        return Path(QLibraryInfo.location(QLibraryInfo.TranslationsPath))
