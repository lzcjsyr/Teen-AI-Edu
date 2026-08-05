from pathlib import Path
import sys


SCRIPT_DIR = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPT_DIR))

import generate_seedream_images as seedream  # noqa: E402


def test_load_env_reads_project_env_without_overriding_existing_environment(tmp_path, monkeypatch):
    env_path = tmp_path / ".env"
    env_path.write_text(
        "\n".join(
            [
                "ARK_API_KEY=from-env-file",
                "ARK_MODEL=from-env-file-model",
                "ARK_ENDPOINT=https://example.test/images",
            ]
        ),
        encoding="utf-8",
    )

    monkeypatch.setenv("ARK_API_KEY", "from-shell")
    monkeypatch.delenv("ARK_MODEL", raising=False)
    monkeypatch.delenv("ARK_ENDPOINT", raising=False)

    seedream.load_env_file(env_path)

    config = seedream.load_seedream_config(env_path)

    assert config.api_key == "from-shell"
    assert config.model == "from-env-file-model"
    assert config.endpoint == "https://example.test/images"


def test_load_seedream_config_requires_api_key(tmp_path, monkeypatch):
    env_path = tmp_path / ".env"
    env_path.write_text("ARK_MODEL=test-model\n", encoding="utf-8")

    monkeypatch.delenv("ARK_API_KEY", raising=False)

    try:
        seedream.load_seedream_config(env_path)
    except RuntimeError as error:
        assert "ARK_API_KEY" in str(error)
    else:
        raise AssertionError("Expected missing ARK_API_KEY to raise RuntimeError.")
