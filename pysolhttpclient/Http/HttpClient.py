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

import logging
from ssl import CERT_NONE
from threading import Lock

import gevent
import urllib3
from gevent.timeout import Timeout
from geventhttpclient.client import PROTO_HTTPS, HTTPClient, METHOD_GET
from geventhttpclient.url import URL
from pysolbase.SolBase import SolBase
from urllib3 import PoolManager, ProxyManager, Retry

from pysolhttpclient.Http.HttpResponse import HttpResponse

logger = logging.getLogger(__name__)

# Suppress warnings
urllib3.disable_warnings()


class HttpClient(object):
    """
    Http client
    """

    HTTP_IMPL_AUTO = None
    HTTP_IMPL_GEVENT = 1
    HTTP_IMPL_URLLIB3 = 3

    def __init__(self):
        """
        Const
        """

        # Gevent
        self._gevent_pool_max = 1024
        self._gevent_locker = Lock()
        self._gevent_pool = dict()

        # urllib3
        # Force underlying fifo queue to 1024 via maxsize
        self._u3_basic_pool_https_assert_off = PoolManager(num_pools=1024, maxsize=1024, assert_hostname=False, cert_reqs=CERT_NONE)
        self._u3_basic_pool_assert_on = PoolManager(num_pools=1024, maxsize=1024)
        self._u3_proxy_pool_max = 1024
        self._u3_proxy_locker = Lock()
        self._u3_proxy_pool = dict()

    # ====================================
    # GEVENT HTTP POOL
    # ====================================

    def gevent_from_pool(self, url, http_request):
        """
        Get a gevent client from url and request
        :param url: geventhttpclient.url.URL
        :type url: geventhttpclient.url.URL
        :param http_request: HttpRequest
        :type http_request: HttpRequest
        :return HTTPClient
        :rtype HTTPClient
        """

        # Compute key
        key = "{0}#{1}#{2}#{3}#{4}#{5}#{6}#{7}#{8}#{9}#".format(
            # host and port
            url.host,
            url.port,
            # Ssl
            url.scheme == PROTO_HTTPS,
            # Other dynamic stuff
            http_request.https_insecure,
            http_request.disable_ipv6,
            http_request.connection_timeout_ms / 1000,
            http_request.network_timeout_ms / 1000,
            http_request.http_concurrency,
            http_request.http_proxy_host,
            http_request.http_proxy_port,
        )

        # Check
        if key in self._gevent_pool:
            SolBase.sleep(0)
            return self._gevent_pool[key]

        # Allocate (in lock)
        with self._gevent_locker:
            # Check maxed
            if len(self._gevent_pool) >= self._gevent_pool_max:
                raise Exception("gevent pool maxed, cur={0}, max={1}".format(
                    len(self._gevent_pool), self._gevent_pool_max
                ))

            # Ok, allocate
            http = HTTPClient.from_url(
                url,
                insecure=http_request.https_insecure,
                disable_ipv6=http_request.disable_ipv6,
                connection_timeout=http_request.connection_timeout_ms / 1000,
                network_timeout=http_request.network_timeout_ms / 1000,
                concurrency=http_request.http_concurrency,
                proxy_host=http_request.http_proxy_host,
                proxy_port=http_request.http_proxy_port,
                headers={},
            )

            self._gevent_pool[key] = http
            logger.info("Started new pool for key=%s", key)
            SolBase.sleep(0)
            return http

    # ====================================
    # URLLIB3 HTTP PROXY POOL
    # ====================================

    def urllib3_from_pool(self, http_request):
        """
        Get a u3 pool from url and request
        :param http_request: HttpRequest
        :type http_request: HttpRequest
        :return urllib3.poolmanager.ProxyManager
        :rtype urllib3.poolmanager.ProxyManager
        """

        # --------------------------
        # DETECT

        # HTTPS
        is_https = http_request.uri.startswith("https")

        # MTLS
        is_mtls = http_request.mtls_enabled

        # PROXY
        is_proxy = http_request.http_proxy_host is not None

        # IF MTLS is on, we need https
        if is_mtls and not is_https:
            raise Exception("Cannot process, mtls ON, https OFF")

        # --------------------------
        # HANDLE PROXY OFF + MTLS OFF
        if not is_proxy and not is_mtls:
            if http_request.https_insecure and is_https:
                # PROXY OFF + MTLS OFF, HTTPS INSECURE
                return self._u3_basic_pool_https_assert_off
            else:
                # PROXY OFF + MTLS OFF, HTTPS SECURE OR HTTP
                return self._u3_basic_pool_assert_on

        # --------------------------
        # HERE, PROXY AND/OR MTLS

        # GET POOL KEY
        if is_proxy and not is_mtls:
            # PROXY ON, MTLS OFF
            key = "P_{0}#{1}#{2}#{3}".format(
                http_request.http_proxy_host,
                http_request.http_proxy_port,
                http_request.https_insecure,
                is_https,
            )
        elif not is_proxy and is_mtls:
            # PROXY OFF, MTLS ON
            key = "M_{0}#{1}#{2}".format(
                http_request.https_insecure,
                is_https,
                http_request.mtls_pool_key_get(),
            )
        else:
            # PROXY ON, MTLS ON
            key = "PM_{0}#{1}#{2}#{3}#{4}".format(
                http_request.http_proxy_host,
                http_request.http_proxy_port,
                http_request.https_insecure,
                is_https,
                http_request.mtls_pool_key_get(),
            )

        # TRY FROM CACHE
        if key in self._u3_proxy_pool:
            SolBase.sleep(0)
            return self._u3_proxy_pool[key]

        # Allocate (in lock)
        with self._u3_proxy_locker:
            # Check maxed
            if len(self._u3_proxy_pool) >= self._u3_proxy_pool_max:
                raise Exception("u3 pool maxed, cur={0}, max={1}".format(
                    len(self._u3_proxy_pool), self._u3_proxy_pool_max
                ))

            # Uri
            # noinspection HttpUrlsUsage
            if is_proxy:
                # noinspection HttpUrlsUsage
                proxy_url = "http://{0}:{1}".format(
                    http_request.http_proxy_host,
                    http_request.http_proxy_port)

            # Ok, allocate
            # Force underlying fifo queue to 1024 via maxsize
            if is_https:
                if is_mtls:
                    if is_proxy:
                        # HTTPS ON + MTLS ON + PROXY ON
                        p = ProxyManager(
                            num_pools=1024, maxsize=1024, proxy_url=proxy_url,
                            assert_hostname=False if http_request.https_insecure else True,
                            key_file=http_request.mtls_client_key,
                            cert_file=http_request.mtls_client_crt,
                            key_password=http_request.mtls_client_pwd,
                            ca_certs=http_request.mtls_ca_crt,
                        )
                    else:
                        # HTTPS ON + MTLS ON + PROXY OFF
                        p = PoolManager(
                            num_pools=1024, maxsize=1024,
                            assert_hostname=False if http_request.https_insecure else True,
                            key_file=http_request.mtls_client_key,
                            cert_file=http_request.mtls_client_crt,
                            key_password=http_request.mtls_client_pwd,
                            ca_certs=http_request.mtls_ca_crt,
                        )
                else:
                    if is_proxy:
                        # HTTPS ON + MTLS OFF + PROXY ON
                        p = ProxyManager(
                            num_pools=1024, maxsize=1024, proxy_url=proxy_url,
                            assert_hostname=False if http_request.https_insecure else True
                        )
                    else:
                        # HTTPS ON + MTLS OFF + PROXY OFF
                        p = PoolManager(
                            num_pools=1024, maxsize=1024,
                            assert_hostname=False if http_request.https_insecure else True
                        )
            else:
                # HTTPS OFF (cannot have MTLS ON)
                if is_proxy:
                    # HTTPS OFF + PROXY ON
                    p = ProxyManager(num_pools=1024, maxsize=1024, proxy_url=proxy_url)
                else:
                    # HTTPS OFF + PROXY OFF
                    p = PoolManager(num_pools=1024, maxsize=1024)

            # STORE IN CACHE
            self._u3_proxy_pool[key] = p
            logger.info("Started new pool for key=%s", key)
            SolBase.sleep(0)
            return p

    # ====================================
    # HTTP EXEC
    # ====================================

    def go_http(self, http_request):
        """
        Perform an http request
        :param http_request: HttpRequest
        :type http_request: HttpRequest
        :return HttpResponse
        :rtype HttpResponse
        """

        ms = SolBase.mscurrent()
        http_response = HttpResponse()
        general_timeout_sec = float(http_request.general_timeout_ms) / 1000.0
        try:
            # Assign request
            http_response.http_request = http_request

            # Fire
            gevent.with_timeout(
                general_timeout_sec,
                self._go_http_internal,
                http_request, http_response)
            SolBase.sleep(0)
        except Timeout:
            # Failed
            http_response.exception = Exception("Timeout while processing, general_timeout_sec={0}".format(general_timeout_sec))
        except Exception as e:
            # Failed
            http_response.exception = e
        finally:
            # Switch
            SolBase.sleep(0)
            # Assign ms
            http_response.elapsed_ms = SolBase.msdiff(ms)

        # Return
        return http_response

    def _go_http_internal(self, http_request, http_response):
        """
        Perform an http request
        :param http_request: HttpRequest
        :type http_request: HttpRequest
        :param http_response: HttpResponse
        :type http_response: HttpResponse
        """

        try:
            # Default to urllib3
            impl = http_request.force_http_implementation
            if impl == HttpClient.HTTP_IMPL_AUTO:
                # Fallback urllib3 as default
                impl = HttpClient.HTTP_IMPL_URLLIB3

            # Validate MTLS
            http_request.mtls_status_validate()

            # Uri
            url = URL(http_request.uri)
            SolBase.sleep(0)

            # If proxy and https => urllib3
            if http_request.http_proxy_host and url.scheme == PROTO_HTTPS:
                # Proxy via urllib3
                impl = HttpClient.HTTP_IMPL_URLLIB3

            # Log
            logger.debug("Http using impl=%s", impl)

            # Fire
            if impl == HttpClient.HTTP_IMPL_GEVENT:
                self._go_gevent(http_request, http_response)
                SolBase.sleep(0)
            elif impl == HttpClient.HTTP_IMPL_URLLIB3:
                self._go_urllib3(http_request, http_response)
                SolBase.sleep(0)
            else:
                raise Exception("Invalid force_http_implementation")
        except Exception:
            # This is not an underlying http exception, we raise without storing in http_response
            raise

    # ====================================
    # MISC
    # ====================================

    @classmethod
    def _add_header(cls, d, k, v):
        """
        Add header k,v to d
        :param d: dict
        :type d: dict
        :param k: header key
        :param k: str
        :param v: header value
        :param v: str
        """

        if isinstance(k, str):
            k = k.lower()

        if k not in d:
            d[k] = v
        else:
            # Already present
            if isinstance(d[k], list):
                # Just append
                d[k].append(v)
            else:
                # Build a list, existing value and new value
                d[k] = [d[k], v]

    # ====================================
    # GEVENT
    # ====================================
    @classmethod
    def _gevent_check_chunked(cls, http_request):
        """
        Check chunked stuff
        :param http_request: HttpRequest
        :type http_request: HttpRequest
        """
        if http_request.chunked:
            # Chunked is NOT supported for geventhttpclient
            # REF : https://github.com/geventhttpclient/geventhttpclient/issues/158
            raise Exception("Chunked not supported for geventhttpclient, req=%s" % http_request)

    def _go_gevent(self, http_request, http_response):
        """
        Perform an http request
        :param http_request: HttpRequest
        :type http_request: HttpRequest
        :param http_response: HttpResponse
        :type http_response: HttpResponse
        """

        # Implementation
        http_response.http_implementation = HttpClient.HTTP_IMPL_GEVENT

        # Uri
        url = URL(http_request.uri)
        SolBase.sleep(0)

        # Get instance
        logger.debug("Get pool")
        http = self.gevent_from_pool(url, http_request)
        logger.debug("Get pool done, pool=%s", http)
        SolBase.sleep(0)

        # Fire
        ms_start = SolBase.mscurrent()
        logger.debug("Http now")
        if not http_request.method:
            # ----------------
            # Auto-detect
            # ----------------
            if http_request.post_data:
                # Post
                self._gevent_check_chunked(http_request=http_request)
                response = http.post(url.request_uri,
                                     body=http_request.post_data,
                                     headers=http_request.headers)
            else:
                # Get
                response = http.get(url.request_uri,
                                    headers=http_request.headers)
        else:
            # ----------------
            # Use input
            # ----------------
            if http_request.method == "GET":
                # With post datas (optional)
                # Get may be called with post buffer (RFC allowed)
                if http_request.post_data:
                    self._gevent_check_chunked(http_request=http_request)
                    response = http.request(METHOD_GET,
                                            url.request_uri,
                                            body=http_request.post_data,
                                            headers=http_request.headers)
                else:
                    response = http.get(url.request_uri,
                                        headers=http_request.headers)
            elif http_request.method == "DELETE":
                # With post datas
                self._gevent_check_chunked(http_request=http_request)
                response = http.delete(url.request_uri,
                                       body=http_request.post_data,
                                       headers=http_request.headers)
            elif http_request.method == "HEAD":
                # No post datas
                response = http.head(url.request_uri,
                                     headers=http_request.headers)
            elif http_request.method == "OPTIONS":
                # No post datas
                response = http.options(url.request_uri,
                                        headers=http_request.headers)
            elif http_request.method == "PUT":
                # With post datas
                self._gevent_check_chunked(http_request=http_request)
                response = http.put(url.request_uri,
                                    body=http_request.post_data,
                                    headers=http_request.headers)
            elif http_request.method == "POST":
                # With post datas
                self._gevent_check_chunked(http_request=http_request)
                response = http.post(url.request_uri,
                                     body=http_request.post_data,
                                     headers=http_request.headers)
            elif http_request.method == "PATCH":
                # With post datas
                self._gevent_check_chunked(http_request=http_request)
                response = http.patch(url.request_uri,
                                      body=http_request.post_data,
                                      headers=http_request.headers)
            elif http_request.method == "TRACE":
                # With post datas
                self._gevent_check_chunked(http_request=http_request)
                response = http.trace(url.request_uri,
                                      body=http_request.post_data,
                                      headers=http_request.headers)
            else:
                raise Exception("Invalid gevent method={0}".format(http_request.method))

        logger.debug("Http done, ms=%s", SolBase.msdiff(ms_start))
        SolBase.sleep(0)

        # Check
        if not response:
            raise Exception("No response from http")

        # Process it
        http_response.status_code = response.status_code

        # Read
        ms_start = SolBase.mscurrent()
        logger.debug("Read now")
        http_response.buffer = response.read()
        SolBase.sleep(0)
        logger.debug("Read done, ms=%s", SolBase.msdiff(ms_start))
        if response.content_length:
            http_response.content_length = response.content_length
        else:
            if http_response.buffer:
                http_response.content_length = len(http_response.buffer)
            else:
                http_response.content_length = 0

        # noinspection PyProtectedMember
        for k, v in response._headers_index.items():
            HttpClient._add_header(http_response.headers, k, v)

        response.should_close()

        # Over
        SolBase.sleep(0)

    # ====================================
    # URLLIB3
    # ====================================

    def _go_urllib3(self, http_request, http_response):
        """
        Perform an http request
        :param http_request: HttpRequest
        :type http_request: HttpRequest
        :param http_response: HttpResponse
        :type http_response: HttpResponse
        """

        # Implementation
        http_response.http_implementation = HttpClient.HTTP_IMPL_URLLIB3

        # Get pool
        cur_pool = self.urllib3_from_pool(http_request)
        SolBase.sleep(0)

        # From pool
        if http_request.http_proxy_host:
            # ProxyManager : direct
            conn = cur_pool
        else:
            # Get connection from basic pool
            conn = cur_pool.connection_from_url(http_request.uri)
        SolBase.sleep(0)

        # Retries
        retries = Retry(total=0,
                        connect=0,
                        read=0,
                        redirect=0)
        SolBase.sleep(0)

        # Fire
        logger.debug("urlopen")
        if not http_request.method:
            # ----------------
            # Auto-detect
            # ----------------
            if http_request.post_data:
                r = conn.urlopen(
                    method='POST',
                    url=http_request.uri,
                    body=http_request.post_data,
                    headers=http_request.headers,
                    redirect=False,
                    retries=retries,
                    chunked=http_request.chunked,
                )
            else:
                r = conn.urlopen(
                    method='GET',
                    url=http_request.uri,
                    headers=http_request.headers,
                    redirect=False,
                    retries=retries,
                )
        else:
            # ----------------
            # Use input
            # ----------------
            if http_request.method in ["HEAD", "OPTIONS"]:
                # No post datas
                r = conn.urlopen(
                    method=http_request.method,
                    url=http_request.uri,
                    headers=http_request.headers,
                    redirect=False,
                    retries=retries,
                )
            elif http_request.method in ["GET", "TRACE", "POST", "PUT", "PATCH", "DELETE"]:
                # GET can be called with post datas
                r = conn.urlopen(
                    method=http_request.method,
                    url=http_request.uri,
                    body=http_request.post_data,
                    headers=http_request.headers,
                    redirect=False,
                    retries=retries,
                    chunked=http_request.chunked,
                )
            else:
                raise Exception("Invalid urllib3 method={0}".format(http_request.method))
        logger.debug("urlopen ok")
        SolBase.sleep(0)

        # Ok
        http_response.status_code = r.status
        for k, v in r.headers.items():
            HttpClient._add_header(http_response.headers, k, v)
        http_response.buffer = r.data
        http_response.content_length = len(http_response.buffer)

        # Over
        SolBase.sleep(0)
