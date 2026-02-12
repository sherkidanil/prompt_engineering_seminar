import asyncio
from bs4 import BeautifulSoup

# PubMed отдаёт список статей в HTML, поэтому сначала пробуем requests (работает без браузера)
def fetch_with_requests(url: str) -> str:
    import requests
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; rv:109.0) Gecko/20100101 Firefox/115.0",
        "Accept": "text/html,application/xhtml+xml",
    }
    r = requests.get(url, headers=headers, timeout=30)
    r.raise_for_status()
    return r.text


async def fetch_articles():
    url = "https://pubmed.ncbi.nlm.nih.gov/?term=genai"
    html_content = None

    # 1) Пробуем без браузера (подходит для Coder, Docker, CI)
    try:
        html_content = fetch_with_requests(url)
    except Exception as e:
        print(f"requests failed: {e}")

    # 2) Если не сработало — пробуем Playwright (нужен установленный chromium)
    if html_content is None:
        try:
            from langchain_community.document_loaders import AsyncChromiumLoader
            loader = AsyncChromiumLoader([url])
            docs = await loader.aload()
            html_content = docs[0].page_content
        except Exception as e:
            print(f"Playwright failed (часто в Docker/Coder без браузера): {e}")
            print("Установите: pip install playwright && playwright install chromium")
            raise

    with open("page.html", "w", encoding="utf-8") as f:
        f.write(html_content)

    soup = BeautifulSoup(html_content, "html.parser")
    links = []
    for link in soup.find_all("a", class_="docsum-title"):
        href = "https://pubmed.ncbi.nlm.nih.gov" + link.get("href", "")
        links.append(href)

    with open("links.txt", "w", encoding="utf-8") as f:
        for href in links:
            f.write(href + "\n")

    print(f"Extracted {len(links)} article links.")


if __name__ == "__main__":
    asyncio.run(fetch_articles())
