"""Semantic HTML component rendering for the portfolio and printable CV."""

from __future__ import annotations

from html import escape
import json
from typing import Iterable

from .brand import brand_mark
from .content import (
    Article,
    CareerEntry,
    Certification,
    Education,
    Expertise,
    Impact,
    Metric,
    OpenSourceOrganisation,
    Principle,
    Profile,
    Project,
    Recognition,
    Social,
)


ICON_PATHS = {
    "github": (
        '<path d="M12 .7a11.5 11.5 0 0 0-3.64 22.4c.58.1.79-.25.79-.56v-2.23c-3.22.7-3.9-1.37-3.9-1.37-.53-1.34-1.29-1.7-1.29-1.7-1.05-.72.08-.71.08-.71 1.17.08 1.78 1.2 1.78 1.2 1.04 1.78 2.72 1.27 3.38.97.1-.75.4-1.27.74-1.56-2.57-.29-5.27-1.28-5.27-5.68 0-1.26.45-2.29 1.19-3.09-.12-.29-.52-1.46.11-3.05 0 0 .97-.31 3.17 1.18A11 11 0 0 1 12 6.12c.98 0 1.96.13 2.88.39 2.2-1.49 3.17-1.18 3.17-1.18.63 1.59.23 2.76.11 3.05.74.8 1.19 1.83 1.19 3.09 0 4.41-2.71 5.38-5.29 5.67.42.36.79 1.06.79 2.14v3.26c0 .31.21.67.8.56A11.5 11.5 0 0 0 12 .7Z"/>'
    ),
    "linkedin": (
        '<path d="M5.37 7.98H.8V22.7h4.57V7.98ZM3.09.65a2.66 2.66 0 1 0 0 5.32 2.66 2.66 0 0 0 0-5.32ZM22.7 14.26c0-4.43-2.37-6.49-5.53-6.49a4.78 4.78 0 0 0-4.34 2.39h-.06V7.98H8.39V22.7h4.57v-7.29c0-1.92.36-3.78 2.74-3.78 2.35 0 2.38 2.2 2.38 3.91v7.16h4.57l.05-8.44Z"/>'
    ),
    "medium": (
        '<path d="M2.01 5.13a.66.66 0 0 0-.22-.56L.22 2.68V2.4h6.13l4.74 10.4 4.16-10.4h5.85v.28l-1.34 1.29a.4.4 0 0 0-.15.38v15.3a.4.4 0 0 0 .15.38l1.31 1.29v.28h-6.6v-.28l1.36-1.32c.13-.13.13-.17.13-.38V7.26L12.2 21.57h-.51L7.32 7.26v10.4c-.04.28.06.57.26.77l1.77 2.15v.28h-5v-.28l1.76-2.15c.2-.2.29-.49.23-.77V5.13H2.01Zm20.12-2.73h1.65v18.46h-1.65V2.4Z"/>'
    ),
    "stackoverflow": (
        '<path d="m17.47 20.78-12.2-.01v-5.22H3.53v6.97h15.68v-6.97h-1.74v5.23ZM7 15.05l8.55 1.8.36-1.7-8.55-1.81-.36 1.7Zm1.13-4.08 7.92 3.67.73-1.58-7.92-3.67-.73 1.58Zm2.2-3.88 6.72 5.56 1.1-1.34-6.71-5.57-1.11 1.35Zm4.34-4.12-1.4 1.03 5.17 7.02 1.4-1.03-5.17-7.02ZM7 19.02h8.72v-1.74H7v1.74Z"/>'
    ),
}


def icon(name: str, class_name: str = "icon") -> str:
    """Return a decorative inline SVG from the small, local icon set."""
    path = ICON_PATHS.get(name)
    if path is None:
        return ""
    return (
        f'<svg class="{escape(class_name)}" viewBox="0 0 24 24" '
        f'aria-hidden="true" focusable="false">{path}</svg>'
    )


def external_arrow() -> str:
    return '<span aria-hidden="true">↗</span>'


def cube_rule() -> str:
    """Return a decorative cube-tick section break, reusing the shared cube glyph."""
    return (
        '<div class="section-shell cube-rule-shell">'
        '<div class="cube-rule" aria-hidden="true"><i></i><i></i><i></i></div>'
        "</div>"
    )


def tags(values: Iterable[str]) -> str:
    return "".join(f'<li class="tag">{escape(value)}</li>' for value in values)


def render_socials(socials: tuple[Social, ...], compact: bool = False) -> str:
    modifier = " social-list--compact" if compact else ""
    items = []
    for social in socials:
        detail = "" if compact else f'<span>{escape(social.handle)}</span>'
        items.append(
            '<li><a href="{url}" rel="me noopener noreferrer" '
            'target="_blank" aria-label="{label} — opens in a new tab">'
            '{icon}<span class="social-label"><strong>{label}</strong>{detail}</span>'
            "{arrow}</a></li>".format(
                url=escape(social.url, quote=True),
                label=escape(social.label, quote=True),
                icon=icon(social.icon),
                detail=detail,
                arrow=external_arrow(),
            )
        )
    return f'<ul class="social-list{modifier}">{"".join(items)}</ul>'


