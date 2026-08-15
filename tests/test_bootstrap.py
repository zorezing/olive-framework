from olive.core import Olive


def test_olive_bootstrap():
    olive = Olive()

    status = olive.status()

    assert status["name"] == "Olive Framework"
    assert status["version"] == "0.1.0"
    assert status["status"] == "ready"
