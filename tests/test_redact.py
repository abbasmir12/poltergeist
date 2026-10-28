"""Redaction tests — secrets must not survive into model context or logs."""

from poltergeist.safety.redact import redact_command, redact_output, redact_text

FAKE = {
    "openai": "sk-XXXXXXXXXXXXXXXXXXXX",
    "github": "ghp_XXXXXXXXXXXXXXXXXXXXXXXXXXXX",
    "aws": "AKIAIOSFODNN7EXAMPLE",
    "bearer": "Bearer eyJhbGciOiJIUzI1NiJ9.e30.abc-DEF_12345678",
}


def test_openai_key_redacted():
    out = redact_text(f"api key {FAKE['openai']} leaked")
    assert FAKE["openai"] not in out and "REDACTED" in out


def test_github_pat_redacted():
    out = redact_text(FAKE["github"])
    assert "REDACTED" in out


def test_aws_key_redacted():
    out = redact_text(FAKE["aws"])
    assert FAKE["aws"] not in out


def test_bearer_jwt_redacted():
    out = redact_text(FAKE["bearer"])
    assert "eyJhbGci" not in out


def test_env_assignment_value_redacted():
    text = "export GITHUB_TOKEN=ghp_realGhostTokenAndLongerValue123456\n"
    assert "realGhostToken" not in redact_text(text)


def test_password_assignment_redacted():
    text = "DB_PASSWORD=sup3r-haunted-value\n"
    out = redact_text(text)
    assert "sup3r" not in out and "REDACTED" in out


def test_benign_assignment_not_touched():
    text = "CSS_COLOR=marigold\n"
    assert redact_text(text) == text


def test_private_key_block_redacted():
    pem = (
        "-----BEGIN OPENSSH PRIVATE KEY-----\n"
        "b3BlbnNzaC1rZXktdjEAAAAABG5vbmVGYWtlS2V5Cg==\n"
        "-----END OPENSSH PRIVATE KEY-----\n"
    )
    out = redact_text(pem)
    assert "b3BlbnNzaC1rZXktdjEA" not in out


def test_redact_command_inline_env():
    cmd = "GITHUB_TOKEN=ghp_ZzzZzzZzzZzzZzzZzzZzzZzzZzzZzzZ poltergeist doctor"
    out = redact_command(cmd)
    assert "ghp_ZzzZzzZzzZzzZzzZzzZzzZzzZzzZzzZ" not in out
    assert "poltergeist doctor" in out


def test_redact_output_handles_yaml_and_json():
    out = redact_output('api_key: haunted-ok-api-key\ncolor: "orange"\n')
    assert "haunted-ok-api-key" not in out
    assert 'color: "orange"' in out


def test_redact_output_keeps_normal_lines():
    note = "Build succeeded. warnings: 2\ngit status clean\n"
    assert redact_output(note) == note


def test_pem_multiline_is_knocked_out():
    pem = "-----BEGIN RSA PRIVATE KEY-----\nGEIST\nGEIST2\n-----END RSA PRIVATE KEY-----\n"
    assert "GEIST" not in redact_text(pem)


def test_plain_prose_survives():
    text = "The ghost lingers in section 7.3, whispering exit codes."
    assert redact_text(text) == text


def test_all_fake_tokens_never_survive():
    combined = " ".join(FAKE.values())
    out = redact_text(combined)
    for value in FAKE.values():
        assert value not in out
    assert "REDACTED" in out
