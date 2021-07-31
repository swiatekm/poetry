import re
import uuid

import httpretty
import pytest
import requests

from cleo.io.null_io import NullIO

from poetry.installation.authenticator import Authenticator


@pytest.fixture()
def mock_remote(http):
    http.register_uri(
        http.GET,
        re.compile("^https?://foo.bar/(.+?)$"),
    )


@pytest.mark.usefixtures("mock_remote")
def test_authenticator_uses_url_provided_credentials(config, http):
    config.merge(
        {
            "repositories": {"foo": {"url": "https://foo.bar/simple/"}},
            "http-basic": {"foo": {"username": "bar", "password": "baz"}},
        }
    )

    authenticator = Authenticator(config, NullIO())
    authenticator.request("get", "https://foo001:bar002@foo.bar/files/foo-0.1.0.tar.gz")

    request = http.last_request()

    assert "Basic Zm9vMDAxOmJhcjAwMg==" == request.headers["Authorization"]


@pytest.mark.usefixtures("mock_remote")
def test_authenticator_uses_credentials_from_config_if_not_provided(config, http):
    config.merge(
        {
            "repositories": {"foo": {"url": "https://foo.bar/simple/"}},
            "http-basic": {"foo": {"username": "bar", "password": "baz"}},
        }
    )

    authenticator = Authenticator(config, NullIO())
    authenticator.request("get", "https://foo.bar/files/foo-0.1.0.tar.gz")

    request = http.last_request()

    assert "Basic YmFyOmJheg==" == request.headers["Authorization"]


@pytest.mark.usefixtures("mock_remote")
def test_authenticator_uses_username_only_credentials(config, http):
    config.merge(
        {
            "repositories": {"foo": {"url": "https://foo.bar/simple/"}},
            "http-basic": {"foo": {"username": "bar", "password": "baz"}},
        }
    )

    authenticator = Authenticator(config, NullIO())
    authenticator.request("get", "https://foo001@foo.bar/files/foo-0.1.0.tar.gz")

    request = http.last_request()

    assert "Basic Zm9vMDAxOg==" == request.headers["Authorization"]


@pytest.mark.usefixtures("mock_remote")
def test_authenticator_uses_password_only_credentials(config, http):
    config.merge(
        {
            "repositories": {"foo": {"url": "https://foo.bar/simple/"}},
            "http-basic": {"foo": {"username": "bar", "password": "baz"}},
        }
    )

    authenticator = Authenticator(config, NullIO())
    authenticator.request("get", "https://:bar002@foo.bar/files/foo-0.1.0.tar.gz")

    request = http.last_request()

    assert "Basic OmJhcjAwMg==" == request.headers["Authorization"]


@pytest.mark.usefixtures("mock_remote")
def test_authenticator_uses_empty_strings_as_default_password(config, http):
    config.merge(
        {
            "repositories": {"foo": {"url": "https://foo.bar/simple/"}},
            "http-basic": {"foo": {"username": "bar"}},
        }
    )

    authenticator = Authenticator(config, NullIO())
    authenticator.request("get", "https://foo.bar/files/foo-0.1.0.tar.gz")

    request = http.last_request()

    assert "Basic YmFyOg==" == request.headers["Authorization"]


@pytest.mark.usefixtures("mock_remote")
def test_authenticator_uses_empty_strings_as_default_username(config, http):
    config.merge(
        {
            "repositories": {"foo": {"url": "https://foo.bar/simple/"}},
            "http-basic": {"foo": {"username": None, "password": "bar"}},
        }
    )

    authenticator = Authenticator(config, NullIO())
    authenticator.request("get", "https://foo.bar/files/foo-0.1.0.tar.gz")

    request = http.last_request()

    assert "Basic OmJhcg==" == request.headers["Authorization"]


@pytest.mark.usefixtures("http")
def test_authenticator_request_retries_on_exception(mocker, config):
    sleep = mocker.patch("time.sleep")
    sdist_uri = "https://foo.bar/files/{}/foo-0.1.0.tar.gz".format(str(uuid.uuid4()))
    content = str(uuid.uuid4())
    seen = list()

    def callback(request, uri, response_headers):
        if seen.count(uri) < 2:
            seen.append(uri)
            raise requests.exceptions.ConnectionError("Disconnected")
        return [200, response_headers, content]

    httpretty.register_uri(httpretty.GET, sdist_uri, body=callback)

    authenticator = Authenticator(config, NullIO())
    response = authenticator.request("get", sdist_uri)
    assert response.text == content
    assert sleep.call_count == 2


@pytest.mark.usefixtures("http")
def test_authenticator_request_raises_exception_when_attempts_exhausted(mocker, config):
    sleep = mocker.patch("time.sleep")
    sdist_uri = "https://foo.bar/files/{}/foo-0.1.0.tar.gz".format(str(uuid.uuid4()))

    def callback(*_, **__):
        raise requests.exceptions.ConnectionError(str(uuid.uuid4()))

    httpretty.register_uri(httpretty.GET, sdist_uri, body=callback)
    authenticator = Authenticator(config, NullIO())

    with pytest.raises(requests.exceptions.ConnectionError):
        authenticator.request("get", sdist_uri)

    assert sleep.call_count == 5


@pytest.mark.usefixtures("http")
@pytest.mark.parametrize(
    "status, attempts",
    [(400, 0), (401, 0), (403, 0), (404, 0), (500, 0), (502, 5), (503, 5), (504, 5)],
)
def test_authenticator_request_retries_on_status_code(mocker, config, status, attempts):
    sleep = mocker.patch("time.sleep")
    sdist_uri = "https://foo.bar/files/{}/foo-0.1.0.tar.gz".format(str(uuid.uuid4()))
    content = str(uuid.uuid4())

    def callback(request, uri, response_headers):
        return [status, response_headers, content]

    httpretty.register_uri(httpretty.GET, sdist_uri, body=callback)
    authenticator = Authenticator(config, NullIO())

    with pytest.raises(requests.exceptions.HTTPError) as excinfo:
        authenticator.request("get", sdist_uri)

    assert excinfo.value.response.status_code == status
    assert excinfo.value.response.text == content

    assert sleep.call_count == attempts


@pytest.fixture
def environment_repository_credentials(monkeypatch):
    monkeypatch.setenv("POETRY_HTTP_BASIC_FOO_USERNAME", "bar")
    monkeypatch.setenv("POETRY_HTTP_BASIC_FOO_PASSWORD", "baz")


@pytest.mark.usefixtures("environ", "mock_remote", "environment_repository_credentials")
def test_authenticator_uses_env_provided_credentials(config, http):
    config.merge({"repositories": {"foo": {"url": "https://foo.bar/simple/"}}})

    authenticator = Authenticator(config, NullIO())
    authenticator.request("get", "https://foo.bar/files/foo-0.1.0.tar.gz")

    request = http.last_request()

    assert "Basic YmFyOmJheg==" == request.headers["Authorization"]