def render_navigation(path_prefix: str = "", cv_active: bool = False) -> str:
    links = (
        ("Work", f"{path_prefix}#work"),
        ("Expertise", f"{path_prefix}#expertise"),
        ("Writing", f"{path_prefix}#writing"),
        ("Journey", f"{path_prefix}#journey"),
    )
    nav_links = "".join(
        f'<li><a href="{escape(href, quote=True)}">{escape(label)}</a></li>'
        for label, href in links
    )
    active = ' aria-current="page"' if cv_active else ""
    cv_href = "./" if cv_active else "cv/"
    return (
        '<nav class="site-nav" id="site-navigation" aria-label="Primary">'
        f'<ul>{nav_links}<li><a class="nav-cv" href="{cv_href}"{active}>CV</a></li></ul>'
        "</nav>"
    )


def render_theme_toggle() -> str:
    return (
        '<button class="theme-toggle" type="button" aria-pressed="false" '
        'data-theme-toggle title="Use dark theme">'
        '<span class="sr-only">Dark theme</span>'
        '<svg class="theme-icon theme-icon--moon" viewBox="0 0 24 24" '
        'aria-hidden="true" focusable="false"><path '
        'd="M20.5 14.1A8.5 8.5 0 0 1 9.9 3.5a8.5 8.5 0 1 0 10.6 10.6Z"/></svg>'
        '<svg class="theme-icon theme-icon--sun" viewBox="0 0 24 24" '
        'aria-hidden="true" focusable="false"><circle cx="12" cy="12" r="3.5"/>'
        '<path d="M12 2v2m0 16v2M4.93 4.93l1.42 1.42m11.3 11.3 1.42 1.42M2 12h2m16 '
        '0h2M4.93 19.07l1.42-1.42m11.3-11.3 1.42-1.42"/></svg></button>'
    )


def render_scroll_progress() -> str:
    return '<div class="scroll-progress" data-scroll-progress aria-hidden="true"></div>'


def render_section_rail() -> str:
    """Return the desktop-only quick-navigation rail for the homepage sections."""
    links = (
        ("work", "Work"),
        ("expertise", "Expertise"),
        ("writing", "Writing"),
        ("journey", "Journey"),
    )
    items = "".join(
        '<li><a href="#{anchor}" data-rail-link>'
        '<span class="section-rail__tick" aria-hidden="true"></span>'
        '<span class="sr-only">{label}</span></a></li>'.format(
            anchor=anchor, label=escape(label)
        )
        for anchor, label in links
    )
    return (
        '<nav class="section-rail" aria-label="Section quick navigation" data-section-rail>'
        f"<ul>{items}</ul>"
        "</nav>"
    )


def render_header(path_prefix: str = "", cv_active: bool = False) -> str:
    home_href = "../" if cv_active else ("/" if path_prefix == "/" else "#top")
    return (
        f"{render_scroll_progress()}"
        '<header class="site-header" data-header>'
        '<div class="header-inner">'
        f'<a class="brand" href="{home_href}" aria-label="Marcin Cuber — home">'
        f"{brand_mark()}"
        '<span class="brand-copy"><strong>Marcin Cuber</strong>'
        '<span>Cloud / Platform</span></span></a>'
        '<div class="header-controls">'
        f'{render_theme_toggle()}'
        '<button class="nav-toggle" type="button" aria-expanded="false" '
        'aria-controls="site-navigation" data-nav-toggle>'
        '<span class="sr-only">Toggle navigation</span><span></span><span></span></button>'
        f'{render_navigation(path_prefix, cv_active)}'
        "</div></div></header>"
    )


def render_metrics(metrics: tuple[Metric, ...]) -> str:
    cards = "".join(
        '<article class="metric"><strong>{value}</strong><div><span>{label}</span>'
        '<p>{detail}</p></div></article>'.format(
            value=escape(metric.value),
            label=escape(metric.label),
            detail=escape(metric.detail),
        )
        for metric in metrics
    )
    return f'<div class="metrics-grid" aria-label="Profile at a glance">{cards}</div>'


def render_principles(principles: tuple[Principle, ...]) -> str:
    return "".join(
        '<article class="principle-card" data-reveal>'
        '<span class="principle-number">{number}</span>'
        '<h3>{title}</h3><p>{summary}</p></article>'.format(
            number=escape(principle.number),
            title=escape(principle.title),
            summary=escape(principle.summary),
        )
        for principle in principles
    )


def render_project(project: Project) -> str:
    featured_class = " project-card--featured" if project.featured else ""
    return (
        f'<article class="project-card project-card--{project.accent}{featured_class}" data-reveal>'
        '<div class="project-topline"><span>{kind}</span>'
        '<span class="project-status"><i aria-hidden="true"></i> public</span></div>'
        '<div class="project-icon" aria-hidden="true"><span></span><span></span><span></span></div>'
        '<h3>{name}</h3><code>{repository}</code><p>{description}</p>'
        '<ul class="tag-list" aria-label="Technology">{tags}</ul>'
        '<div class="project-footer"><span>{evidence}</span>'
        '<a href="{url}" target="_blank" rel="noopener noreferrer" '
        'aria-label="View {name} on GitHub — opens in a new tab">View source {arrow}</a>'
        "</div></article>"
    ).format(
        kind=escape(project.kind),
        name=escape(project.name),
        repository=escape(project.repository),
        description=escape(project.description),
        tags=tags(project.tags),
        evidence=escape(project.evidence),
        url=escape(project.url, quote=True),
        arrow=external_arrow(),
    )


