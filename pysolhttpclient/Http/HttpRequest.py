"""
# -*- coding: utf-8 -*-
# ===============================================================================
#
# Copyright (C) 2013/2025 Laurent Labatut / Laurent Champagnac
#
#
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA
# ===============================================================================
"""
import os.path

from pysolhttpclient.Http.HttpClient import HttpClient


class HttpRequest(object):
    """
    Http client
    """

    def __init__(self):
        """
        Const
        """

        # Method
        # If none, auto-detect (post_data : POST, GET otherwise)
        # If set : GET|HEAD|OPTIONS|TRACE, or POST|PUT|PATCH|DELETE (with post_data)
        self.method = None

        # Uri
        self.uri = None

        # Post data
        self.post_data = None

        # Request headers
        self.headers = dict()

        # General timeout
        self.general_timeout_ms = 30000

        # Connection timeout
        self.connection_timeout_ms = 10000

        # Network timeout
        self.network_timeout_ms = 10000

        # Keep alive on/off
        self.keep_alive = True

        # Http concurrency
        self.http_concurrency = 8192

        # Https insecure
        self.https_insecure = True

        # Ip v6
        self.disable_ipv6 = True

        # Proxy
        self.http_proxy_host = None
        self.http_proxy_port = None

        # Socks5
        self.socks5_proxy_host = None
        self.socks5_proxy_port = None

        # Force implementation
        self.force_http_implementation = HttpClient.HTTP_IMPL_AUTO

        # Chunked, default False
        # SUPPORTED only for urllib3 implementation
        self.chunked = False

        # MTLS SUPPORT
        # NOTE : this will rely on file system load (which is bad for perf....)
        # => https://github.com/urllib3/urllib3/issues/474
        # => https://bugs.python.org/issue16487
        self.mtls_enabled = False
        self.mtls_client_key = None  # Mandatory
        self.mtls_client_crt = None  # Mandatory
        self.mtls_client_pwd = None  # Optional
        self.mtls_ca_crt = None  # Optional

    def mtls_pool_key_get(self):
        """
        Get MTLS pool key
        :return: str,None
        :return str,None
        """
        if self.mtls_enabled:
            return "MTLS_%s_%s_%s_%s" % (
                self.mtls_ca_crt,
                self.mtls_client_key,
                self.mtls_client_crt,
                len(self.mtls_client_pwd),
            )
        else:
            return None

    def mtls_status_validate(self):
        """
        Get MTLS status _mtls_status_msg and _mtls_status_ex
        :return tuple msg_status, Exception|None
        :rtype tuple
        """

        if not self.mtls_enabled:
            return

        # Notice : mtls_client_pwd and mtls_ca_crt are optional
        if self.mtls_client_key is None or self.mtls_client_crt is None:
            # Invalid
            raise Exception(
                "MTLS_INVALID_A, mtls_ca_crt=%s, mtls_client_key=%s, mtls_client_crt=%s" % (
                    "set" if self.mtls_ca_crt is not None else "unset",
                    "set" if self.mtls_client_key is not None else "unset",
                    "set" if self.mtls_client_crt is not None else "unset",
                )
            )

        # OPTIONAL
        if self.mtls_ca_crt is not None and not os.path.isfile(self.mtls_ca_crt):
            raise Exception("MTLS_FAILED (not isfile), mtls_ca_crt=%s" % self.mtls_ca_crt)
        # MANDATORY
        elif not os.path.isfile(self.mtls_client_key):
            raise Exception("MTLS_FAILED (not isfile), mtls_client_key=%s" % self.mtls_client_key)
        # MANDATORY
        elif not os.path.isfile(self.mtls_client_crt):
            raise Exception("MTLS_FAILED (not isfile), mtls_client_crt=%s" % self.mtls_client_crt)

        # MUST RUN UNDER URLLIB3
        if self.force_http_implementation == HttpClient.HTTP_IMPL_AUTO:
            self.force_http_implementation = HttpClient.HTTP_IMPL_URLLIB3
        elif self.force_http_implementation == HttpClient.HTTP_IMPL_GEVENT:
            raise Exception("MTLS_FAILED (not supported on HTTP_IMPL_GEVENT)")

    def __str__(self):
        """
        To string override
        :return: A string
        :rtype str
        """

        return "hreq:uri={0}*m={1}*pd={2}*ka={3}*cc={4}*httpsi={5}*prox={6}*socks={7}*force={8}*h={9}*to.c/n/g={10}/{11}/{12}*mtls={13}/{14}/{15}/{16}/{17}".format(
            self.uri,
            self.method,
            len(self.post_data) if self.post_data else "None",
            self.keep_alive,
            self.http_concurrency,
            self.https_insecure,
            "{0}:{1}".format(self.http_proxy_host, self.http_proxy_port),
            "{0}:{1}".format(self.socks5_proxy_host, self.socks5_proxy_port),
            self.force_http_implementation,
            self.headers,
            self.connection_timeout_ms, self.network_timeout_ms, self.general_timeout_ms,
            self.mtls_enabled,
            "y" if self.mtls_client_crt is not None else "",
            "y" if self.mtls_client_key is not None else "",
            "y" if self.mtls_client_pwd is not None else "",
            "y" if self.mtls_ca_crt is not None else "",
        )
