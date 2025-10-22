import os
import random
import asyncio
import shutil
import logging
from pathlib import Path
from dotenv import load_dotenv
from bs4 import BeautifulSoup
from fastapi import FastAPI
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel
import httpx

# ---------------- Setup ----------------
load_dotenv()

UNPAYWALL_EMAIL = os.getenv("UNPAYWALL_EMAIL")
SERP_API_KEY = os.getenv("SERP_API_KEY")
SEMANTIC_SCHOLAR_BASE = "https://api.semanticscholar.org/graph/v1"
OPENALEX_BASE = "https://api.openalex.org"
SERPAPI_URL = "https://serpapi.com/search.json"

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

app = FastAPI(title="Scholar Downloader API 🚀")

client = httpx.AsyncClient(
    timeout=30.0,
    headers={
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/128.0 Safari/537.36",
        "Accept-Language": "en-US,en;q=0.9",
    },
)

BLOCKED_DOMAINS = ["lww.com", "sagepub.com", "medrxiv.org"]

# ---------------- HTTP Helper ----------------
async def safe_get(url, params=None, retries=3):
    if any(domain in url for domain in BLOCKED_DOMAINS):
        logging.warning(f"⛔ Skipping blocked domain: {url}")
        return None

    for attempt in range(retries):
        try:
            r = await client.get(url, params=params, follow_redirects=True)
            if r.status_code == 200:
                return r
            elif r.status_code in [429, 500, 502, 503]:
                delay = random.uniform(2, 4)
                logging.warning(f"⚠️ {r.status_code} — retrying in {delay:.1f}s: {url}")
                await asyncio.sleep(delay)
        except Exception as e:
            logging.warning(f"⚡ {e} — retrying...")
            await asyncio.sleep(random.uniform(1, 3))
    return None

# ---------------- Models ----------------
class SearchRequest(BaseModel):
    names: list[str]

class DownloadRequest(BaseModel):
    pdf_urls: list[str]
    author_name: str

# ---------------- Helpers ----------------
async def query_unpaywall(doi):
    if not doi:
        return None
    url = f"https://api.unpaywall.org/v2/{doi.strip().replace('doi:', '')}"
    params = {"email": UNPAYWALL_EMAIL}
    r = await safe_get(url, params)
    return r.json() if r else None

async def find_pdf_for_paper(paper):
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

# ---------------- Search Functions ----------------
async def search_semantic_scholar(name):
    papers, offset = [], 0
    while True:
        params = {"query": name, "limit": 100, "offset": offset,
                  "fields": "title,year,authors,doi,isOpenAccess,openAccessPdf,url"}
        r = await safe_get(f"{SEMANTIC_SCHOLAR_BASE}/paper/search", params)
        if not r:
            break
        data = r.json().get("data", [])
        for p in data:
            if any(name.lower() in (a.get("name", "").lower()) for a in p.get("authors", [])):
                papers.append(p)
        if len(data) < 100:
            break
        offset += 100
        await asyncio.sleep(1)
    return papers

async def search_openalex(name):
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
                "openAccessPdf": {"url": w.get("open_access", {}).get("oa_url")},
            })
        cursor = j.get("meta", {}).get("next_cursor")
        if not cursor:
            break
        await asyncio.sleep(1)
    return papers

async def search_google_scholar_scrape(name):
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
            url = title_tag.find("a")["href"] if title_tag.find("a") else None
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
        await asyncio.sleep(2)
    return papers

# ---------------- Routes ----------------
@app.post("/search")
async def search_papers(req: SearchRequest):
    results = []
    for name in req.names:
        author_data = {"Researcher": name, "papers": []}
        try:
            tasks = [
                search_semantic_scholar(name),
                search_openalex(name),
                search_google_scholar_scrape(name),
            ]
            all_papers = [p for src in await asyncio.gather(*tasks) for p in src]
            seen, unique = set(), []
            for p in all_papers:
                title = (p.get("title") or "").strip().lower()
                if title and title not in seen:
                    seen.add(title)
                    unique.append(p)
            for i, p in enumerate(unique, start=1):
                pdf = await find_pdf_for_paper(p)
                author_data["papers"].append({
                    "index": i, "title": p.get("title"),
                    "year": p.get("year"), "doi": p.get("doi"),
                    "pdf_url": pdf
                })
        except Exception as e:
            author_data["Error"] = str(e)
        results.append(author_data)
    return JSONResponse(content={"data": results})

@app.post("/download")
async def download_pdfs(req: DownloadRequest):
    folder = Path(f"downloads/{req.author_name.replace(' ', '_')}")
    folder.mkdir(parents=True, exist_ok=True)
    seen_urls = set()
    for i, url in enumerate(req.pdf_urls):
        if not url or url in seen_urls:
            continue
        seen_urls.add(url)
        try:
            r = await safe_get(url)
            if r and "pdf" in r.headers.get("content-type", "").lower():
                with open(folder / f"paper_{i+1}.pdf", "wb") as f:
                    f.write(r.content)
        except Exception as e:
            logging.warning(f"Failed to download {url}: {e}")
        await asyncio.sleep(0.2)
    zip_path = f"{folder}.zip"
    shutil.make_archive(str(folder), "zip", folder)
    shutil.rmtree(folder)
    return FileResponse(zip_path, media_type="application/zip", filename=f"{req.author_name}.zip")

@app.get("/")
def root():
    return {"message": "Scholar Downloader API is running 🚀"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host=os.getenv("HOST", "0.0.0.0"), port=int(os.getenv("PORT", 8000)))