def render_open_source_organisation(
    organisation: OpenSourceOrganisation,
    index: int,
) -> str:
    title_id = f"open-source-organisation-{index}"
    initials = "".join(
        word[0] for word in organisation.name.split() if word
    )[:2].upper()
    if organisation.name == "Native Cube":
        organisation_mark = (
            '<svg class="organisation-card__logo" viewBox="0 0 40 40" '
            'focusable="false">'
            '<path d="M20 2.5 36 11.3 20 20 4 11.3 20 2.5Z" fill="#2563eb"/>'
            '<path d="M4 11.3 20 20v17.5L4 28.7V11.3Z" fill="#14243b"/>'
            '<path d="M36 11.3 20 20v17.5l16-8.8V11.3Z" fill="#22a77a"/>'
            '<path d="m20 8 6 3.3-6 3.2-6-3.2L20 8Z" fill="#f2f5f9" opacity=".95"/>'
            "</svg>"
        )
    else:
        organisation_mark = escape(initials)
    module_items = "".join(
        '<li><a href="{url}" target="_blank" rel="noopener noreferrer">'
        '<span class="organisation-module__index">{index:02d}</span>'
        '<span class="organisation-module__copy"><code>{repository}</code>'
        '<span>{summary}</span></span>'
        '<span class="organisation-module__arrow" aria-hidden="true">↗</span>'
        '<span class="sr-only"> — opens on GitHub in a new tab</span>'
        "</a></li>".format(
            url=escape(module.url, quote=True),
            index=module_index,
            repository=escape(module.repository),
            summary=escape(module.summary),
        )
        for module_index, module in enumerate(organisation.modules, start=1)
    )
    module_count = len(organisation.modules)
    module_label = "Terraform module" if module_count == 1 else "Terraform modules"
    return (
        '<article class="organisation-card" aria-labelledby="{title_id}" data-reveal>'
        '<div class="organisation-card__intro">'
        '<p class="eyebrow">Open-source organisation</p>'
        '<div class="organisation-card__identity">'
        '<span class="organisation-card__mark" aria-hidden="true">{organisation_mark}</span>'
        '<div><h3 id="{title_id}"><a class="organisation-card__title-link" '
        'href="{website_url}" target="_blank" rel="noopener noreferrer">{name}'
        '<span class="sr-only"> — opens in a new tab</span></a></h3>'
        '<code>{handle}</code></div></div>'
        '<p class="organisation-card__summary">{summary}</p>'
        '<dl class="organisation-signals">'
        '<div><dt>Catalogue</dt><dd><strong>{module_count:02d}</strong> '
        "{module_label}</dd></div>"
        '<div><dt>Adoption</dt><dd>{evidence}</dd></div></dl>'
        '<div class="organisation-links">'
        '<a href="{website_url}" target="_blank" rel="noopener noreferrer">'
        'Explore the toolbox {arrow}'
        '<span class="sr-only"> — opens in a new tab</span></a>'
        '<a href="{url}" target="_blank" rel="noopener noreferrer">'
        'Explore on GitHub {arrow}<span class="sr-only"> — opens in a new tab</span></a>'
        '<a href="{registry_url}" target="_blank" rel="noopener noreferrer">'
        "Terraform Registry {arrow}"
        '<span class="sr-only"> — opens in a new tab</span></a></div></div>'
        '<div class="organisation-card__catalogue">'
        '<div class="organisation-catalogue__header">'
        '<p class="eyebrow">Reusable AWS building blocks</p>'
        '<span>AWS · Terraform · HCL</span></div>'
        '<ol class="organisation-modules" '
        'aria-label="{name} Terraform module catalogue">{module_items}</ol></div>'
        "</article>"
    ).format(
        title_id=title_id,
        organisation_mark=organisation_mark,
        name=escape(organisation.name),
        handle=escape(organisation.handle),
        summary=escape(organisation.summary),
        module_count=module_count,
        module_label=module_label,
        evidence=escape(organisation.evidence),
        website_url=escape(organisation.website_url, quote=True),
        url=escape(organisation.url, quote=True),
        registry_url=escape(organisation.registry_url, quote=True),
        arrow=external_arrow(),
        module_items=module_items,
    )


def render_expertise(item: Expertise, index: int) -> str:
    technology = "".join(f"<li>{escape(value)}</li>" for value in item.items)
    return (
        '<article class="expertise-card" data-reveal>'
        '<div class="expertise-index"><span>{index:02d}</span><i></i></div>'
        '<p class="eyebrow">{kicker}</p><h3>{title}</h3><p>{summary}</p>'
        '<ul>{technology}</ul></article>'
    ).format(
        index=index,
        kicker=escape(item.kicker),
        title=escape(item.title),
        summary=escape(item.summary),
        technology=technology,
    )


