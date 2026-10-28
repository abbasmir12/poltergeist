"""Config load/save roundtrip and env overrides."""

from pathlib import Path

from poltergeist.config import Config, load_config, save_config


def test_defaults():
    cfg = Config()
    assert cfg.model == "gemma3:1b"
    assert cfg.autonomy == "ask"
    assert cfg.theme == "classic"
    assert cfg.history_consent is None  # first-run asks


def test_roundtrip(tmp_path: Path):
    cfg = Config()
    cfg.model = "gemma3:4b"
    cfg.theme = "ofrenda"
    cfg.autonomy = "curious"
    cfg.intro = False
    cfg.voice = True
    cfg.history_consent = True
    cfg.extra["custom_knob"] = "spookier"
    path = tmp_path / "config.toml"
    save_config(cfg, path)

    loaded = load_config(path)
    assert loaded.model == "gemma3:4b"
    assert loaded.theme == "ofrenda"
    assert loaded.autonomy == "curious"
    assert loaded.intro is False
    assert loaded.voice is True
    assert loaded.history_consent is True
    assert loaded.extra["custom_knob"] == "spookier"


def test_env_overrides(tmp_path: Path, monkeypatch):
    save_config(Config(), tmp_path / "c.toml")
    environ = {
        "POLTERGEIST_MODEL": "gemma3:270m",
        "POLTERGEIST_OLLAMA_URL": "http://192.168.1.50:11434",
        "POLTERGEIST_THEME": "SLASHER",
        "POLTERGEIST_AUTONOMY": "curious",
    }
    cfg = load_config(tmp_path / "c.toml", environ=environ)
    assert cfg.model == "gemma3:270m"
    assert cfg.ollama_url == "http://192.168.1.50:11434"
    assert cfg.theme == "slasher"
    assert cfg.autonomy == "curious"


def test_ollama_host_env_bare_host(tmp_path, monkeypatch):
    environ = {"OLLAMA_HOST": "0.0.0.0:11434"}
    cfg = load_config(environ=environ)
    assert cfg.ollama_url == "http://0.0.0.0:11434"


def test_invalid_theme_falls_back(tmp_path):
    cfg = Config()
    cfg.theme = "neon"
    path = tmp_path / "c.toml"
    save_config(cfg, path)
    loaded = load_config(path)
    assert loaded.theme == "classic"


def test_corrupt_config_is_survivable(tmp_path):
    path = tmp_path / "c.toml"
    path.write_text("not [valid toml = = ==")
    cfg = load_config(path)
    assert cfg.model == "gemma3:1b"  # all defaults


def test_no_color_disables_flicker(tmp_path, monkeypatch):
    cfg = load_config(environ={"NO_COLOR": "1"})
    assert cfg.flicker is False
