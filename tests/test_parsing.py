from main import _split_token, parse_text


def test_split_token_basic():
    token = _split_token("Hello,")
    assert token is not None
    assert token.core == "Hello"
    assert token.suffix == ","
    assert token.pause_mult >= 1.4


def test_parse_text_filters_non_words():
    tokens = parse_text("*** Hello world! ***")
    assert [t.core for t in tokens] == ["Hello", "world"]
