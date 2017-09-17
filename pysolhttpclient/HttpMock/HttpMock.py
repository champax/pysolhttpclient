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


import logging
import urlparse
from threading import Lock

import gevent
# noinspection PyProtectedMember
from gevent.baseserver import _parse_address
from gevent.event import Event
from gevent.pywsgi import WSGIServer
from pysolbase.SolBase import SolBase

SolBase.voodoo_init()

logger = logging.getLogger(__name__)
lifecyclelogger = logging.getLogger("LifeCycle")


# noinspection PyProtectedMember
class HttpMock(object):
    """
    Http mock
    """

    def __init__(self):
        """
        Constructor
        """

        # Daemon control
        self._locker = Lock()
        self._is_running = False
        self._server_greenlet = None

        # Zip on
        self._zip_enabled = True

        # Start event
        self._start_event = Event()

        # Server
        self._wsgi_server = None

        # Lifecycle stuff (from daemon)
        self._lifecycle_locker = Lock()
        self._lifecycle_interval_ms = 30000
        self._lifecycle_last_log_ms = SolBase.mscurrent()

    # ==============================
    # START / STOP
    # ==============================

    def start(self):
        """
        Start
        """

        with self._locker:
            try:
                lifecyclelogger.info("Start : starting")

                # Check
                if self._is_running:
                    logger.warn("Already running, doing nothing")

                # Start
                self._server_greenlet = gevent.spawn(self._server_forever)
                SolBase.sleep(0)

                # Wait
                lifecyclelogger.debug("Start : waiting")
                self._start_event.wait()
                SolBase.sleep(0)

                # Signal
                self._is_running = True
                lifecyclelogger.info("Start : started")
            except Exception as e:
                logger.error("Exception, e=%s", SolBase.extostr(e))

    def stop(self):
        """
        Stop
        """

        # Signal out of lock (may help greenlet to exit itself)
        self._is_running = False

        with self._locker:
            try:
                lifecyclelogger.info("Stop : stopping")

                # Stop
                if self._wsgi_server:
                    self._wsgi_server.close()
                    self._wsgi_server = None

                # Kill the greenlet
                if self._server_greenlet:
                    logger.info("_server_greenlet.kill")
                    self._server_greenlet.kill()
                    logger.info("_server_greenlet.kill done")
                    # gevent.kill(self._server_greenlet)
                    self._server_greenlet.join()
                    self._server_greenlet = None

                lifecyclelogger.info("Stop : stopped")
            except Exception as e:
                logger.error("Exception, e=%s", SolBase.extostr(e))

    # =====================================
    # LIFECYCLE
    # =====================================

    def _lifecycle_log_status(self):
        """
        Run
        """

        try:
            with self._lifecycle_locker:
                # Check
                ms_diff = SolBase.msdiff(self._lifecycle_last_log_ms)
                if ms_diff < self._lifecycle_interval_ms:
                    return

                # Log now
                self._lifecycle_last_log_ms = SolBase.mscurrent()

            # noinspection PyProtectedMember
            lifecyclelogger.info(
                "self=%s",
                # Id
                id(self),
            )
        except Exception as e:
            logger.warning("Exception, ex=%s", SolBase.extostr(e))

    # ==============================
    # SERVER
    # ==============================

    def _server_forever(self):
        """
        Exec loop
        """

        try:
            # Alloc
            logger.info("Allocating WSGIServer")
            self._wsgi_server = WSGIServer(listener=('localhost', 7900), application=self.on_request)

            logger.info("Starting, %s, %s", self._wsgi_server.address, _parse_address(self._wsgi_server.address))
            SolBase.sleep(0)

            # Signal
            logger.info("Signaling _start_event")
            self._start_event.set()
            SolBase.sleep(0)

            # This will block until signaled
            logger.info("Calling serve_forever")
            self._wsgi_server.serve_forever()
        except Exception as e:
            logger.error("Ex=%s", SolBase.extostr(e))
            # This is fatal, we exit, we cannot serve
            exit(-1)
        finally:
            logger.info("Clearing _start_event")
            self._start_event.clear()

    # ==========================
    # TOOLS
    # ==========================

    def _get_param_from_qs(self, environ):
        """
        Extract params from query string
        :param environ: dict
        :type environ: dict
        :return dict
        :rtype dict
        """

        return self._get_param_internal(environ["QUERY_STRING"])

    def _get_param_from_post_data(self, environ):
        """
        Extract params from post data (treat them as a normal query string)
        Assume post data is urlencoded.
        :param environ: dict
        :type environ: dict
        :return dict
        :rtype dict
        """

        return self._get_param_internal(self._get_post_data(environ))

    # noinspection PyMethodMayBeStatic
    def _get_param_internal(self, buf):
        """
        Get param from a buffer (query string or post data)
        Assume post data is urlencoded.
        :param buf: str
        :type buf: str
        :return dict
        :rtype dict
        """

        if not buf:
            return dict()
        elif len(buf) == 0:
            return dict

        # Decode, browse and hash (got a list of tuple (param, value))
        d = dict()
        for tu in urlparse.parse_qsl(buf, keep_blank_values=True, strict_parsing=True):
            d[tu[0]] = tu[1]
        return d

    # noinspection PyMethodMayBeStatic
    def _get_post_data_raw(self, environ):
        """
        Get post data, raw, not decoded. Return an empty string is no post data.
        :param environ: dict
        :type environ: dict
        :return str
        :rtype str
        """
        wi = environ["wsgi.input"]
        if not wi:
            return ""
        else:
            return wi.read()

    def _get_post_data(self, environ):
        """
        Get post data, raw, not decoded. Return an empty string is no post data.
        :param environ: dict
        :type environ: dict
        :return str
        :rtype str
        """
        wi = self._get_post_data_raw(environ)
        if wi:
            # Try gzip
            try:
                wi = wi.decode("zlib")
            except Exception as ex:
                logger.debug("Unable to decode zlib, should be a normal buffer, ex=%s",
                             SolBase.extostr(ex))

        return wi

    # ==============================
    # MAIN REQUEST CALLBACK
    # ==============================

    def on_request(self, environ, start_response):
        """
        On request callback
        :param environ: environ
        :type environ: dict
        :param start_response: start_response
        :type start_response: instancemethod
        :return: list
        :rtype: list
        """

        try:
            logger.info("Request start now")

            # Log
            for k, v in environ.iteritems():
                logger.debug("Env: %s=%s", k, v)

            # Switch
            pi = environ["PATH_INFO"]
            logger.debug("pi=%s", pi)

            # Sometimes PATH_INFO come with full uri (urllib3) (?!)
            # http://127.0.0.1:7900/unittest
            if pi.endswith("/unittest"):
                return self._on_unit_test(environ, start_response)
            else:
                return self._on_invalid(start_response)
        except Exception as e:
            logger.warn("Ex=%s", SolBase.extostr(e))
            status = "500 Internal Server Error"
            body = status
            headers = [('Content-Type', 'text/plain')]
            start_response(status, headers)
            return [body]
        finally:
            self._lifecycle_log_status()

    # ==============================
    # REQUEST : INVALID
    # ==============================

    # noinspection PyMethodMayBeStatic
    def _on_invalid(self, start_response):
        """
        On request callback
        :param start_response: start_response
        :type start_response: instancemethod
        :return: list
        :rtype: list
        """

        # Debug
        status = "400 Bad Request"
        body = status
        headers = [('Content-Type', 'text/txt')]
        start_response(status, headers)
        return [body]

    # ==============================
    # REQUEST : UNITTEST
    # ==============================

    def _on_unit_test(self, environ, start_response):
        """
        On request callback
        :param environ: environ
        :type environ: dict
        :param start_response: start_response
        :type start_response: instancemethod
        :return: list
        :rtype: list
        """

        # Param
        from_qs = self._get_param_from_qs(environ)
        from_post = self._get_param_from_post_data(environ)

        # Debug
        status = "200 OK"
        body = "OK" + "\n"
        body += "from_qs=" + str(from_qs) + " -EOL\n"
        body += "from_post=" + str(from_post) + " -EOL\n"
        headers = [('Content-Type', 'text/txt')]
        start_response(status, headers)
        return [body]
