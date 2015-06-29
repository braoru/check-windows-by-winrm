#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Copyright (C) 2013:
#     Sébastien Pasche, sebastien.pasche@leshop.ch
#     Mikael Bugnon, mikael.bugnon@leshop.ch
#
# Permission is hereby granted, free of charge, to any person obtaining a
# copy of this software and associated documentation files (the "Software"),
# to deal in the Software without restriction, including without limitation
# the rights to use, copy, modify, merge, publish, distribute, sublicense,
# and/or sell copies of the Software, and to permit persons to whom the
# Software is furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
# FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER
# DEALINGS IN THE SOFTWARE.
#

author = "Sebastien Pasche"
maintainer = "Sebastien Pasche"
version = "0.0.1"

import optparse
import sys
import os
import traceback

try:
    import winrm
    from winrm.protocol import Protocol
except ImportError:
    print "ERROR : this plugin needs the local winrm lib. Please install it"
    sys.exit(2)


#Ok try to load our directory to load the plugin utils.
my_dir = os.path.dirname(__file__)
sys.path.insert(0, my_dir)

try:
    from winrm_checks import OutputFormatHelpers, PowerShellHelpers
except ImportError:
    print "ERROR : this plugin needs the local winrm lib. Please install it"
    sys.exit(2)

#DEFAULT LIMITS
#--------------

#https://msdn.microsoft.com/en-us/library/system.serviceprocess.servicecontrollerstatus(v=vs.110).aspx
WINDOWS_SERVICE_STATUS = {
    5: "ContinuePending",
    7: "Paused",
    6: "PausePending",
    4: "Running",
    2: "StartPending",
    1: "Stopped",
    3: "StopPending"
}


DEFAULT_OK= frozenset(
    [
        4
    ]
)

DEFAULT_WARNING = frozenset(
    [
        7,
        6,
        2,
        5
    ]
)

DEFAULT_CRITICAL = frozenset(
    [
        1,
        3
    ]
)

# Powershell
# ----------
ps_script = """
#Functions
#---------

#check input data
#----------------
{check_input_json}


#Obtain data
#-----------
$CheckOutputObj = Get-Service -name $CheckInputDaTa.service_to_check

#Format output
$CheckOuputJson = $CheckOutputObj | ConvertTo-Json
$CheckOuputJsonBytes  = [System.Text.Encoding]::UTF8.GetBytes($CheckOuputJson)
$CheckOuputJsonBytesBase64 = [System.Convert]::ToBase64String($CheckOuputJsonBytes)
Write-Host $CheckOuputJsonBytesBase64
"""


# OPT parsing
# -----------
parser = optparse.OptionParser(
    "%prog [options]", version="%prog " + version)
parser.add_option('-H', '--hostname',
                  dest="hostname",
                  help='Hostname to connect to')
parser.add_option('-p', '--port',
                  dest="port", type="int", default=5986,
                  help='WinRM HTTP port to connect to. Default : HTTPS - 5986')
parser.add_option('-s', '--http-scheme',
                  dest="scheme", default="https",
                  help='WinRM HTTP scheme to connect to. Default : https://')
parser.add_option('-U', '--user',
                  dest="user", default="shinken",
                  help='remote use to use. By default shinken.')
parser.add_option('-P', '--password',
                  dest="password",
                  help='Password. By default will use void')
parser.add_option('-S', '--service',
                  dest="service", default=None,
                  help='Service to check')
parser.add_option('--debug',
                  dest="debug", default=False, action="store_true",
                  help='Enable debug')

if __name__ == '__main__':
    # Ok first job : parse args
    opts, args = parser.parse_args()
    if args:
        parser.error("Does not accept any argument.")

    # connection parameters
    port = opts.port
    hostname = opts.hostname or ''
    scheme = opts.scheme
    user = opts.user
    password = opts.password
    debug = opts.debug

    # get service
    if opts.service is None:
        raise Exception("You must specify a service to check")

    service_name = opts.service

    try:
        # Connect to the remote host
        client = winrm.Session(
            '{s}://{h}:{p}'.format(
                s=scheme,
                h=hostname,
                p=port
            ),
            auth=(
                user,
                password
            )
        )

        # Fill script data
        data = {
            "service_to_check": service_name
        }

        #prepare the script
        executable_ps_script = PowerShellHelpers.generate_ps(
            ps_script,
            data
        )

        if debug:
            print("Script to execute")
            print("-----------------")
            print(executable_ps_script)

        #execute the scripte
        service_state = PowerShellHelpers.ececute_powershell(
            client,
            executable_ps_script,
            debug
        )
        if debug:
            print("check output")
            print("------------")
            print(service_state)

        #check logic
        service_status_code = service_state['Status']
        if service_status_code in DEFAULT_OK:
            status = "OK"
        elif service_status_code in DEFAULT_WARNING:
            status = "Warning"
        elif service_status_code in DEFAULT_CRITICAL:
            status = "Critical"
        else:
            raise Exception("Invalid service status")

        message = "{s} state is : {status}".format(
            s=service_name,
            status=WINDOWS_SERVICE_STATUS[service_status_code]
        )

        output = OutputFormatHelpers.check_output_string(
            status,
            message,
            None
        )

        print(output)
    except Exception as e:
        if debug:
            print(e)
            the_type, value, tb = sys.exc_info()
            traceback.print_tb(tb)
        print("Error: {m}".format(m=e))
        sys.exit(2)