def render_impact(impact: Impact) -> str:
    return (
        '<article class="impact-card" data-reveal><strong>{value}</strong>'
        '<h3>{title}</h3><p>{summary}</p></article>'
    ).format(
        value=escape(impact.value),
        title=escape(impact.title),
        summary=escape(impact.summary),
    )


def render_article(article: Article, index: int) -> str:
    return (
        '<article class="article-card" data-reveal>'
        '<div class="article-meta"><span>{topic}</span>'
        '<time datetime="{date}">{display_date}</time></div>'
        '<span class="article-index" aria-hidden="true">{index:02d}</span>'
        '<h3><a href="{url}" target="_blank" rel="noopener noreferrer">'
        '{title} <span class="sr-only">— opens on Medium in a new tab</span></a></h3>'
        '<p>{description}</p><a class="text-link" href="{url}" target="_blank" '
        'rel="noopener noreferrer">Read article {arrow}</a></article>'
    ).format(
        topic=escape(article.topic),
        date=escape(article.date, quote=True),
        display_date=escape(article.display_date),
        index=index,
        url=escape(article.url, quote=True),
        title=escape(article.title),
        description=escape(article.description),
        arrow=external_arrow(),
    )


def render_career_entry(entry: CareerEntry) -> str:
    current = '<span class="current-marker">Current</span>' if entry.current else ""
    return (
        '<article class="timeline-entry{current_class}" data-reveal>'
        '<div class="timeline-rail"><span></span></div>'
        '<p class="timeline-period">{period}</p>'
        '<div class="timeline-copy"><div><h3>{role}</h3>{current}</div>'
        '<p class="timeline-company">{company}</p><p>{summary}</p></div></article>'
    ).format(
        current_class=" timeline-entry--current" if entry.current else "",
        period=escape(entry.period),
        role=escape(entry.role),
        current=current,
        company=escape(entry.company),
        summary=escape(entry.summary),
    )


def render_education(item: Education) -> str:
    return (
        '<article class="education-item"><p class="education-period">{period}</p>'
        '<div class="education-copy"><h4>{qualification}</h4>'
        '<p class="education-institution">{institution}</p>'
        '<p class="education-summary">{summary}</p></div></article>'
    ).format(
        period=escape(item.period),
        qualification=escape(item.qualification),
        institution=escape(item.institution),
        summary=escape(item.summary),
    )


def render_certification(item: Certification) -> str:
    return (
        '<li class="certification-item">'
        '<span class="cert-mark" aria-hidden="true">✓</span><div>'
        '<strong>{name}</strong><span>{issuer} · {group}</span></div></li>'
    ).format(
        name=escape(item.name), issuer=escape(item.issuer), group=escape(item.group)
    )


def render_recognition(item: Recognition) -> str:
    return (
        '<a class="recognition-card" href="{url}" target="_blank" '
        'rel="noopener noreferrer"><span class="recognition-arrow">{arrow}</span>'
        '<h3>{title}</h3><p>{detail}</p></a>'
    ).format(
        url=escape(item.url, quote=True),
        arrow=external_arrow(),
        title=escape(item.title),
        detail=escape(item.detail),
    )


