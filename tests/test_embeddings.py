from app.embeddings import embed

def test_embed_returns_384_dim_vector():
    vector = embed("Italian pasta restaurant downtown")
    assert isinstance(vector, list)
    assert len(vector) == 384

def test_embed_is_deterministic():
    a = embed("spicy vegetarian curry")
    b = embed("spicy vegetarian curry")
    assert a == b
