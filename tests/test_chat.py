from app.chat import build_context, get_reply
from app.retrieval import RetrievedRestaurant


def sample_candidates():
    return [
        RetrievedRestaurant(
            name="Pasta Palace", cuisine="italian", budget="mid",
            location="downtown", dietary_tags=["vegetarian"],
            description="Fresh pasta", rating=4.5, distance=0.1,
        ),
    ]


def test_build_context_includes_candidate_fields():
    context = build_context(sample_candidates())
    assert "Pasta Palace" in context
    assert "italian" in context
    assert "mid" in context


def test_build_context_empty_candidates():
    context = build_context([])
    assert "none found" in context


class FakeMessage:
    def __init__(self, content):
        self.content = content


class FakeChoice:
    def __init__(self, content):
        self.message = FakeMessage(content)


class FakeResponse:
    def __init__(self, text):
        self.choices = [FakeChoice(text)]


class FakeCompletions:
    def create(self, **kwargs):
        assert "CANDIDATES" in kwargs["messages"][-1]["content"]
        return FakeResponse("I recommend Pasta Palace.")


class FakeChat:
    def __init__(self):
        self.completions = FakeCompletions()


class FakeClient:
    def __init__(self):
        self.chat = FakeChat()


def test_get_reply_uses_context_and_client():
    reply = get_reply([], "suggest italian food", sample_candidates(), client=FakeClient())
    assert reply == "I recommend Pasta Palace."