def render_home(
    profile: Profile,
    *,
    avatar_asset: str,
    github_avatar_asset: str,
) -> str:
    site = profile.site
    projects = "".join(render_project(project) for project in profile.projects)
    open_source_organisations = "".join(
        render_open_source_organisation(organisation, index)
        for index, organisation in enumerate(
            profile.open_source_organisations,
            start=1,
        )
    )
    expertise = "".join(
        render_expertise(item, index) for index, item in enumerate(profile.expertise, 1)
    )
    impacts = "".join(render_impact(item) for item in profile.impacts)
    articles = "".join(
        render_article(item, index) for index, item in enumerate(profile.articles, 1)
    )
    career = "".join(render_career_entry(item) for item in profile.career)
    education = "".join(render_education(item) for item in profile.education)
    certifications = "".join(
        render_certification(item) for item in profile.certifications
    )
    education_count = len(profile.education)
    education_count_label = "entry" if education_count == 1 else "entries"
    certification_count = len(profile.certifications)
    certification_count_label = (
        "credential" if certification_count == 1 else "credentials"
    )
    recognition = "".join(render_recognition(item) for item in profile.recognition)
    github = next(item for item in profile.socials if item.label == "GitHub")
    linkedin = next(item for item in profile.socials if item.label == "LinkedIn")

    return f"""
<div class="hero-shell" id="top">
  {render_header()}
  <div class="hero-content">
    <section class="hero section-shell" aria-labelledby="hero-title">
      <div class="hero-copy" data-reveal>
        <p class="terminal-label"><span aria-hidden="true">$</span> whoami</p>
        <p class="hero-role">{escape(site.role)}</p>
        <h1 id="hero-title">{escape(site.headline)}</h1>
        <p class="hero-intro">{escape(site.intro)}</p>
        <div class="hero-actions">
          <a class="button button--primary" href="#work">Explore my work <span aria-hidden="true">↓</span></a>
          <a class="button button--ghost" href="{escape(linkedin.url, quote=True)}" target="_blank" rel="me noopener noreferrer">Start a conversation {external_arrow()}</a>
        </div>
      </div>
      <div class="profile-console" data-reveal>
        <div class="console-bar"><span></span><span></span><span></span><code>principal-engineer.yaml</code></div>
        <div class="console-profile">
          <a class="profile-photo-trigger" href="{escape(avatar_asset, quote=True)}" data-portrait-open aria-haspopup="dialog" aria-controls="portrait-dialog" aria-label="View larger portrait of {escape(site.name, quote=True)}">
            <img src="{escape(avatar_asset, quote=True)}" width="180" height="180" alt="Portrait of {escape(site.name, quote=True)}" decoding="async" fetchpriority="high">
            <span class="profile-photo-action" aria-hidden="true">
              <svg viewBox="0 0 24 24" focusable="false"><path d="M8 3H3v5M16 3h5v5M8 21H3v-5m18 0v5h-5"/></svg>
            </span>
          </a>
          <div><a class="availability" href="{escape(linkedin.url, quote=True)}" target="_blank" rel="me noopener noreferrer"><i aria-hidden="true"></i><span>available to connect</span><span class="availability__arrow" aria-hidden="true">↗</span><span class="sr-only"> on LinkedIn — opens in a new tab</span></a><h2>{escape(site.name)}</h2><p>{escape(site.status)}</p></div>
        </div>
        <dl class="yaml-list">
          <div><dt>focus:</dt><dd>cloud_platforms</dd></div>
          <div><dt>runtime:</dt><dd>kubernetes</dd></div>
          <div><dt>provisioner:</dt><dd>terraform</dd></div>
          <div><dt>delivery:</dt><dd>[gitops, ci/cd]</dd></div>
          <div><dt>mode:</dt><dd>hands_on + strategic</dd></div>
          <div class="yaml-list__consulting"><dt>consulting:</dt><dd class="consulting-availability"><span>{escape(site.consulting_availability)}</span></dd></div>
        </dl>
        <a class="console-link console-link--github" href="{escape(github.url, quote=True)}" target="_blank" rel="me noopener noreferrer" aria-label="Open {escape(site.name, quote=True)}’s GitHub profile in a new tab">
          <img class="github-profile-avatar" src="{escape(github_avatar_asset, quote=True)}" width="64" height="64" alt="{escape(site.name, quote=True)}’s GitHub avatar" decoding="async">
          <span class="github-identity"><span class="github-identity__label">{icon('github')} git identity</span><code>github.com/marcincuber</code></span>
          <span class="github-identity__arrow" aria-hidden="true">↗</span>
        </a>
      </div>
    </section>
    <div class="section-shell hero-metrics">{render_metrics(profile.metrics)}</div>
  </div>
</div>

<dialog class="portrait-dialog" id="portrait-dialog" data-portrait-dialog aria-labelledby="portrait-dialog-title">
  <div class="portrait-dialog__surface">
    <header class="portrait-dialog__header">
      <div><p class="terminal-label"><span aria-hidden="true">$</span> open profile_portrait</p><h2 id="portrait-dialog-title">{escape(site.name)}</h2></div>
      <button class="portrait-dialog__close" type="button" data-portrait-close aria-label="Close enlarged portrait" autofocus>
        <svg viewBox="0 0 24 24" aria-hidden="true" focusable="false"><path d="m6 6 12 12M18 6 6 18"/></svg>
      </button>
    </header>
    <figure class="portrait-dialog__figure">
      <img src="{escape(avatar_asset, quote=True)}" width="1412" height="1382" alt="Professional portrait of {escape(site.name, quote=True)}" decoding="async">
      <figcaption><code>profile://principal-cloud-engineer</code><span>{escape(site.location)}</span></figcaption>
    </figure>
  </div>
</dialog>

{render_section_rail()}

<main id="main-content">
  <section class="section section--approach" id="approach" aria-labelledby="approach-title">
    <div class="section-shell">
      <div class="section-heading section-heading--split" data-reveal>
        <div><p class="eyebrow">Engineering approach</p><h2 id="approach-title">Platforms are socio-technical systems.</h2></div>
        <p>Good infrastructure is only half the job. I align architecture, developer experience and operations so that the whole system remains understandable as it scales.</p>
      </div>
      <div class="principles-grid">{render_principles(profile.principles)}</div>
    </div>
  </section>

  {cube_rule()}

  <section class="section section--projects" id="work" aria-labelledby="work-title">
    <div class="section-shell">
      <div class="section-heading" data-reveal>
        <p class="eyebrow">Selected work / open source</p>
        <h2 id="work-title">Working systems, not logo walls.</h2>
        <p>Public implementations that show how I think about lifecycle, operability and the trade-offs behind cloud-native platforms.</p>
      </div>
      <div class="organisation-grid">{open_source_organisations}</div>
      <div class="project-grid">{projects}</div>
      <p class="section-cta" data-reveal><a class="text-link text-link--large" href="https://github.com/marcincuber?tab=repositories" target="_blank" rel="noopener noreferrer">Browse all 50+ public repositories {external_arrow()}</a></p>
    </div>
  </section>

  <section class="section section--expertise" id="expertise" aria-labelledby="expertise-title">
    <div class="section-shell">
      <div class="section-heading section-heading--split section-heading--light" data-reveal>
        <div><p class="eyebrow">Capability map</p><h2 id="expertise-title">From account boundary to running workload.</h2></div>
        <p>I work across the platform stack and the organisational interfaces around it—deep enough to debug a pod, broad enough to set the direction.</p>
      </div>
      <div class="architecture-label" aria-hidden="true"><span>Strategy</span><i></i><span>Runtime</span></div>
      <div class="expertise-grid">{expertise}</div>
    </div>
  </section>

  <section class="section section--impact" aria-labelledby="impact-title">
    <div class="section-shell">
      <div class="impact-heading" data-reveal><p class="eyebrow">Selected outcomes</p><h2 id="impact-title">Engineering measured in change.</h2><p>Representative outcomes delivered across platform engagements.</p></div>
      <div class="impact-grid">{impacts}</div>
    </div>
  </section>

  <section class="section section--writing" id="writing" aria-labelledby="writing-title">
    <div class="section-shell">
      <div class="section-heading section-heading--split" data-reveal>
        <div><p class="eyebrow">Technical writing</p><h2 id="writing-title">Field notes from operating cloud-native systems.</h2></div>
        <p>Runbooks, upgrade journeys and explanations shaped by the failure modes engineers meet in real environments.</p>
      </div>
      <div class="articles-grid">{articles}</div>
      <p class="section-cta" data-reveal><a class="text-link text-link--large" href="{escape(site.medium_url, quote=True)}" target="_blank" rel="me noopener noreferrer">Read all articles on Medium {external_arrow()}</a></p>
    </div>
  </section>

  <section class="section section--journey" id="journey" aria-labelledby="journey-title">
    <div class="section-shell journey-layout">
      <div class="journey-sticky" data-reveal>
        <p class="eyebrow">Career journey</p>
        <h2 id="journey-title">From software engineer to technical leader.</h2>
        <p>A progression from product software into the design and operation of enterprise cloud platforms.</p>
        <a class="button button--dark" href="cv/">Open the full CV <span aria-hidden="true">→</span></a>
      </div>
      <div class="timeline">{career}</div>
    </div>
  </section>

  {cube_rule()}

  <section class="section section--credentials" aria-labelledby="credentials-title">
    <div class="section-shell">
      <div class="section-heading" data-reveal><p class="eyebrow">Education & credentials</p><h2 id="credentials-title">Credentials, not just claims.</h2></div>
      <div class="credential-layout" data-reveal>
        <section class="credential-panel credential-panel--education" aria-labelledby="education-panel-title">
          <header class="credential-panel__header">
            <div><p class="eyebrow">Formal study</p><h3 id="education-panel-title">Education</h3></div>
            <span class="credential-count">
              <strong>{education_count:02d}</strong><small>{education_count_label}</small>
            </span>
          </header>
          <div class="education-list">{education}</div>
        </section>
        <section class="credential-panel credential-panel--certifications" aria-labelledby="certification-panel-title">
          <header class="credential-panel__header">
            <div><p class="eyebrow">Professional development</p><h3 id="certification-panel-title">Certifications</h3></div>
            <span class="credential-count">
              <strong>{certification_count:02d}</strong><small>{certification_count_label}</small>
            </span>
          </header>
          <ul class="certification-list">{certifications}</ul>
        </section>
      </div>
      <div class="recognition-grid" data-reveal>{recognition}</div>
    </div>
  </section>

  <section class="contact-section" id="contact" aria-labelledby="contact-title">
    <div class="section-shell contact-layout" data-reveal>
      <div><p class="eyebrow">Let’s compare notes</p><h2 id="contact-title">Architecture challenge, platform problem or open-source idea?</h2><p>The best conversations usually begin with a system diagram and one stubborn constraint.</p></div>
      <a class="button button--primary button--large" href="{escape(linkedin.url, quote=True)}" target="_blank" rel="me noopener noreferrer">Connect on LinkedIn {external_arrow()}</a>
    </div>
  </section>
</main>

<footer class="site-footer">
  <div class="section-shell footer-grid">
    <div><a class="brand brand--footer" href="#top" aria-label="{escape(site.name, quote=True)} — back to top">{brand_mark()}<span class="brand-copy"><strong>{escape(site.name)}</strong><span>{escape(site.short_role)}</span></span></a><p>Designed as an honest, inspectable account of the systems I build and how I work.</p></div>
    {render_socials(profile.socials, compact=True)}
    <p class="footer-meta">London, UK<br>Built with Python · deployed on GitHub Pages</p>
  </div>
</footer>
"""


