import os
import time
import random
import asyncio
import shutil
from pathlib import Path
from dotenv import load_dotenv
from bs4 import BeautifulSoup
from fastapi import FastAPI
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel
import httpx
import logging

# ---------------- Setup ----------------
load_dotenv()

UNPAYWALL_EMAIL = os.getenv("UNPAYWALL_EMAIL")
SERP_API_KEY = os.getenv("SERP_API_KEY")
SEMANTIC_SCHOLAR_BASE = "https://api.semanticscholar.org/graph/v1"
OPENALEX_BASE = "https://api.openalex.org"
SERPAPI_URL = "https://serpapi.com/search.json"

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

app = FastAPI(title="Scholar Downloader API 🚀")

# Async client
client = httpx.AsyncClient(timeout=25.0, headers={"User-Agent": f"scholar-downloader (+{UNPAYWALL_EMAIL})"})


# ---------------- Models ----------------
class SearchRequest(BaseModel):
    names: list[str]


class DownloadRequest(BaseModel):
    pdf_urls: list[str]
    author_name: str


# ---------------- Helper ----------------
async def safe_get(url, params=None, retries=3):
    """Make a robust async HTTP GET with retry + delay."""
    for attempt in range(retries):
        try:
            r = await client.get(url, params=params)
            if r.status_code == 200:
                return r
        except Exception as e:
            logging.warning(f"Request failed ({attempt+1}/{retries}): {e}")
        await asyncio.sleep(random.uniform(0.5, 1.5) * (attempt + 1))
    return None


async def query_unpaywall(doi):
    if not doi:
        return None
    doi = doi.strip().replace("doi:", "")
    url = f"https://api.unpaywall.org/v2/{doi}"
    params = {"email": UNPAYWALL_EMAIL}
    r = await safe_get(url, params)
    if not r:
        return None
    return r.json()


async def find_pdf_for_paper(paper):
    """Try multiple PDF sources."""
    oap = paper.get("openAccessPdf")
    if oap and oap.get("url"):
        return oap["url"]

    doi = paper.get("doi")
    if doi:
        up = await query_unpaywall(doi)
        if up:
            bol = up.get("best_oa_location")
            if bol and bol.get("url_for_pdf"):
                return bol["url_for_pdf"]
            for loc in up.get("oa_locations", []):
                if loc.get("url_for_pdf"):
                    return loc["url_for_pdf"]

    return paper.get("url")


# ---------------- Search Engines ----------------
async def search_semantic_scholar(name):
    """Search papers from Semantic Scholar."""
    logging.info(f"🔎 Semantic Scholar → {name}")
    papers, offset = [], 0

    while True:
        params = {
            "query": name,
            "limit": 100,
            "offset": offset,
            "fields": "title,year,authors,doi,isOpenAccess,openAccessPdf,url"
        }
        r = await safe_get(f"{SEMANTIC_SCHOLAR_BASE}/paper/search", params)
        if not r:
            break
        data = r.json().get("data", [])
        if not data:
            break
        for p in data:
            if any(name.lower() in (a.get("name", "").lower()) for a in p.get("authors", [])):
                papers.append(p)
        if len(data) < 100:
            break
        offset += 100
        await asyncio.sleep(random.uniform(0.5, 1.2))
    return papers


async def search_openalex(name):
    """Search using OpenAlex API."""
    logging.info(f"📚 OpenAlex → {name}")
    papers, cursor = [], "*"

    while True:
        params = {"search": name, "per_page": 200, "cursor": cursor}
        r = await safe_get(f"{OPENALEX_BASE}/works", params)
        if not r:
            break
        j = r.json()
        for w in j.get("results", []):
            papers.append({
                "title": w.get("title"),
                "year": w.get("publication_year"),
                "doi": w.get("doi"),
                "url": w.get("id"),
                "openAccessPdf": {"url": w.get("open_access", {}).get("oa_url")}
            })
        cursor = j.get("meta", {}).get("next_cursor")
        if not cursor:
            break
        await asyncio.sleep(random.uniform(0.5, 1.2))
    return papers


