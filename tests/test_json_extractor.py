import sys
import types
import os
import pytest

# Ensure project root is on the path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# Provide a minimal openai stub to satisfy imports in json_extractor
openai_stub = types.ModuleType("openai")
openai_stub.AzureOpenAI = object
sys.modules.setdefault("openai", openai_stub)

from extractors.json_extractor import JSONExtractor


def test_extract_json_block_with_surrounding_text():
    text = 'Hello {"foo": 1, "bar": 2} goodbye'
    result = JSONExtractor._extract_json_block(text)
    assert result == '{"foo": 1, "bar": 2}'


def test_extract_json_block_no_json():
    with pytest.raises(ValueError):
        JSONExtractor._extract_json_block('No braces here')