def render_cv(profile: Profile) -> str:
    site = profile.site
    career = "".join(
        '<article class="cv-role"><div class="cv-role-heading"><div><h3>{role}</h3>'
        '<p>{company}</p></div><time>{period}</time></div><p>{summary}</p></article>'.format(
            role=escape(entry.role),
            company=escape(entry.company),
            period=escape(entry.period),
            summary=escape(entry.summary),
        )
        for entry in profile.career
    )
    expertise = "".join(
        '<section class="cv-skill"><h3>{title}</h3><p>{summary}</p><ul>{items}</ul></section>'.format(
            title=escape(item.title),
            summary=escape(item.summary),
            items="".join(f"<li>{escape(value)}</li>" for value in item.items),
        )
        for item in profile.expertise
    )
    education = "".join(
        '<article class="cv-education"><h3>{qualification}</h3><p><strong>{institution}</strong>'
        ' · {period}</p><p>{summary}</p></article>'.format(
            qualification=escape(item.qualification),
            institution=escape(item.institution),
            period=escape(item.period),
            summary=escape(item.summary),
        )
        for item in profile.education
    )
    certifications = "".join(
        '<li><strong>{name}</strong><span>{issuer}</span></li>'.format(
            name=escape(item.name), issuer=escape(item.issuer)
        )
        for item in profile.certifications
    )
    recognition = "".join(
        '<li><a href="{url}" target="_blank" rel="noopener noreferrer"><strong>{title}</strong>'
        '<span>{detail}</span></a></li>'.format(
            url=escape(item.url, quote=True),
            title=escape(item.title),
            detail=escape(item.detail),
        )
        for item in profile.recognition
    )
    contact_links = " · ".join(
        f'<a href="{escape(item.url, quote=True)}">{escape(item.label)}</a>'
        for item in profile.socials
    )
    project_links = "".join(
        '<li><a href="{url}"><strong>{name}</strong><span>{repository}</span></a></li>'.format(
            url=escape(item.url, quote=True),
            name=escape(item.name),
            repository=escape(item.repository),
        )
        for item in profile.projects[:4]
    )
    open_source_organisations = "".join(
        '<article class="cv-organisation">'
        '<div class="cv-organisation__heading"><div><h3>{name}</h3>'
        '<code>{handle}</code></div><strong>{module_count:02d} modules</strong></div>'
        '<p>{summary}</p><p class="cv-organisation__evidence">{evidence}</p>'
        '<ul class="cv-organisation__modules" '
        'aria-label="{name} Terraform modules">{modules}</ul>'
        '<p class="cv-organisation__links">'
        '<a href="{website_url}" target="_blank" rel="noopener noreferrer">'
        'Cloud-native toolbox<span class="sr-only"> — opens in a new tab</span></a>'
        ' · <a href="{url}" target="_blank" rel="noopener noreferrer">GitHub organisation'
        '<span class="sr-only"> — opens in a new tab</span></a>'
        ' · <a href="{registry_url}" target="_blank" '
        'rel="noopener noreferrer">Terraform Registry'
        '<span class="sr-only"> — opens in a new tab</span></a></p></article>'.format(
            name=escape(organisation.name),
            handle=escape(organisation.handle),
            module_count=len(organisation.modules),
            summary=escape(organisation.summary),
            evidence=escape(organisation.evidence),
            modules="".join(
                '<li><a href="{url}" target="_blank" rel="noopener noreferrer">'
                '<code>{repository}</code><span class="sr-only">'
                " — opens on GitHub in a new tab</span></a></li>".format(
                    url=escape(module.url, quote=True),
                    repository=escape(module.repository),
                )
                for module in organisation.modules
            ),
            website_url=escape(organisation.website_url, quote=True),
            url=escape(organisation.url, quote=True),
            registry_url=escape(organisation.registry_url, quote=True),
        )
        for organisation in profile.open_source_organisations
    )
    cv_profile = "".join(
        f'<p class="cv-profile-paragraph">{escape(paragraph)}</p>'
        for paragraph in site.cv_profile
    )

    return f"""
<div class="cv-shell" id="top">
  {render_header('../', cv_active=True)}
  <main id="main-content" class="cv-page">
    <header class="cv-hero">
      <div class="cv-identity">
        {brand_mark("cv-brand-mark")}
        <div class="cv-identity__copy">
          <p class="eyebrow">Curriculum vitae</p>
          <h1>{escape(site.name)}</h1>
          <p class="cv-title">{escape(site.role)}</p>
          <p class="cv-location">{escape(site.location)} · {contact_links}</p>
        </div>
      </div>
      <button class="button button--dark print-button" type="button" data-print>Print / save PDF</button>
    </header>

    <section class="cv-summary" aria-labelledby="profile-heading">
      <h2 id="profile-heading">Profile</h2><div class="cv-summary-copy">{cv_profile}</div>
    </section>

    <div class="cv-layout">
      <div class="cv-primary">
        <section class="cv-section" aria-labelledby="experience-heading"><h2 id="experience-heading">Experience</h2>{career}</section>
        <section class="cv-section" aria-labelledby="expertise-heading"><h2 id="expertise-heading">Technical expertise</h2><div class="cv-skills">{expertise}</div></section>
      </div>
      <aside class="cv-sidebar" aria-label="Additional CV information">
        <section class="cv-section" aria-labelledby="education-heading"><h2 id="education-heading">Education</h2>{education}</section>
        <section class="cv-section" aria-labelledby="certifications-heading"><h2 id="certifications-heading">Credentials earned</h2><ul class="cv-list">{certifications}</ul></section>
        <section class="cv-section" aria-labelledby="open-source-organisations-heading"><h2 id="open-source-organisations-heading">Open-source organisation</h2>{open_source_organisations}</section>
        <section class="cv-section" aria-labelledby="projects-heading"><h2 id="projects-heading">Selected open source</h2><ul class="cv-list cv-list--links">{project_links}</ul></section>
        <section class="cv-section" aria-labelledby="community-heading"><h2 id="community-heading">Community & recognition</h2><ul class="cv-list cv-list--links">{recognition}</ul></section>
      </aside>
    </div>
  </main>
  <footer class="cv-footer"><p>marcincuber.github.io · Generated from the same structured source as the portfolio.</p></footer>
</div>
"""


