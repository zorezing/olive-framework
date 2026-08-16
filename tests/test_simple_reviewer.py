import json

from olive.state.project import Project
from olive.workflow.simple_reviewer import SimpleReviewer


def make_project(**overrides):
    defaults = dict(
        name="Demo",
        goal="Print Hello, World!",
        requirements=["A file named hello.py must exist"],
        constraints=["Must be a single file"],
        path="PROJECT.md",
    )
    defaults.update(overrides)
    return Project(**defaults)


class FakeOllamaClient:
    def __init__(self, response):
        self.response = response
        self.calls = []

    def chat(self, model, system, prompt, json_mode=True, num_predict=None):
        self.calls.append(
            dict(model=model, system=system, prompt=prompt,
                 json_mode=json_mode, num_predict=num_predict)
        )
        return self.response


APPROVED_RESPONSE = json.dumps(
    {"approved": True, "findings": [], "notes": "Looks good."}
)

REJECTED_RESPONSE = json.dumps(
    {
        "approved": False,
        "findings": [{"summary": "hello.py is missing", "blocking": True}],
        "notes": "Requirement not met.",
    }
)


def test_collects_files_from_workspace(tmp_path):
    (tmp_path / "hello.py").write_text('print("Hello, World!")', encoding="utf-8")

    client = FakeOllamaClient(APPROVED_RESPONSE)
    reviewer = SimpleReviewer(workspace=tmp_path, client=client)

    reviewer.review(make_project())

    prompt = client.calls[0]["prompt"]
    assert "hello.py" in prompt
    assert "Hello, World!" in prompt


def test_skips_common_noise_directories(tmp_path):
    (tmp_path / "hello.py").write_text("print(1)", encoding="utf-8")
    (tmp_path / ".git").mkdir()
    (tmp_path / ".git" / "config").write_text("junk", encoding="utf-8")
    (tmp_path / "node_modules").mkdir()
    (tmp_path / "node_modules" / "pkg.js").write_text("junk", encoding="utf-8")

    client = FakeOllamaClient(APPROVED_RESPONSE)
    reviewer = SimpleReviewer(workspace=tmp_path, client=client)
    reviewer.review(make_project())

    prompt = client.calls[0]["prompt"]
    assert "junk" not in prompt


def test_excludes_its_own_review_output_files(tmp_path):
    (tmp_path / "hello.py").write_text("print(1)", encoding="utf-8")
    (tmp_path / "review.json").write_text('{"approved": true}', encoding="utf-8")
    (tmp_path / "review.md").write_text("# old review", encoding="utf-8")

    client = FakeOllamaClient(APPROVED_RESPONSE)
    reviewer = SimpleReviewer(workspace=tmp_path, client=client)
    reviewer.review(make_project())

    prompt = client.calls[0]["prompt"]
    assert "old review" not in prompt


def test_includes_requirements_and_constraints_in_prompt(tmp_path):
    client = FakeOllamaClient(APPROVED_RESPONSE)
    reviewer = SimpleReviewer(workspace=tmp_path, client=client)

    reviewer.review(
        make_project(
            requirements=["Must have a login page"],
            constraints=["No external database"],
        )
    )

    prompt = client.calls[0]["prompt"]
    assert "Must have a login page" in prompt
    assert "No external database" in prompt


def test_parses_approved_verdict(tmp_path):
    client = FakeOllamaClient(APPROVED_RESPONSE)
    reviewer = SimpleReviewer(workspace=tmp_path, client=client)

    result = reviewer.review(make_project())

    assert result.approved is True
    assert result.findings == []
    assert result.notes == "Looks good."


def test_parses_rejected_verdict_with_findings(tmp_path):
    client = FakeOllamaClient(REJECTED_RESPONSE)
    reviewer = SimpleReviewer(workspace=tmp_path, client=client)

    result = reviewer.review(make_project())

    assert result.approved is False
    assert len(result.findings) == 1
    assert result.findings[0].summary == "hello.py is missing"
    assert result.findings[0].blocking is True


def test_handles_markdown_fenced_response(tmp_path):
    client = FakeOllamaClient(f"```json\n{APPROVED_RESPONSE}\n```")
    reviewer = SimpleReviewer(workspace=tmp_path, client=client)

    result = reviewer.review(make_project())

    assert result.approved is True


def test_uses_json_mode_and_num_predict(tmp_path):
    client = FakeOllamaClient(APPROVED_RESPONSE)
    reviewer = SimpleReviewer(workspace=tmp_path, client=client)

    reviewer.review(make_project())

    assert client.calls[0]["json_mode"] is True
    assert client.calls[0]["num_predict"] == 2048


def test_default_model_is_qwen3_8b(tmp_path):
    reviewer = SimpleReviewer(workspace=tmp_path)

    assert reviewer.model == "qwen3:8b"


class FlakyOllamaClient:
    def __init__(self, bad_responses):
        self.bad_responses = list(bad_responses)
        self.calls = 0

    def chat(self, model, system, prompt, json_mode=True, num_predict=None):
        self.calls += 1
        if self.bad_responses:
            return self.bad_responses.pop(0)
        return APPROVED_RESPONSE


def test_retries_after_invalid_json(tmp_path):
    client = FlakyOllamaClient(bad_responses=["not json"])
    reviewer = SimpleReviewer(workspace=tmp_path, client=client, max_attempts=3)

    result = reviewer.review(make_project())

    assert client.calls == 2
    assert result.approved is True


def test_gives_up_after_max_attempts(tmp_path):
    client = FlakyOllamaClient(
        bad_responses=["not json", "still not json", "nope"]
    )
    reviewer = SimpleReviewer(workspace=tmp_path, client=client, max_attempts=3)

    result = reviewer.review(make_project())

    assert client.calls == 3
    assert result.approved is False
    assert "3 attempt" in result.findings[0].summary


def test_empty_workspace_still_produces_a_prompt(tmp_path):
    client = FakeOllamaClient(APPROVED_RESPONSE)
    reviewer = SimpleReviewer(workspace=tmp_path, client=client)

    result = reviewer.review(make_project())

    assert result.approved is True
    assert "no readable files found" in client.calls[0]["prompt"]


class RaisingThenValidOllamaClient:
    def __init__(self, exceptions):
        self.exceptions = list(exceptions)
        self.calls = 0

    def chat(self, model, system, prompt, json_mode=True, num_predict=None):
        self.calls += 1
        if self.exceptions:
            raise self.exceptions.pop(0)
        return APPROVED_RESPONSE


def test_retries_after_runtime_error(tmp_path):
    # OllamaClient.chat() raises RuntimeError for a malformed-but-received
    # response -- distinct from the RequestException family, easy to miss.
    client = RaisingThenValidOllamaClient(
        exceptions=[RuntimeError("Ollama returned an unexpected response.")]
    )
    reviewer = SimpleReviewer(workspace=tmp_path, client=client, max_attempts=3)

    result = reviewer.review(make_project())

    assert client.calls == 2
    assert result.approved is True
