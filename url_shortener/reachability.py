
"""
Check whether a submitted HTTP/HTTPS URL has a reachable destination.

This is an internship/demo-level reachability checker. Do not treat it
as a complete SSRF defense for a publicly deployed service.
"""

import ipaddress
import socket
from urllib.parse import urlparse

import requests


TIMEOUT_SECONDS = 5
MAX_REDIRECTS = 3


class ReachabilityError(Exception):
    """Raised when a URL cannot safely be verified as reachable."""


def _is_public_address(address):
    """Allow only globally routable IP addresses."""
    try:
        ip = ipaddress.ip_address(address.split("%")[0])
        return ip.is_global
    except ValueError:
        return False


def _check_public_destination(url):
    """
    Resolve the hostname and reject destinations resolving to non-public IPs.

    Note: requests resolves the hostname again when connecting. This separate
    check is useful for a local demo but does not fully prevent DNS rebinding.
    """
    parsed = urlparse(url)
    hostname = parsed.hostname

    if not hostname:
        raise ReachabilityError("The URL does not contain a hostname.")

    try:
        port = parsed.port
    except ValueError:
        raise ReachabilityError("The URL contains an invalid port.")

    port = port or (443 if parsed.scheme == "https" else 80)

    try:
        results = socket.getaddrinfo(
            hostname,
            port,
            type=socket.SOCK_STREAM
        )
    except (socket.gaierror, OSError):
        raise ReachabilityError(
            "The destination domain could not be resolved."
        )

    if not results:
        raise ReachabilityError(
            "The destination domain could not be resolved."
        )

    addresses = {result[4][0] for result in results}

    # Reject the hostname if ANY returned address is not public.
    if any(not _is_public_address(address) for address in addresses):
        raise ReachabilityError(
            "The destination resolves to a restricted network address."
        )


def check_url_reachable(url):
    """
    Verify that a destination responds to an HTTP request.

    Redirects are inspected manually and limited. The checker does not
    follow redirects automatically.
    """
    current_url = url

    for hop in range(MAX_REDIRECTS + 1):
        parsed = urlparse(current_url)

        if parsed.scheme not in ("http", "https") or not parsed.hostname:
            raise ReachabilityError(
                "The destination redirected to an invalid URL."
            )

        _check_public_destination(current_url)

        try:
            # GET is used instead of HEAD because many legitimate servers
            # do not support HEAD. Redirects are handled manually.
            response = requests.get(
                current_url,
                timeout=TIMEOUT_SECONDS,
                allow_redirects=False,
                stream=True,
                headers={"User-Agent": "URLShortener-Checker/1.0"},
            )
        except requests.exceptions.SSLError:
            raise ReachabilityError(
                "The destination has a TLS certificate or connection problem."
            )
        except requests.exceptions.Timeout:
            raise ReachabilityError(
                "The destination took too long to respond."
            )
        except requests.exceptions.RequestException:
            raise ReachabilityError(
                "The destination could not be reached."
            )

        try:
            status = response.status_code

            # These responses prove an HTTP server answered. A 403 or 405
            # does not mean that the website itself does not exist.
            if status in (401, 403, 405):
                return True

            # Do not automatically follow redirects. Validate every target.
            if status in (301, 302, 303, 307, 308):
                location = response.headers.get("Location")

                if not location:
                    raise ReachabilityError(
                        "The destination returned a redirect without a target."
                    )

                if hop >= MAX_REDIRECTS:
                    raise ReachabilityError(
                        "The destination redirected too many times."
                    )

                from urllib.parse import urljoin
                current_url = urljoin(current_url, location)
                continue

            # A 404 means the server is reachable, but the requested page
            # was not found. Other 4xx/5xx responses also prove that an HTTP
            # server responded, though the page may not be usable.
            if 200 <= status < 600:
                return True

            raise ReachabilityError(
                "The destination returned an unexpected HTTP response."
            )
        finally:
            response.close()

    raise ReachabilityError("The destination could not be verified.")
