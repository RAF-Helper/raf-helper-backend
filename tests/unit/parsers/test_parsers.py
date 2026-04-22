"""Unit tests for document parsers."""

import pytest
from pathlib import Path
from src.app.parsers import TextParser
from src.app.schemas.document import DocumentFormat

@pytest.fixture
def text_parser():
    return TextParser()

def test_text_parser_basic(text_parser, tmp_path):
    # Create a temporary text file
    file_content = "Hello world!\nThis is a test file."
    test_file = tmp_path / "test.txt"
    test_file.write_text(file_content, encoding="utf-8")

    # Parse the file
    artifact = text_parser.load(str(test_file))
    document = text_parser.parse(artifact, test_file.name)

    assert document.format == DocumentFormat.TXT
    assert document.filename == "test.txt"
    assert document.name == "test"
    assert len(document.document_chunks) == 1
    assert document.document_chunks[0].content == file_content

def test_text_parser_empty(text_parser, tmp_path):
    test_file = tmp_path / "empty.txt"
    test_file.write_text("", encoding="utf-8")

    artifact = text_parser.load(str(test_file))
    document = text_parser.parse(artifact, test_file.name)

    assert len(document.document_chunks) == 1
    assert document.document_chunks[0].content == ""
