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
from datetime import datetime
from math import ceil

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
DEFAULT_WARNING = 1000
DEFAULT_CRITICAL = 1500


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
$CheckOutputObj = $CheckInputDaTa

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
parser.add_option('-w', '--warning',
                  dest="warning", type="int",
                  help='Warning value for connection. In [ms]. Default : 100 [ms]')
parser.add_option('-c', '--critical',
                  dest="critical", type="int",
                  help='Critical value for connection. In [ms]. Default : 300 [ms]')
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

    # Try to get numeic warning/critical values
    s_warning = opts.warning or DEFAULT_WARNING
    s_critical = opts.critical or DEFAULT_CRITICAL

    try:
        #start timming
        start_time = datetime.now()

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
            "hello": "world",
            "I": "Kick rock das mama"
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
        result = PowerShellHelpers.ececute_powershell(
            client,
            executable_ps_script,
            debug
        )
        if debug:
            print("check output")
            print("------------")
            print(result)

        #get request time
        stop_time = datetime.now()
        elapsed_time = (stop_time - start_time)
        elapsed_time_ms = int(
            ceil(
                elapsed_time.microseconds * 0.001
            )
        )

        #Format perf data string
        con_perf_data_string = OutputFormatHelpers.perf_data_string(
            label="connection delay",
            value=elapsed_time_ms,
            warn=s_warning,
            crit=s_critical,
            UOM='ms'
        )

        #check logic
        if data == result:
            status = "OK"
            message = "WinRM Connection successful"
            if elapsed_time_ms > s_warning:
                status = "Warning"
                message = "WinRM connection with too slow"
            if elapsed_time_ms > s_critical:
                status = "Critical"
                message = "WinRMC onnection too slow"
        else:
            status = "Critical"
            message = "Echo does not match"

        output = OutputFormatHelpers.check_output_string(
            status,
            message,
            [con_perf_data_string]
        )

        print(output)

    except Exception as e:
        if debug:
            print(e)
            the_type, value, tb = sys.exc_info()
            traceback.print_tb(tb)
        print("Error: {m}".format(m=e))
        sys.exit(2)

    finally:
        if status == "Critical":
            sys.exit(2)
        if status == "Warning":
            sys.exit(1)
        sys.exit(0)