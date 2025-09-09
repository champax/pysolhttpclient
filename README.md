pysolhttpclient
============

Welcome to pysol

Copyright (C) 2013/2025 Laurent Labatut / Laurent Champagnac

pysolhttpclient is a set an HTTP client Apis

They are gevent based
They support urllib3 and geventhttpclient implementations
They support http and https
They support http proxy (tested with squid)

HttpResponse.headers is a dict, from string to string (direct header access) or from string to list (in case the same header is present several times in the http response)

