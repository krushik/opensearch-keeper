"""
Authentication module for OpenSearch connections.
"""

import logging
from typing import Dict, Any

import boto3
from opensearchpy import RequestsHttpConnection
from requests.auth import HTTPBasicAuth

logger = logging.getLogger(__name__)


class ProxiedRequestsHttpConnection(RequestsHttpConnection):
    """Custom connection class that supports SOCKS proxy."""

    def __init__(self, proxy_config: Dict[str, Any], *args, **kwargs):
        """Initialize the proxied connection.

        :param proxy_config: Dictionary with proxy configuration.
        :param args: Additional arguments for RequestsHttpConnection.
        :param kwargs: Additional keyword arguments for RequestsHttpConnection.
        """
        super().__init__(*args, **kwargs)
        self.proxy_config = proxy_config

    def perform_request(
        self,
        method,
        url,
        params=None,
        body=None,
        timeout=None,
        allow_redirects=True,
        ignore=(),
        headers=None,
    ):
        """Perform the request through a proxy.

        :param method: HTTP method.
        :param url: URL to request.
        :param params: Query parameters.
        :param body: Request body.
        :param timeout: Request timeout.
        :param allow_redirects: Allow redirects.
        :param ignore: Status codes to ignore.
        :param headers: Request headers.
        :return: Response from the server.
        """
        proxy_host = self.proxy_config.get("host")
        proxy_port = self.proxy_config.get("port")
        proxy_username = self.proxy_config.get("username")
        proxy_password = self.proxy_config.get("password")

        proxy_url = f"socks5://{proxy_host}:{proxy_port}"
        if proxy_username and proxy_password:
            proxy_url = f"socks5://{proxy_username}:{proxy_password}@{proxy_host}:{proxy_port}"

        proxies = {
            "http": proxy_url,
            "https": proxy_url,
        }

        self.session.proxies = proxies
        return super().perform_request(
            method, url, params, body, timeout, allow_redirects, ignore, headers
        )


def create_aws_auth(region: str, service: str = "es") -> Any:
    """Create AWS SigV4 authentication for OpenSearch.

    :param region: AWS region.
    :param service: AWS service name (default: 'es').
    :return: AWS authentication object.
    """
    try:
        from opensearchpy import AWSV4SignerAuth

        credentials = boto3.Session().get_credentials()
        auth = AWSV4SignerAuth(credentials, region, service)
        logger.info(f"Created AWS SigV4 authentication for region {region}")
        return auth
    except ImportError:
        logger.error("Failed to import AWSV4SignerAuth. Make sure opensearch-py is installed.")
        raise
    except Exception as e:
        logger.error(f"Failed to create AWS authentication: {e}")
        raise


def create_basic_auth(username: str, password: str) -> HTTPBasicAuth:
    """Create HTTP Basic authentication.

    :param username: Username.
    :param password: Password.
    :return: HTTP Basic authentication object.
    """
    return HTTPBasicAuth(username, password)


def get_connection_params(env_config: Dict[str, Any]) -> Dict[str, Any]:
    """Get connection parameters for OpenSearch client.

    :param env_config: Environment configuration.
    :return: Dictionary with connection parameters.
    """
    connection_params = {
        "hosts": [{"host": env_config["host"], "port": env_config["port"]}],
        "use_ssl": env_config.get("use_ssl", True),
        "verify_certs": env_config.get("verify_certs", True),
        "connection_class": RequestsHttpConnection,
    }

    # Add AWS authentication if configured
    if "aws_auth" in env_config:
        aws_config = env_config["aws_auth"]
        auth = create_aws_auth(aws_config["region"], aws_config.get("service", "es"))
        connection_params["http_auth"] = auth

    # Add basic authentication if configured
    if "basic_auth" in env_config:
        basic_auth = env_config["basic_auth"]
        auth = create_basic_auth(basic_auth["username"], basic_auth["password"])
        connection_params["http_auth"] = auth

    # Configure proxy if specified
    if "proxy" in env_config:
        connection_params["connection_class"] = (
            lambda *args, **kwargs: ProxiedRequestsHttpConnection(
                env_config["proxy"], *args, **kwargs
            )
        )

    return connection_params
