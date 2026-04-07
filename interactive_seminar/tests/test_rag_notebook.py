import json
from pathlib import Path


NOTEBOOK_PATH = Path('RAG_seminar.ipynb')
RAG_REQUIREMENTS = Path('requirements_rag.txt')
README_PATH = Path('README.md')


def _load_notebook():
    return json.loads(NOTEBOOK_PATH.read_text())


def _code_sources():
    notebook = _load_notebook()
    return [''.join(cell.get('source', [])) for cell in notebook['cells'] if cell['cell_type'] == 'code']


def _all_code() -> str:
    return '\n\n'.join(_code_sources())


def test_rag_notebook_uses_colab_friendly_split_package_install_cells():
    code = _all_code()

    assert '%pip install -qU' in code
    assert 'langchain-classic==1.0.3' in code
    assert 'langchain-community==0.4.1' in code
    assert 'langchain-core==1.2.26' in code
    assert 'langchain-huggingface==1.2.1' in code
    assert 'langchain-gigachat==0.5.0' in code
    assert 'langchain-text-splitters==1.1.1' in code
    assert 'gigachat==0.2.0' in code
    assert 'pypdf==6.9.2' in code
    assert 'faiss-cpu' in code
    assert 'sentence-transformers' in code
    assert 'rank_bm25' in code
    assert 'gigachain' not in code
    assert 'pydantic==1.10.13' not in code
    assert 'playwright==1.58.0' not in code


def test_rag_notebook_uses_current_split_import_paths():
    code = _all_code()

    assert 'from langchain_huggingface import HuggingFaceEmbeddings' in code
    assert 'from langchain_text_splitters import RecursiveCharacterTextSplitter' in code
    assert 'from langchain_gigachat.chat_models import GigaChat' in code
    assert 'from langchain_community.vectorstores import FAISS' in code
    assert 'from langchain_community.retrievers import BM25Retriever' in code
    assert 'from langchain_classic.retrievers import EnsembleRetriever' in code
    assert 'from langchain_classic.chains import RetrievalQA' in code
    assert 'from langchain_classic.chains import create_retrieval_chain' in code
    assert 'from langchain_classic.chains.combine_documents import create_stuff_documents_chain' in code

    assert 'from langchain.embeddings import HuggingFaceEmbeddings' not in code
    assert 'from langchain.retrievers import BM25Retriever, EnsembleRetriever' not in code
    assert 'from langchain.vectorstores.faiss import FAISS' not in code
    assert 'from langchain.text_splitter import RecursiveCharacterTextSplitter' not in code
    assert 'from langchain.chat_models.gigachat import GigaChat' not in code
    assert 'from langchain.chains.combine_documents import create_stuff_documents_chain' not in code
    assert 'from langchain.chains import RetrievalQA' not in code
    assert 'from langchain.chains import create_retrieval_chain' not in code


def test_rag_notebook_replaces_deprecated_invoke_patterns():
    code = _all_code()

    assert 'response = llm.invoke(' in code
    assert 'bm25_retriever.invoke(q1)' in code
    assert 'response = llm(formatted_prompt.to_messages())' not in code
    assert '.get_relevant_documents(' not in code


def test_rag_requirements_follow_current_notebook_stack():
    content = RAG_REQUIREMENTS.read_text()

    assert 'langchain-classic==1.0.3' in content
    assert 'langchain-community==0.4.1' in content
    assert 'langchain-core==1.2.26' in content
    assert 'langchain-huggingface==1.2.1' in content
    assert 'langchain-gigachat==0.5.0' in content
    assert 'langchain-text-splitters==1.1.1' in content
    assert 'gigachat==0.2.0' in content
    assert 'pypdf==6.9.2' in content
    assert 'gigachain' not in content
    assert 'playwright' not in content


def test_csv_rag_section_builds_ensemble_retriever_before_qa_chain():
    notebook = _load_notebook()
    cell_source = ''.join(notebook['cells'][80]['source'])

    assert cell_source.index('ensemble_retriever = EnsembleRetriever(') < cell_source.index(
        'qa = RetrievalQA.from_chain_type('
    )


def test_rag_parser_uses_requests_and_beautifulsoup_without_playwright():
    notebook = _load_notebook()
    parser_cell = ''.join(notebook['cells'][8]['source'])
    parser_intro = ''.join(notebook['cells'][7]['source']) + '\n' + ''.join(notebook['cells'][8]['source'])

    assert 'AsyncChromiumLoader' not in parser_cell
    assert 'import requests' in parser_cell
    assert "requests.get(" in parser_cell
    assert 'BeautifulSoup' in parser_cell
    assert "soup.find_all('a', class_='docsum-title')" in parser_cell
    assert 'playwright' not in parser_intro.lower()


def test_readme_no_longer_requires_playwright_for_rag():
    readme = README_PATH.read_text()
    assert 'playwright install' not in readme
