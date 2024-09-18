"""
# -*- coding: utf-8 -*-
# ===============================================================================
#
# Copyright (C) 2013/2017 Laurent Labatut / Laurent Champagnac
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
import subprocess
from os.path import dirname, abspath

from pysolbase.SolBase import SolBase

SolBase.voodoo_init()
import logging
import unittest
from urllib import parse

from pysolbase.FileUtility import FileUtility

from pysolhttpclient.Http.HttpClient import HttpClient
from pysolhttpclient.Http.HttpRequest import HttpRequest
from pysolhttpclient.Http.HttpResponse import HttpResponse
from pysolhttpclient.HttpMock.HttpMock import HttpMock

logger = logging.getLogger(__name__)


def is_squid_present():
    """
    Check is squid is present
    :return bool
    :rtype bool
    """

    for f in [
        "/etc/squid/squid.conf",
        "/etc/squid3/squid.conf"
    ]:
        if FileUtility.is_file_exist(f):
            logger.info("Squid detected, f=%s", f)
            return True

    logger.info("Squid not detected")
    return False


# noinspection PyProtectedMember
class TestHttpClientUsingHttpMock(unittest.TestCase):
    """
    Test description
    """

    # noinspection PyPep8Naming
    def setUp(self):
        """
        Setup (called before each test)
        """

        self.h = None

        import warnings
        warnings.simplefilter("ignore", ResourceWarning)
        from urllib3.exceptions import InsecureRequestWarning
        warnings.simplefilter("ignore", InsecureRequestWarning)

    # noinspection PyPep8Naming
    def tearDown(self):
        """
        Setup (called after each test)
        """

        if self.h:
            logger.warning("h set, stopping, not normal")
            self.h.stop()
            self.h = None

    def test_mtls_limit_cases(self):
        """
        Test
        """

        current_dir = dirname(abspath(__file__)) + SolBase.get_pathseparator()
        logger.info("Using current_dir=%s", current_dir)

        mtls_dir = current_dir + "../z_mtls/"
        logger.info("Using mtls_dir=%s", mtls_dir)
        self.assertTrue(os.path.exists(mtls_dir))

        s_client_crt = mtls_dir + "client.crt"
        s_client_key = mtls_dir + "client.key"
        s_client_pass = "zzzz"
        s_ca_crt = mtls_dir + "ca.crt"

        self.assertTrue(os.path.isfile(s_client_crt))
        self.assertTrue(os.path.isfile(s_client_key))
        self.assertTrue(os.path.isfile(s_ca_crt))

        # Lets go
        mtls_uri = "https://127.0.0.1:7943"
        hreq = HttpRequest()
        hreq.method = "GET"
        hreq.uri = mtls_uri
        hreq.mtls_enabled = True
        hreq.mtls_client_key = s_client_key
        hreq.mtls_client_crt = s_client_crt
        hreq.mtls_client_pwd = s_client_pass
        hreq.mtls_ca_crt = s_ca_crt

        # OK
        hreq.mtls_status_validate()

        # NO PWD (optional)
        hreq.mtls_client_pwd = None
        hreq.mtls_status_validate()

        # Invalid client key
        hreq.mtls_client_key = None
        self.assertRaisesRegex(Exception, "MTLS_INVALID.*mtls_client_key.*", hreq.mtls_status_validate)

        hreq.mtls_client_key = "do_not_exists"
        self.assertRaisesRegex(Exception, "MTLS_FAILED.*mtls_client_key.*", hreq.mtls_status_validate)

        # Invalid client crt
        hreq.mtls_client_key = s_client_key
        hreq.mtls_client_crt = None
        self.assertRaisesRegex(Exception, "MTLS_INVALID.*mtls_client_crt.*", hreq.mtls_status_validate)

        hreq.mtls_client_crt = "do_not_exists"
        self.assertRaisesRegex(Exception, "MTLS_FAILED.*mtls_client_crt.*", hreq.mtls_status_validate)

        # Invalid ca crt : optional
        hreq.mtls_client_crt = s_client_crt
        hreq.mtls_ca_crt = None
        hreq.mtls_status_validate()

        hreq.mtls_ca_crt = "do_not_exists"
        self.assertRaisesRegex(Exception, "MTLS_FAILED.*mtls_ca_crt.*", hreq.mtls_status_validate)

        # Reset
        hreq.mtls_client_key = s_client_key
        hreq.mtls_client_crt = s_client_crt
        hreq.mtls_client_pwd = s_client_pass
        hreq.mtls_ca_crt = s_ca_crt

        # Force gevent
        hreq.force_http_implementation = HttpClient.HTTP_IMPL_GEVENT
        self.assertRaisesRegex(Exception, "MTLS_FAILED.*not supported on HTTP_IMPL_GEVENT", hreq.mtls_status_validate)

        # Invalid full config but enabled
        hreq.mtls_client_key = None
        hreq.mtls_client_crt = None
        hreq.mtls_ca_crt = None
        hreq.mtls_client_pwd = None
        hreq.force_http_implementation = HttpClient.HTTP_IMPL_AUTO
        self.assertRaisesRegex(Exception, "MTLS_INVALID_A.*", hreq.mtls_status_validate)

        # MTLS off
        hreq.mtls_enabled = False
        hreq.mtls_status_validate()

    def test_mtls_ok(self):
        """
        Test MTLS
        """

        cmd = "netstat -ltpn | grep 7943"
        cmd_out = subprocess.getoutput(cmd)
        logger.info("GOT cmd_out=%s", cmd_out)
        if ":7943" not in cmd_out:
            logger.info("MTLS not detected, bypass")
            return

        logger.info("MTLS detected, checking")
        current_dir = dirname(abspath(__file__)) + SolBase.get_pathseparator()
        logger.info("Using current_dir=%s", current_dir)

        mtls_dir = current_dir + "../z_mtls/"
        logger.info("Using mtls_dir=%s", mtls_dir)
        self.assertTrue(os.path.exists(mtls_dir))

        s_client_crt = mtls_dir + "client.crt"
        s_client_key = mtls_dir + "client.key"
        s_client_pass = "zzzz"
        s_ca_crt = mtls_dir + "ca.crt"

        self.assertTrue(os.path.isfile(s_client_crt))
        self.assertTrue(os.path.isfile(s_client_key))
        self.assertTrue(os.path.isfile(s_ca_crt))

        # Lets go
        mtls_uri = "https://127.0.0.1:7943"
        hreq = HttpRequest()
        hreq.method = "GET"
        hreq.uri = mtls_uri
        hreq.mtls_enabled = True
        hreq.mtls_client_key = s_client_key
        hreq.mtls_client_crt = s_client_crt
        hreq.mtls_client_pwd = s_client_pass
        hreq.mtls_ca_crt = s_ca_crt

        hrep = HttpClient().go_http(http_request=hreq)
        logger.info("GOT hrep=%s", hrep)
        self.assertIsNone(hrep.exception)
        self.assertEqual(hrep.status_code, 200)
        self.assertEqual(hrep.buffer.decode("utf8"), "MTLS_OK")

    def test_add_headers(self):
        """
        Test
        """

        d = dict()

        # First one
        HttpClient._add_header(d, "toto", "toto_v1")
        self.assertIsInstance(d["toto"], str)

        # Switch to list
        self.assertEqual(d["toto"], "toto_v1")
        HttpClient._add_header(d, "toto", "toto_v2")
        self.assertIsInstance(d["toto"], list)
        self.assertIn("toto_v1", d["toto"])
        self.assertIn("toto_v2", d["toto"])

        # Add a new one
        HttpClient._add_header(d, "toto", "toto_v3")
        self.assertIsInstance(d["toto"], list)
        self.assertIn("toto_v1", d["toto"])
        self.assertIn("toto_v2", d["toto"])
        self.assertIn("toto_v3", d["toto"])

    def test_get_basic_gevent(self):
        """
        Test
        """

        self._http_basic_internal(HttpClient.HTTP_IMPL_GEVENT)

    def test_get_basic_urllib3(self):
        """
        Test
        """

        self._http_basic_internal(HttpClient.HTTP_IMPL_URLLIB3)

    def test_get_basic_https_gevent(self):
        """
        Test
        """

        self._http_basic_internal(HttpClient.HTTP_IMPL_GEVENT, https=True)

    def test_get_basic_https_urllib3(self):
        """
        Test
        """

        self._http_basic_internal(HttpClient.HTTP_IMPL_URLLIB3, https=True)

    @unittest.skipIf(not is_squid_present(), "squid not detected")
    def test_get_proxy_squid_gevent(self):
        """
        Test
        """

        self._http_basic_internal(HttpClient.HTTP_IMPL_GEVENT, proxy=True)

    @unittest.skipIf(not is_squid_present(), "squid not detected")
    def test_get_proxy_squid_urllib3(self):
        """
        Test
        """

        self._http_basic_internal(HttpClient.HTTP_IMPL_URLLIB3, proxy=True)

    @unittest.skipIf(not is_squid_present(), "squid not detected")
    def test_get_proxy_squid_https_gevent(self):
        """
        Test
        """

        self._http_basic_internal(HttpClient.HTTP_IMPL_GEVENT, proxy=True, https=True)

    @unittest.skipIf(not is_squid_present(), "squid not detected")
    def test_get_proxy_squid_https_squid3(self):
        """
        Test
        """

        self._http_basic_internal(HttpClient.HTTP_IMPL_URLLIB3, proxy=True, https=True)

    def _http_basic_internal(self, force_implementation, proxy=False, https=False):
        """
        Test
        """

        logger.info("Starting, impl=%s", force_implementation)

        hc = HttpClient()

        for _ in range(0, 8):

            # Setup request
            hreq = HttpRequest()
            hreq.force_http_implementation = force_implementation

            if https:
                hreq.uri = "https://pypi.org"
            else:
                # This will redirect https
                # noinspection HttpUrlsUsage
                hreq.uri = "http://pypi.org"

            # Http proxy
            if proxy:
                hreq.http_proxy_host = "127.0.0.1"
                hreq.http_proxy_port = 1180

            hresp = hc.go_http(hreq)

            self.assertIsNotNone(hresp)
            self.assertIsInstance(hresp, HttpResponse)

            self.assertIsNotNone(hresp.http_request)
            self.assertEqual(id(hreq), id(hresp.http_request))

            self.assertIsNotNone(hresp.elapsed_ms)

            self.assertIsNone(hresp.exception)

            if proxy and https:
                # Force to urllib3
                self.assertEqual(hresp.http_implementation, HttpClient.HTTP_IMPL_URLLIB3)
            else:
                self.assertEqual(hresp.http_implementation, force_implementation)

            self.assertIsNotNone(hresp.content_length)
            self.assertIsNotNone(hresp.buffer)
            self.assertEqual(hresp.content_length, len(hresp.buffer))

            self.assertGreater(len(hresp.headers), 0)

            self.assertIn(hresp.status_code, [200, 302, 301])

            SolBase.sleep(250)

    def test_httpmock_noproxy_gevent(self):
        """
        Test
        """

        self._http_basic_internal_to_httpmock(HttpClient.HTTP_IMPL_GEVENT, proxy=False)

    def test_httpmock_noproxy_urllib3(self):
        """
        Test
        """

        self._http_basic_internal_to_httpmock(HttpClient.HTTP_IMPL_URLLIB3, proxy=False)

    @unittest.skipIf(not is_squid_present(), "squid not detected")
    def test_httpmock_proxy_squid_gevent(self):
        """
        Test
        """

        self._http_basic_internal_to_httpmock(HttpClient.HTTP_IMPL_GEVENT, proxy=True)

    @unittest.skipIf(not is_squid_present(), "squid not detected")
    def test_httpmock_proxy_squid_urllib3(self):
        """
        Test
        """

        self._http_basic_internal_to_httpmock(HttpClient.HTTP_IMPL_URLLIB3, proxy=True)

    def _http_basic_internal_to_httpmock(self, force_implementation, proxy=False):
        """
        Test
        """

        logger.info("impl=%s, proxy=%s", force_implementation, proxy)

        self.h = HttpMock()

        self.h.start()
        self.assertTrue(self.h._is_running)
        self.assertIsNotNone(self.h._wsgi_server)
        self.assertIsNotNone(self.h._server_greenlet)

        # Param
        v = parse.urlencode({"p1": "v1 2.3/4"})

        # Client
        hc = HttpClient()

        # ---------------------
        # AUTO-DETECT
        # ---------------------

        # AUTO-DETECT : Http get
        logger.info("AUTO: GET")
        hreq = HttpRequest()
        hreq.force_http_implementation = force_implementation
        if proxy:
            hreq.http_proxy_host = "127.0.0.1"
            hreq.http_proxy_port = 1180
        hreq.uri = "http://127.0.0.1:7900/unittest?" + v
        hresp = hc.go_http(hreq)
        logger.info("Got=%s", hresp)
        self.assertEqual(hresp.status_code, 200)
        self.assertEqual(SolBase.binary_to_unicode(hresp.buffer, "utf-8"),
                         "OK\nfrom_qs={'p1': 'v1 2.3/4'} -EOL\nfrom_post={} -EOL\nfrom_method=GET\n")

        # AUTO-DETECT : Http post
        logger.info("AUTO: POST")
        hreq = HttpRequest()
        hreq.force_http_implementation = force_implementation
        if proxy:
            hreq.http_proxy_host = "127.0.0.1"
            hreq.http_proxy_port = 1180
        hreq.uri = "http://127.0.0.1:7900/unittest"
        hreq.post_data = v
        hresp = hc.go_http(hreq)
        logger.info("Got=%s", hresp)
        self.assertEqual(hresp.status_code, 200)

        # PY3 : urllib parse return binary, so we have binary in post...
        self.assertEqual(SolBase.binary_to_unicode(hresp.buffer, "utf-8"),
                         "OK\nfrom_qs={} -EOL\nfrom_post={b'p1': b'v1 2.3/4'} -EOL\nfrom_method=POST\n")

        # ---------------------
        # MANUAL
        # ---------------------

        # No post
        for cur_method in ["GET", "HEAD", "OPTIONS", "TRACE"]:
            # Gevent do not support some, skip
            # if force_implementation == HttpClient.HTTP_IMPL_GEVENT and cur_method in ["PATCH", "OPTIONS", "TRACE"]:
            #    continue
            logger.info("MANUAL, NO BODY : %s", cur_method)
            hreq = HttpRequest()
            hreq.force_http_implementation = force_implementation
            if proxy:
                hreq.http_proxy_host = "127.0.0.1"
                hreq.http_proxy_port = 1180
            hreq.uri = "http://127.0.0.1:7900/unittest?" + v
            hreq.method = cur_method
            hresp = hc.go_http(hreq)
            logger.info("Got=%s", hresp)
            self.assertEqual(hresp.status_code, 200)
            if cur_method == "HEAD":
                # No body in reply
                self.assertEqual(SolBase.binary_to_unicode(hresp.buffer, "utf-8"), "")
            else:

                self.assertEqual(SolBase.binary_to_unicode(hresp.buffer, "utf-8"),
                                 "OK\nfrom_qs={'p1': 'v1 2.3/4'} -EOL\nfrom_post={} -EOL\nfrom_method=" + cur_method + "\n")

        # Post
        for cur_method in ["GET", "TRACE", "POST", "PUT", "PATCH", "DELETE"]:
            # Gevent do not support some, skip
            # if force_implementation == HttpClient.HTTP_IMPL_GEVENT and cur_method in ["PATCH", "OPTIONS", "TRACE"]:
            #    continue
            logger.info("MANUAL, BODY : %s", cur_method)
            hreq = HttpRequest()
            hreq.force_http_implementation = force_implementation
            if proxy:
                hreq.http_proxy_host = "127.0.0.1"
                hreq.http_proxy_port = 1180
            hreq.uri = "http://127.0.0.1:7900/unittest"
            hreq.method = cur_method
            hreq.post_data = v
            hresp = hc.go_http(hreq)
            logger.info("Got=%s", hresp)
            self.assertEqual(hresp.status_code, 200)

            # PY3 : urllib parse return binary, so we have binary in post...
            self.assertEqual(SolBase.binary_to_unicode(hresp.buffer, "utf-8"),
                             "OK\nfrom_qs={} -EOL\nfrom_post={b'p1': b'v1 2.3/4'} -EOL\nfrom_method=" + cur_method + "\n")

        # ---------------------
        # INVALID
        # ---------------------

        # Http get toward invalid
        hreq = HttpRequest()
        hreq.force_http_implementation = force_implementation
        if proxy:
            hreq.http_proxy_host = "127.0.0.1"
            hreq.http_proxy_port = 1180
        hreq.uri = "http://127.0.0.1:7900/invalid"
        hresp = hc.go_http(hreq)
        logger.info("Got=%s", hresp)
        self.assertEqual(hresp.status_code, 400)

        # Over
        self.h.stop()
        self.assertFalse(self.h._is_running)
        self.assertIsNone(self.h._wsgi_server)
        self.assertIsNone(self.h._server_greenlet)