def render_not_found(profile: Profile) -> str:
    return f"""
<div class="not-found-shell">
  {render_header('/', cv_active=False)}
  <div class="not-found-cube" aria-hidden="true"><i></i><i></i><i></i></div>
  <main id="main-content" class="not-found">
    <p class="terminal-label"><span aria-hidden="true">$</span> kubectl get page</p>
    <p class="not-found-code" aria-hidden="true">404</p>
    <h1>That route is not in the cluster.</h1>
    <p>The page may have moved during the site rebuild. The platform is healthy; this path is not.</p>
    <a class="button button--primary" href="/">Return to the profile <span aria-hidden="true">→</span></a>
  </main>
</div>
"""


def structured_data(
    profile: Profile,
    page_url: str,
    avatar_url: str,
    *,
    page_name: str,
    page_description: str,
    page_kind: str,
) -> str:
    """Render page-specific JSON-LD without introducing templating injection."""
    if page_kind not in {"home", "cv", "not_found"}:
        raise ValueError(f"unsupported structured-data page kind: {page_kind}")

    site = profile.site
    home_url = f"{site.canonical_url}/"
    person_id = f"{site.canonical_url}/#person"
    website_id = f"{site.canonical_url}/#website"
    profile_page_id = f"{page_url}#profile-page"
    current_role = next(entry for entry in profile.career if entry.current)
    public_handle = next(
        (
            social.handle
            for social in profile.socials
            if social.handle.startswith("@")
        ),
        site.name,
    )
    knows_about = list(
        dict.fromkeys(
            [item.title for item in profile.expertise]
            + [tag for project in profile.projects for tag in project.tags]
            + [
                module.repository
                for organisation in profile.open_source_organisations
                for module in organisation.modules
            ]
        )
    )
    person = {
        "@type": "Person",
        "@id": person_id,
        "name": site.name,
        "alternateName": public_handle,
        "description": site.description,
        "jobTitle": site.role,
        "url": home_url,
        "image": avatar_url,
        "homeLocation": {"@type": "Place", "name": site.location},
        "sameAs": [social.url for social in profile.socials],
        "worksFor": {
            "@type": "Organization",
            "name": current_role.company,
        },
        "affiliation": [
            {
                "@type": "Organization",
                "name": organisation.name,
                "url": organisation.website_url,
                "description": organisation.summary,
                "sameAs": [organisation.url, organisation.registry_url],
            }
            for organisation in profile.open_source_organisations
        ],
        "alumniOf": [
            {
                "@type": "CollegeOrUniversity",
                "name": education.institution,
            }
            for education in profile.education[:1]
        ],
        "hasCredential": [
            {
                "@type": "EducationalOccupationalCredential",
                "name": certification.name,
                "credentialCategory": certification.group,
                "recognizedBy": {
                    "@type": "Organization",
                    "name": certification.issuer,
                },
            }
            for certification in profile.certifications
        ],
        "knowsAbout": knows_about,
    }
    graph: list[dict[str, object]] = []
    if page_kind == "home":
        graph.append(
            {
                "@type": "WebSite",
                "@id": website_id,
                "url": home_url,
                "name": site.name,
                "alternateName": [
                    f"{site.name} Portfolio",
                    "marcincuber.github.io",
                ],
                "description": site.description,
                "inLanguage": "en-GB",
                "publisher": {"@id": person_id},
            }
        )

    if page_kind in {"home", "cv"}:
        page: dict[str, object] = {
            "@type": "ProfilePage",
            "@id": profile_page_id,
            "url": page_url,
            "name": page_name,
            "description": page_description,
            "dateModified": site.last_updated,
            "mainEntity": {"@id": person_id},
            "isPartOf": {"@id": website_id},
            "inLanguage": "en-GB",
            "primaryImageOfPage": {
                "@type": "ImageObject",
                "url": avatar_url,
                "contentUrl": avatar_url,
                "caption": f"Portrait of {site.name}",
            },
        }
        if page_kind == "home":
            page["hasPart"] = [
                {
                    "@type": "Article",
                    "headline": article.title,
                    "description": article.description,
                    "url": article.url,
                    "datePublished": article.date,
                    "author": {"@id": person_id},
                    "inLanguage": "en-GB",
                }
                for article in profile.articles
            ]
        graph.extend((person, page))
    else:
        graph.append(
            {
                "@type": "WebPage",
                "@id": f"{page_url}#webpage",
                "url": page_url,
                "name": page_name,
                "description": page_description,
                "isPartOf": {"@id": website_id},
                "inLanguage": "en-GB",
            }
        )

    graph = {
        "@context": "https://schema.org",
        "@graph": graph,
    }
    payload = json.dumps(graph, ensure_ascii=False, separators=(",", ":"))
    return payload.replace("<", "\\u003c")
