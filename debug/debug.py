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
from os.path import dirname, abspath

import urllib3
from pysolbase.SolBase import SolBase
from urllib3 import Retry

current_dir = dirname(abspath(__file__)) + SolBase.get_pathseparator()
mtls_dir = current_dir + "../z_mtls/"
s_client_pem = mtls_dir + "client.pem"
s_client_key = mtls_dir + "client.key"
s_client_pass = "zzz"
s_ca_crt = mtls_dir + "ca.crt"
uri = "https://127.0.0.1:7943"

retries = Retry(total=0,
                connect=0,
                read=0,
                redirect=0)
pool = urllib3.PoolManager(
    cert_file=s_client_pem,
    key_file=s_client_key,
    key_password=s_client_pass,
    # ca_certs=s_ca_crt,
    cert_reqs='CERT_REQUIRED',
    assert_hostname=False,
)
conn = pool.connection_from_url(uri)
r = conn.urlopen(
    method='GET',
    url=uri,
    headers=None,
    redirect=False,
    retries=retries,
)
assert r.status == 200
