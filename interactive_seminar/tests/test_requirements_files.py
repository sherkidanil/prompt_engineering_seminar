from pathlib import Path


ROOT_REQUIREMENTS = Path("requirements.txt")
PROMPT_REQUIREMENTS = Path("requirements_prompt_engineering.txt")
RAG_REQUIREMENTS = Path("requirements_rag.txt")
MCP_REQUIREMENTS = Path("requirements_mcp.txt")
NESTED_MCP_REQUIREMENTS = Path("Function_Calling_MCP_seminar/MCP/requirements.txt")
ROOT_README = Path("README.md")
MCP_README = Path("Function_Calling_MCP_seminar/MCP/README.md")


def test_split_requirement_files_exist():
    assert PROMPT_REQUIREMENTS.exists()
    assert RAG_REQUIREMENTS.exists()
    assert MCP_REQUIREMENTS.exists()


def test_root_requirements_aggregates_split_files():
    content = ROOT_REQUIREMENTS.read_text()
    assert "-r requirements_prompt_engineering.txt" in content
    assert "-r requirements_rag.txt" in content
    assert "-r requirements_mcp.txt" in content
    assert "gigachat" not in content


def test_nested_mcp_requirements_points_to_root_profile():
    content = NESTED_MCP_REQUIREMENTS.read_text().strip()
    assert content == "-r ../../requirements_mcp.txt"


def test_readmes_document_split_requirements():
    root_readme = ROOT_README.read_text()
    assert "requirements_prompt_engineering.txt" in root_readme
    assert "requirements_rag.txt" in root_readme
    assert "requirements_mcp.txt" in root_readme

    mcp_readme = MCP_README.read_text()
    assert "requirements_mcp.txt" in mcp_readme
