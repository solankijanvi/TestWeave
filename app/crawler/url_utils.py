from urllib.parse import urljoin, urlparse


def normalize_url(base_url: str, href: str | None) -> str | None:
    if not href:
        return None

    if href.startswith("#"):
        return None

    absolute_url = urljoin(base_url, href)

    parsed = urlparse(absolute_url)

    if parsed.scheme not in ("http", "https"):
        return None

    return absolute_url.split("#")[0]


def is_same_domain(base_url: str, target_url: str) -> bool:
    base_domain = urlparse(base_url).netloc
    target_domain = urlparse(target_url).netloc

    return base_domain == target_domain