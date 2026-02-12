

import asyncio
from langchain_community.document_loaders import AsyncChromiumLoader
from bs4 import BeautifulSoup

async def fetch_articles():
    url = "https://pubmed.ncbi.nlm.nih.gov/?term=genai"
    loader = AsyncChromiumLoader([url])
    html = await loader.aload()

    with open('page.html', 'w', encoding='utf-8') as f:
        f.write(html[0].page_content)

    soup = BeautifulSoup(html[0].page_content, 'html.parser')
    links = []

    with open('links.txt', 'w', encoding='utf-8') as f:
        for link in soup.find_all('a', class_='docsum-title'):
            href = "https://pubmed.ncbi.nlm.nih.gov" + link['href']
            links.append(href)
            f.write(href + '\n')

    print(f"Extracted {len(links)} article links.")

# Run the async function
asyncio.run(fetch_articles())
