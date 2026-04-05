from src.tts_engine import chunk_text

def test_short_text_not_chunked():
    text = "Hello world."
    chunks = chunk_text(text, max_chars=500)
    assert chunks == ["Hello world."]

def test_long_text_split_at_sentence_boundary():
    text = "First sentence. Second sentence. Third sentence."
    chunks = chunk_text(text, max_chars=30)
    for chunk in chunks:
        assert len(chunk) <= 30
    assert " ".join(chunks).strip() == text.strip()

def test_no_sentence_boundary_splits_at_max():
    text = "A" * 200
    chunks = chunk_text(text, max_chars=50)
    for chunk in chunks:
        assert len(chunk) <= 50

def test_empty_text_returns_empty_list():
    assert chunk_text("", max_chars=500) == []

def test_whitespace_only_returns_empty_list():
    assert chunk_text("   \n  ", max_chars=500) == []
