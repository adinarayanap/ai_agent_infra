"""Unit tests for Day 12 local pre-checks."""

import json
from pathlib import Path

import pytest

from agent.validators.pre_check import (
    LocalRejectionError,
    pre_check_request,
)

FIXTURES_DIR = Path(__file__).resolve().parent.parent / "fixtures"


def load_fixture(filename: str) -> list[dict]:
    with (FIXTURES_DIR / filename).open("r", encoding="utf-8") as fixture_file:
        return json.load(fixture_file)


def test_valid_prompts_pass():
    for fixture in load_fixture("valid_prompts.json"):
        pre_check_request({"prompt": fixture["prompt_text"]})


def test_missing_body_fails():
    with pytest.raises(LocalRejectionError):
        pre_check_request(None)


def test_invalid_json_body_fails():
    with pytest.raises(LocalRejectionError):
        pre_check_request("not a dict")


def test_missing_prompt_fails():
    with pytest.raises(LocalRejectionError):
        pre_check_request({})


def test_empty_prompt_fails():
    with pytest.raises(LocalRejectionError):
        pre_check_request({"prompt": "   "})


def test_oversized_request_fails(monkeypatch):
    monkeypatch.setenv("MAX_REQUEST_SIZE_BYTES", "50")
    oversized_prompt = "Create an encrypted S3 bucket " * 10

    with pytest.raises(LocalRejectionError):
        pre_check_request({"prompt": oversized_prompt})


def test_blocked_prompts_fail():
    for fixture in load_fixture("blocked_prompts.json"):
        with pytest.raises(LocalRejectionError):
            pre_check_request({"prompt": fixture["prompt_text"]})


def test_local_rejection_does_not_call_aws(monkeypatch):
    def fail_if_called(*args, **kwargs):
        raise AssertionError("AWS client must not be called by local pre-check.")

    monkeypatch.setattr("boto3.client", fail_if_called)

    with pytest.raises(LocalRejectionError):
        pre_check_request({"prompt": "Create an EC2 instance"})
