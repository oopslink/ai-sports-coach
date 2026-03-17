import logging
from pathlib import Path

import requests
from duckduckgo_search import DDGS

logger = logging.getLogger(__name__)


def fetch_reference_images(sport: str, output_dir: Path, max_images: int = 3) -> list[Path]:
    """Search DuckDuckGo for standard technique images and download them."""
    output_dir.mkdir(parents=True, exist_ok=True)
    query = f"{sport} standard technique professional athlete"
    downloaded: list[Path] = []

    try:
        with DDGS() as ddgs:
            results = list(ddgs.images(query, max_results=max_images * 2))
    except Exception as e:
        logger.warning(f"Reference image search failed: {e}")
        return []

    for i, result in enumerate(results):
        if len(downloaded) >= max_images:
            break
        url = result.get("image", "")
        if not url:
            continue
        dest = output_dir / f"ref_{len(downloaded) + 1:03d}.jpg"
        try:
            resp = requests.get(url, timeout=10)
            resp.raise_for_status()
            dest.write_bytes(resp.content)
            downloaded.append(dest)
        except Exception as e:
            logger.warning(f"Failed to download reference image {url}: {e}")
            continue

    return downloaded
