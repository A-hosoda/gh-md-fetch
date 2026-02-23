"""Convert HTML to Markdown using site-specific extraction rules."""

from __future__ import annotations

import dataclasses
import re

import markdownify
from bs4 import BeautifulSoup, Tag

from md_fetch.sites.base import SiteConfig


class ConversionError(Exception):
    """Raised when HTML cannot be converted to Markdown."""


@dataclasses.dataclass(frozen=True)
class ConvertResult:
    """Result of converting HTML to Markdown."""

    title: str
    markdown: str


def _detect_language(el: Tag) -> str | None:
    """Extract language name from a ``<pre>`` element's child ``<code>`` class.

    Called by markdownify with the ``<pre>`` element.  Looks for a child
    ``<code>`` whose class matches ``language-xxx`` or ``lang-xxx`` patterns
    commonly used by syntax highlighters (Prism, Highlight.js, etc.).
    """
    code = el.find("code") if el.name == "pre" else el
    if code is None:
        return None
    classes = code.get("class") or []
    for cls in classes:
        match = re.match(r"(?:language|lang)-(\w+)", cls)
        if match:
            return match.group(1)
    return None


def convert_to_markdown(html: str, site_config: SiteConfig) -> ConvertResult:
    """Convert an HTML string to Markdown based on a site configuration.

    Args:
        html: Raw HTML string.
        site_config: Site-specific extraction rules.

    Returns:
        A ConvertResult with title and markdown body.

    Raises:
        ConversionError: If *html* is empty or the content selector matches nothing.
    """
    if not html or not html.strip():
        raise ConversionError("HTML must not be empty")

    soup = BeautifulSoup(html, "html.parser")

    # Extract content element
    content = soup.select_one(site_config.content_selector)
    if content is None:
        raise ConversionError(
            f"No element matched content_selector {site_config.content_selector!r}"
        )

    # Remove unwanted elements
    for selector in site_config.remove_selectors:
        for el in content.select(selector):
            el.decompose()

    # Extract title
    title_el = soup.select_one(site_config.title_selector)
    title = title_el.get_text(strip=True) if title_el else ""

    # Convert to Markdown
    md = markdownify.markdownify(
        str(content),
        heading_style="ATX",
        code_language_callback=_detect_language,
    )

    # Collapse 3+ consecutive blank lines into 2
    md = re.sub(r"\n{3,}", "\n\n", md)
    md = md.strip()

    return ConvertResult(title=title, markdown=md)