async def search_google_scholar_serpapi(name):
    """Structured query through SerpAPI."""
    if not SERP_API_KEY:
        return []
    logging.info(f"🔍 SerpAPI → {name}")
    papers, start = [], 0

    while True:
        params = {"engine": "google_scholar", "q": name, "api_key": SERP_API_KEY, "num": 20, "start": start}
        r = await safe_get(SERPAPI_URL, params)
        if not r:
            break
        results = r.json().get("organic_results", [])
        if not results:
            break
        for res in results:
            papers.append({
                "title": res.get("title"),
                "year": res.get("publication_info", {}).get("year"),
                "doi": None,
                "url": res.get("link"),
                "openAccessPdf": {"url": res.get("link")}
            })
        start += 20
        if len(results) < 20:
            break
        await asyncio.sleep(random.uniform(0.8, 1.5))
    return papers


async def search_google_scholar_scrape(name):
    """BeautifulSoup Google Scholar scraper."""
    logging.info(f"🧠 Scraping Google Scholar → {name}")
    base_url = "https://scholar.google.com/scholar"
    query = name.replace(" ", "+")
    start, papers, seen = 0, [], set()

    while True:
        params = {"q": query, "start": start}
        r = await safe_get(base_url, params)
        if not r:
            break
        soup = BeautifulSoup(r.text, "html.parser")
        results = soup.find_all("div", class_="gs_ri")
        if not results:
            break
        for item in results:
            title_tag = item.find("h3", class_="gs_rt")
            if not title_tag:
                continue
            title = title_tag.text.strip()
            if title.lower() in seen:
                continue
            seen.add(title.lower())
            link_tag = title_tag.find("a")
            url = link_tag["href"] if link_tag else None
            year = None
            snippet = item.find("div", class_="gs_a")
            if snippet:
                for token in snippet.text.split():
                    if token.isdigit() and len(token) == 4:
                        year = token
                        break
            papers.append({
                "title": title,
                "year": year,
                "doi": None,
                "url": url,
                "openAccessPdf": {"url": url}
            })
        start += 10
        await asyncio.sleep(random.uniform(1, 2.5))
    return papers


# ---------------- Main Search ----------------
@app.post("/search")
async def search_papers(req: SearchRequest):
    results = []

    for name in req.names:
        author_data = {"Researcher": name, "papers": []}
        try:
            all_papers = []

            tasks = [
                search_semantic_scholar(name),
                search_openalex(name),
                search_google_scholar_serpapi(name) if SERP_API_KEY else search_google_scholar_scrape(name)
            ]
            sources = await asyncio.gather(*tasks)
            for s in sources:
                all_papers.extend(s)

            # Remove duplicates
            seen_titles, unique_papers = set(), []
            for p in all_papers:
                title = (p.get("title") or "").strip().lower()
                if title and title not in seen_titles:
                    seen_titles.add(title)
                    unique_papers.append(p)

            # Enrich with PDFs
            for idx, p in enumerate(unique_papers, start=1):
                pdf = await find_pdf_for_paper(p)
                author_data["papers"].append({
                    "index": idx,
                    "title": p.get("title"),
                    "year": p.get("year"),
                    "doi": p.get("doi"),
                    "pdf_url": pdf
                })
                await asyncio.sleep(0.2)

        except Exception as e:
            author_data["Error"] = str(e)
        results.append(author_data)

    return JSONResponse(content={"data": results})


# ---------------- Download ----------------
async def download_and_zip(pdf_urls, author_name):
    folder = Path(f"downloads/{author_name.replace(' ', '_')}")
    folder.mkdir(parents=True, exist_ok=True)

    for i, url in enumerate(pdf_urls):
        if not url:
            continue
        try:
            r = await safe_get(url)
            if r and "pdf" in r.headers.get("content-type", "").lower():
                with open(folder / f"paper_{i+1}.pdf", "wb") as f:
                    f.write(r.content)
        except Exception:
            continue
        await asyncio.sleep(0.3)

    zip_path = f"{folder}.zip"
    shutil.make_archive(str(folder), "zip", folder)

    # Optional cleanup (delete folder after zip)
    shutil.rmtree(folder)
    return zip_path


@app.post("/download")
async def download_pdfs(req: DownloadRequest):
    zip_path = await download_and_zip(req.pdf_urls, req.author_name)
    return FileResponse(zip_path, media_type="application/zip", filename=f"{req.author_name}.zip")


@app.get("/")
def root():
    return {"message": "Scholar Downloader API is running 🚀"}


# ---------------- Entry ----------------
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host=os.getenv("HOST", "127.0.0.1"), port=int(os.getenv("PORT", 8000)), reload=True)
