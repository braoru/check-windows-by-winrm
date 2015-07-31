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
# The Lazy writes metric is defined as "Number of times per second SQL Server relocates dirty pages from buffer pool (memory) to disk"
# The threshold value for Lazy Writes is 20. If SQL Server is under memory pressure. If the Lazy Writes value is constantly higher than 20, to be sure that the server is under memory pressure, check Page Life Expectancy.
# (http://www.sqlshack.com/)
DEFAULT_WARNING = 20
DEFAULT_CRITICAL = 20


# OPT parsing
# -----------
parser = optparse.OptionParser(
    "%prog [options]", version="%prog " + version)
usage = """%prog [options] 

The Lazy writes metric is defined as Number of times per second SQL Server relocates dirty pages from buffer pool (memory) to disk.
If SQL Server is under memory pressure, the lazy writer will be busy trying to free enough internal memory pages and will be flushing the pages extensively.
If the Lazy Writes value is constantly higher than 20, to be sure that the server is under memory pressure.
(http://www.sqlshack.com/)
"""

parser = optparse.OptionParser(usage=usage)

parser = WindowsSystemHelpers.add_winrm_parser_options(parser)
parser = MSSQLHelpers.add_mssql_perfmon_parser_options(parser)

parser.add_option('-w', '--warning',
                  dest="warning", type="float",
                  help='Warning value for connection. Default : 20 ')
parser.add_option('-c', '--critical',
                  dest="critical", type="float",
                  help='Critical value for connection. Default : 20 ')

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
            "perfcounter_to_check": ":Buffer Manager\Lazy writes/sec"
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
        avg_message = "{l} Lazy Writes".format(
            l=raw_buffer_sample
        )
        if raw_buffer_sample >= s_warning:
            status = 'Warning'
        if raw_buffer_sample >= s_critical:
            status = 'Critical'


        #Format perf data string
        con_perf_data_string = OutputFormatHelpers.perf_data_string(
            label="Lazy Writes",
            value=raw_buffer_sample,
            warn=s_warning,
            crit=s_critical,
            UOM='s'
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
