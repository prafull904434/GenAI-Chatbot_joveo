import argparse
import os
import time
from io import StringIO
from typing import Iterable, List
from urllib.parse import urljoin, urlparse
from xml.etree import ElementTree

import numpy as np
import pandas as pd
import requests
from bs4 import BeautifulSoup
from tqdm import tqdm
import google.genai as genai
from dotenv import load_dotenv

load_dotenv(override=True)

from src.config import (
    CHUNK_OVERLAP,
    CHUNK_SIZE,
    CHUNKS_PATH,
    EMBEDDINGS_PATH,
    GITLAB_HANDBOOK_SITEMAP,
    INDEX_DIR,
    MAX_PAGES,
)
from src.config import DEFAULT_USER_AGENT
from src.utils import clean_text, split_text


def fetch_urls_from_sitemap(sitemap_url: str, timeout: int = 25) -> List[str]:
    response = requests.get(
        sitemap_url,
        timeout=timeout,
        headers={"User-Agent": DEFAULT_USER_AGENT},
    )
    response.raise_for_status()
    root = ElementTree.parse(StringIO(response.text)).getroot()
    namespace = {"sm": "http://www.sitemaps.org/schemas/sitemap/0.9"}
    urls = [node.text for node in root.findall(".//sm:loc", namespace) if node.text]
    return urls


def crawl_direction_urls(
    seed_url: str = "https://about.gitlab.com/direction/",
    max_urls: int = 60,
    timeout: int = 25,
) -> List[str]:
    response = requests.get(
        seed_url,
        timeout=timeout,
        headers={"User-Agent": DEFAULT_USER_AGENT},
    )
    response.raise_for_status()
    soup = BeautifulSoup(response.text, "lxml")

    urls = [seed_url]
    seen = {seed_url}
    for anchor in soup.select("a[href]"):
        href = anchor.get("href", "").strip()
        if not href:
            continue
        absolute = urljoin(seed_url, href)
        parsed = urlparse(absolute)
        normalized = f"{parsed.scheme}://{parsed.netloc}{parsed.path}"
        if normalized.startswith("https://about.gitlab.com/direction/") and normalized not in seen:
            seen.add(normalized)
            urls.append(normalized)
        if len(urls) >= max_urls:
            break
    return urls


def extract_page_text(url: str, timeout: int = 25) -> str:
    html = requests.get(
        url,
        timeout=timeout,
        headers={"User-Agent": DEFAULT_USER_AGENT}
    ).text

    soup = BeautifulSoup(html, "lxml")

    removable = {"script", "style", "noscript", "header", "footer"}
    for node in list(soup.find_all(removable)):
        node.extract()

    content_root = next(
        (soup.find(tag) for tag in ("main", "article") if soup.find(tag)),
        soup.body
    )

    if content_root is None:
        return ""

    text = content_root.get_text(" ", strip=True)
    return clean_text(text)

def filter_useful_urls(urls: Iterable[str]) -> List[str]:
    blocked_parts = ("/tags/", "/page/", "/author/", ".xml")
    valid_prefixes = (
        "https://about.gitlab.com/direction/",
        "https://handbook.gitlab.com/",
    )

    filtered = []

    for link in urls:
        if not link.startswith(valid_prefixes):
            continue

        if any(part in link for part in blocked_parts):
            continue

        filtered.append(link)

# remove duplicates while preserving order
    seen = set()
    unique_urls = []
    for link in filtered:
        if link not in seen:
            seen.add(link)
            unique_urls.append(link)

    return unique_urls


def build_dataset(max_pages: int) -> pd.DataFrame:
    handbook = fetch_urls_from_sitemap(GITLAB_HANDBOOK_SITEMAP)
    direction = crawl_direction_urls()

    all_urls = filter_useful_urls([*handbook, *direction])[:max_pages]

    records = []
  # scrape + chunk each page
    for page_url in tqdm(all_urls, desc="Ingesting pages"):
        try:
            page_text = extract_page_text(page_url)

            if len(page_text) < 250:
                continue

            chunks = split_text(page_text, CHUNK_SIZE, CHUNK_OVERLAP)

            for i, chunk_text in enumerate(chunks):
                records.append({
                    "url": page_url,
                    "chunk_id": i,
                    "content": chunk_text,
                })

        except Exception:
            continue

    return pd.DataFrame.from_records(records)


def build_index(df: pd.DataFrame) -> None:
    INDEX_DIR.mkdir(parents=True, exist_ok=True)
    df.to_csv(CHUNKS_PATH, index=False)

    api_key = os.getenv("GEMINI_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError("Missing GEMINI_API_KEY for embedding.")

    contents = df["content"].tolist()
    all_embeddings = []

    batch_size = 100
    endpoint = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-embedding-2:batchEmbedContents?key={api_key}"

# batch embedding generation
    for start in tqdm(range(0, len(contents), batch_size), desc="Generating embeddings"):
        batch = contents[start:start + batch_size]

        payload = {
            "requests": [
                {
                    "model": "models/gemini-embedding-2",
                    "taskType": "RETRIEVAL_DOCUMENT",
                    "content": {"parts": [{"text": text}]},
                }
                for text in batch
            ]
        }

        for attempt in range(10):
            response = requests.post(endpoint, json=payload)

            if response.status_code == 200:
                data = response.json()
                all_embeddings.extend(
                    emb["values"] for emb in data.get("embeddings", [])
                )
                break

            if response.status_code == 429:
                msg = response.json().get("error", {}).get("message", "").lower()

                if any(x in msg for x in ("per day", "rpd", "1500")):
                    raise RuntimeError("Daily rate limit exhausted. Try again later.")

                time.sleep(60)
                continue

            if attempt == 9:
                raise RuntimeError(f"Embedding API failed: {response.text}")

            time.sleep(2 ** attempt)

    np.save(EMBEDDINGS_PATH, np.array(all_embeddings, dtype=np.float32))



def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--max-pages",
        type=int,
        default=MAX_PAGES,
        help="limit how many pages to ingest (useful for quick runs)",
    )

    args = parser.parse_args()

    print(f"starting ingestion (max_pages={args.max_pages})...")

    df = build_dataset(args.max_pages)

    if df.empty:
        raise RuntimeError(
            "no content collected. try increasing --max-pages or check the sources."
        )

    print(f"collected {len(df)} chunks, building index...")

    build_index(df)

    unique_pages = df["url"].nunique()
    print(f"done. indexed {len(df)} chunks from {unique_pages} pages.")


if __name__ == "__main__":
    main()