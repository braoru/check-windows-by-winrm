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

author = "Mikael Bugnon"
maintainer = "Sebastien Pasche"
version = "0.0.1"

import optparse
import sys
import os
import traceback
from pprint import pprint
from statistics import mean

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
    from winrm_checks import OutputFormatHelpers, PowerShellHelpers, MSSQLHelpers, WindowsSystemHelpers
except ImportError:
    print "ERROR : this plugin needs the local winrm lib. Please install it"
    sys.exit(2)

#DEFAULT LIMITS
#--------------
# Ideally, SQL Server would read all pages from the buffer cache and there will be no need to read any from disk.
# In this case, the Buffer Cache Hit Ratio value would be 100. # The recommended value for Buffer Cache Hit Ratio is over 90.
# (http://www.sqlshack.com/)
DEFAULT_CRITICAL = 90.0
DEFAULT_WARNING = 90.0


# OPT parsing
# -----------
parser = optparse.OptionParser(
    "%prog [options]", version="%prog " + version)
usage = """%prog [options]

Cache Hit Ration Indicates It gives the ratio of the data pages found and read from the SQL Server buffer cache and all data page requests.
The pages that are not found in the buffer cache are read from the disk, which is significantly slower and affects performance.
The recommended value for Buffer Cache Hit Ratio is over 90.
(http://www.sqlshack.com/)"
"""
parser = optparse.OptionParser(usage=usage)

parser = WindowsSystemHelpers.add_winrm_parser_options(parser)
parser = MSSQLHelpers.add_mssql_perfmon_parser_options(parser)

parser.add_option('-w', '--warning',
                  dest="warning", type="float",
                  help='Warning value for cache hit ratio. In [%]. Default : 90.0 ')
parser.add_option('-c', '--critical',
                  dest="critical", type="float",
                  help='Critical value for cache hit ratio. In [%]. Default : 90.0 ')


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

    #instance to monitor
    if opts.mssqlinstance_to_check is None:
        parser.error("You must specify a mssql instance")

    mssqlinstance_to_check = opts.mssqlinstance_to_check

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

        #check parameters
        check_parameters = {
            "mssqlinstance_to_check": mssqlinstance_to_check,
            "perfcounter_to_check": ":Buffer Manager\Buffer cache hit ratio"
        }

        #create final powershell script
        executable_ps_script = PowerShellHelpers.generate_ps(
            MSSQLHelpers.PS_SCRIPT_MSSQL_COUNTER,
            check_parameters      
        )

        if debug:
            print("Script to execute")
            print("-----------------")
            print(executable_ps_script)

        #execute the scripte
        raw_buffer_sample = PowerShellHelpers.ececute_powershell(
            client,
            executable_ps_script,
            debug
        )

        if debug:
            print("check output")
            print("------------")
            print(raw_buffer_sample)

        #check logic
        status = 'OK'
        avg_message = "{l}% CacheHitRatio".format(
            l=raw_buffer_sample,            
        )
        if raw_buffer_sample <= s_warning:
            status = 'Warning'
        if raw_buffer_sample <= s_critical:
            status = 'Critical'

        #Format perf data string
        con_perf_data_string = OutputFormatHelpers.perf_data_string(
            label="CacheHitRatio",
            value=raw_buffer_sample,
            warn=s_warning,
            crit=s_critical,
            min='100.0',
            max='0.0',
            UOM='%'
        )

        #print output
        output = OutputFormatHelpers.check_output_string(
            status,
            avg_message,
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
