"""Typed content loading and validation.

The public profile is deliberately stored outside the templates.  This keeps the
HTML, the printable CV and structured metadata on one consistent source of truth.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
import json
from pathlib import Path
from typing import Any, Callable, Mapping, TypeVar
from urllib.parse import urlparse


class ContentError(ValueError):
    """Raised when profile content is incomplete or unsafe to render."""


Record = Mapping[str, Any]
T = TypeVar("T")


def _text(record: Record, key: str, context: str) -> str:
    value = record.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ContentError(f"{context}.{key} must be a non-empty string")
    return value.strip()


def _boolean(record: Record, key: str, context: str) -> bool:
    value = record.get(key)
    if not isinstance(value, bool):
        raise ContentError(f"{context}.{key} must be a boolean")
    return value


def _text_list(record: Record, key: str, context: str) -> tuple[str, ...]:
    value = record.get(key)
    if not isinstance(value, list) or not value:
        raise ContentError(f"{context}.{key} must be a non-empty list")
    if any(not isinstance(item, str) or not item.strip() for item in value):
        raise ContentError(f"{context}.{key} must contain only non-empty strings")
    return tuple(item.strip() for item in value)


def _url(record: Record, key: str, context: str) -> str:
    value = _text(record, key, context)
    parsed = urlparse(value)
    if parsed.scheme != "https" or not parsed.netloc:
        raise ContentError(f"{context}.{key} must be an absolute HTTPS URL")
    return value


def _asset_name(record: Record, key: str, context: str) -> str:
    value = _text(record, key, context)
    if Path(value).name != value or value in {".", ".."}:
        raise ContentError(f"{context}.{key} must be a local asset filename")
    if Path(value).suffix.lower() not in {".avif", ".jpeg", ".jpg", ".png", ".webp"}:
        raise ContentError(f"{context}.{key} must use a supported image format")
    return value


def _section(
    data: Record,
    key: str,
    factory: Callable[[Record, str], T],
) -> tuple[T, ...]:
    raw = data.get(key)
    if not isinstance(raw, list) or not raw:
        raise ContentError(f"{key} must be a non-empty list")
    result: list[T] = []
    for index, item in enumerate(raw):
        if not isinstance(item, dict):
            raise ContentError(f"{key}[{index}] must be an object")
        result.append(factory(item, f"{key}[{index}]"))
    return tuple(result)


def _record_list(
    record: Record,
    key: str,
    context: str,
    factory: Callable[[Record, str], T],
) -> tuple[T, ...]:
    raw = record.get(key)
    nested_context = f"{context}.{key}"
    if not isinstance(raw, list) or not raw:
        raise ContentError(f"{nested_context} must be a non-empty list")
    result: list[T] = []
    for index, item in enumerate(raw):
        if not isinstance(item, dict):
            raise ContentError(f"{nested_context}[{index}] must be an object")
        result.append(factory(item, f"{nested_context}[{index}]"))
    return tuple(result)


@dataclass(frozen=True)
class SiteIdentity:
    canonical_url: str
    last_updated: str
    name: str
    role: str
    short_role: str
    location: str
    headline: str
    description: str
    intro: str
    cv_profile: tuple[str, ...]
    status: str
    consulting_availability: str
    avatar_asset: str
    github_avatar_asset: str
    medium_url: str

    @classmethod
    def from_record(cls, record: Record, context: str = "site") -> SiteIdentity:
        last_updated = _text(record, "last_updated", context)
        try:
            date.fromisoformat(last_updated)
        except ValueError as error:
            raise ContentError(
                f"{context}.last_updated must use YYYY-MM-DD"
            ) from error
        return cls(
            canonical_url=_url(record, "canonical_url", context).rstrip("/"),
            last_updated=last_updated,
            name=_text(record, "name", context),
            role=_text(record, "role", context),
            short_role=_text(record, "short_role", context),
            location=_text(record, "location", context),
            headline=_text(record, "headline", context),
            description=_text(record, "description", context),
            intro=_text(record, "intro", context),
            cv_profile=_text_list(record, "cv_profile", context),
            status=_text(record, "status", context),
            consulting_availability=_text(
                record,
                "consulting_availability",
                context,
            ),
            avatar_asset=_asset_name(record, "avatar_asset", context),
            github_avatar_asset=_asset_name(
                record,
                "github_avatar_asset",
                context,
            ),
            medium_url=_url(record, "medium_url", context),
        )


@dataclass(frozen=True)
class Social:
    label: str
    url: str
    handle: str
    icon: str

    @classmethod
    def from_record(cls, record: Record, context: str) -> Social:
        return cls(
            label=_text(record, "label", context),
            url=_url(record, "url", context),
            handle=_text(record, "handle", context),
            icon=_text(record, "icon", context),
        )


@dataclass(frozen=True)
class Metric:
    value: str
    label: str
    detail: str

    @classmethod
    def from_record(cls, record: Record, context: str) -> Metric:
        return cls(*(_text(record, key, context) for key in ("value", "label", "detail")))


@dataclass(frozen=True)
class Principle:
    number: str
    title: str
    summary: str

    @classmethod
    def from_record(cls, record: Record, context: str) -> Principle:
        return cls(*(_text(record, key, context) for key in ("number", "title", "summary")))


@dataclass(frozen=True)
class Project:
    name: str
    repository: str
    kind: str
    description: str
    evidence: str
    url: str
    tags: tuple[str, ...]
    accent: str
    featured: bool

    @classmethod
    def from_record(cls, record: Record, context: str) -> Project:
        accent = _text(record, "accent", context)
        if accent not in {"lime", "cyan", "violet", "orange", "rose", "blue"}:
            raise ContentError(f"{context}.accent uses an unsupported colour token")
        return cls(
            name=_text(record, "name", context),
            repository=_text(record, "repository", context),
            kind=_text(record, "kind", context),
            description=_text(record, "description", context),
            evidence=_text(record, "evidence", context),
            url=_url(record, "url", context),
            tags=_text_list(record, "tags", context),
            accent=accent,
            featured=_boolean(record, "featured", context),
        )


@dataclass(frozen=True)
class OpenSourceModule:
    repository: str
    summary: str
    url: str

    @classmethod
    def from_record(cls, record: Record, context: str) -> OpenSourceModule:
        return cls(
            repository=_text(record, "repository", context),
            summary=_text(record, "summary", context),
            url=_url(record, "url", context),
        )


@dataclass(frozen=True)
class OpenSourceOrganisation:
    name: str
    handle: str
    summary: str
    evidence: str
    website_url: str
    url: str
    registry_url: str
    modules: tuple[OpenSourceModule, ...]

    @classmethod
    def from_record(cls, record: Record, context: str) -> OpenSourceOrganisation:
        return cls(
            name=_text(record, "name", context),
            handle=_text(record, "handle", context),
            summary=_text(record, "summary", context),
            evidence=_text(record, "evidence", context),
            website_url=_url(record, "website_url", context),
            url=_url(record, "url", context),
            registry_url=_url(record, "registry_url", context),
            modules=_record_list(
                record,
                "modules",
                context,
                OpenSourceModule.from_record,
            ),
        )


@dataclass(frozen=True)
class Expertise:
    kicker: str
    title: str
    summary: str
    items: tuple[str, ...]

    @classmethod
    def from_record(cls, record: Record, context: str) -> Expertise:
        return cls(
            kicker=_text(record, "kicker", context),
            title=_text(record, "title", context),
            summary=_text(record, "summary", context),
            items=_text_list(record, "items", context),
        )


@dataclass(frozen=True)
class Impact:
    value: str
    title: str
    summary: str

    @classmethod
    def from_record(cls, record: Record, context: str) -> Impact:
        return cls(*(_text(record, key, context) for key in ("value", "title", "summary")))


@dataclass(frozen=True)
class Article:
    title: str
    date: str
    display_date: str
    topic: str
    description: str
    url: str

    @classmethod
    def from_record(cls, record: Record, context: str) -> Article:
        published = _text(record, "date", context)
        try:
            date.fromisoformat(published)
        except ValueError as error:
            raise ContentError(f"{context}.date must use YYYY-MM-DD") from error
        return cls(
            title=_text(record, "title", context),
            date=published,
            display_date=_text(record, "display_date", context),
            topic=_text(record, "topic", context),
            description=_text(record, "description", context),
            url=_url(record, "url", context),
        )


@dataclass(frozen=True)
class CareerEntry:
    period: str
    role: str
    company: str
    summary: str
    current: bool

    @classmethod
    def from_record(cls, record: Record, context: str) -> CareerEntry:
        return cls(
            period=_text(record, "period", context),
            role=_text(record, "role", context),
            company=_text(record, "company", context),
            summary=_text(record, "summary", context),
            current=_boolean(record, "current", context),
        )


@dataclass(frozen=True)
class Education:
    period: str
    qualification: str
    institution: str
    summary: str

    @classmethod
    def from_record(cls, record: Record, context: str) -> Education:
        return cls(
            *(
                _text(record, key, context)
                for key in ("period", "qualification", "institution", "summary")
            )
        )


@dataclass(frozen=True)
class Certification:
    name: str
    issuer: str
    group: str

    @classmethod
    def from_record(cls, record: Record, context: str) -> Certification:
        return cls(*(_text(record, key, context) for key in ("name", "issuer", "group")))


@dataclass(frozen=True)
class Recognition:
    title: str
    detail: str
    url: str

    @classmethod
    def from_record(cls, record: Record, context: str) -> Recognition:
        return cls(
            title=_text(record, "title", context),
            detail=_text(record, "detail", context),
            url=_url(record, "url", context),
        )


@dataclass(frozen=True)
class Profile:
    site: SiteIdentity
    socials: tuple[Social, ...]
    metrics: tuple[Metric, ...]
    principles: tuple[Principle, ...]
    projects: tuple[Project, ...]
    open_source_organisations: tuple[OpenSourceOrganisation, ...]
    expertise: tuple[Expertise, ...]
    impacts: tuple[Impact, ...]
    articles: tuple[Article, ...]
    career: tuple[CareerEntry, ...]
    education: tuple[Education, ...]
    certifications: tuple[Certification, ...]
    recognition: tuple[Recognition, ...]

    @classmethod
    def load(cls, path: Path) -> Profile:
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
        except FileNotFoundError as error:
            raise ContentError(f"content file does not exist: {path}") from error
        except json.JSONDecodeError as error:
            raise ContentError(f"invalid JSON in {path}: {error}") from error
        if not isinstance(raw, dict):
            raise ContentError("content root must be an object")
        site_raw = raw.get("site")
        if not isinstance(site_raw, dict):
            raise ContentError("site must be an object")
        profile = cls(
            site=SiteIdentity.from_record(site_raw),
            socials=_section(raw, "socials", Social.from_record),
            metrics=_section(raw, "metrics", Metric.from_record),
            principles=_section(raw, "principles", Principle.from_record),
            projects=_section(raw, "projects", Project.from_record),
            open_source_organisations=_section(
                raw,
                "open_source_organisations",
                OpenSourceOrganisation.from_record,
            ),
            expertise=_section(raw, "expertise", Expertise.from_record),
            impacts=_section(raw, "impacts", Impact.from_record),
            articles=_section(raw, "articles", Article.from_record),
            career=_section(raw, "career", CareerEntry.from_record),
            education=_section(raw, "education", Education.from_record),
            certifications=_section(raw, "certifications", Certification.from_record),
            recognition=_section(raw, "recognition", Recognition.from_record),
        )
        profile.validate()
        return profile

    def validate(self) -> None:
        """Check cross-record invariants that local field validation cannot see."""
        if sum(project.featured for project in self.projects) < 3:
            raise ContentError("at least three projects must be featured")
        if sum(entry.current for entry in self.career) != 1:
            raise ContentError("career must contain exactly one current role")
        if list(self.articles) != sorted(
            self.articles, key=lambda article: article.date, reverse=True
        ):
            raise ContentError("articles must be ordered newest first")
        self._ensure_unique("project repository", (item.repository for item in self.projects))
        self._ensure_unique(
            "open-source organisation URL",
            (item.url for item in self.open_source_organisations),
        )
        self._ensure_unique(
            "open-source organisation website URL",
            (item.website_url for item in self.open_source_organisations),
        )
        self._ensure_unique(
            "open-source organisation handle",
            (item.handle for item in self.open_source_organisations),
        )
        self._ensure_unique(
            "open-source Registry URL",
            (item.registry_url for item in self.open_source_organisations),
        )
        self._ensure_unique(
            "open-source module URL",
            (
                module.url
                for organisation in self.open_source_organisations
                for module in organisation.modules
            ),
        )
        self._ensure_unique(
            "open-source module repository",
            (
                module.repository
                for organisation in self.open_source_organisations
                for module in organisation.modules
            ),
        )
        self._ensure_unique("article URL", (item.url for item in self.articles))
        self._ensure_unique("social label", (item.label for item in self.socials))

    @staticmethod
    def _ensure_unique(label: str, values: Any) -> None:
        materialised = tuple(values)
        if len(materialised) != len(set(materialised)):
            raise ContentError(f"duplicate {label} values are not allowed")
