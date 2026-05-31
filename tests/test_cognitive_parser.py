import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.cognitive_parser import parse_thought_stream

def test_standard_closed():
    thought, response = parse_thought_stream("<think>thought content</think>response content")
    assert thought == "thought content"
    assert response == "response content"

def test_unclosed():
    thought, response = parse_thought_stream("<think>unclosed thought content")
    assert thought == "unclosed thought content"
    assert response == ""

def test_mixed_capitalization():
    thought, response = parse_thought_stream("<ThInK>thought</tHiNk>response")
    assert thought == "thought"
    assert response == "response"

def test_multiple_blocks():
    thought, response = parse_thought_stream("<think>thought 1</think>response 1<think>thought 2</think>response 2")
    assert thought == "thought 1thought 2"
    assert response == "response 1response 2"

def test_no_blocks():
    thought, response = parse_thought_stream("just response")
    assert thought == ""
    assert response == "just response"

if __name__ == "__main__":
    test_standard_closed()
    test_unclosed()
    test_mixed_capitalization()
    test_multiple_blocks()
    test_no_blocks()
    print("All cognitive parser unit tests PASSED!")
