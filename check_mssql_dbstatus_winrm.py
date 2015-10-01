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
DEFAULT_WARNING = 1
DEFAULT_CRITICAL = 1


#SQL QUERY
#--------
SQL_QUERY = "SELECT 'databases in failed state:' as parameter,COUNT(*) AS nb_db_errors FROM sys.databases WHERE state IN (1, 3, 4, 5, 6, 7)"

# OPT parsing
# ----------- 
parser = optparse.OptionParser(
    "%prog [options]", version="%prog " + version)

usage = """%prog [options]

Execute SQL query
"""

parser = optparse.OptionParser(usage=usage)

parser = WindowsSystemHelpers.add_winrm_parser_options(parser)

parser.add_option('-w', '--warning',
                  dest="warning", type="float",
                  help='Warning value for connection. In [ms]. Default : 1')
parser.add_option('-c', '--critical',
                  dest="critical", type="float",
                  help='Critical value for connection. In [ms]. Default : 1')
parser.add_option('--sample-interval',
                  dest="sample_interval", type="int", default=1,
                  help='Sampling interval. In [s]. Default : 1 []')
parser.add_option('--max-sample',
                  dest="max_sample", type="int", default=1,
                  help='Sampling number. In [number]. Default : 5')
parser.add_option('-I',
                  dest="mssqlinstance_to_check", default="MSSQLSERVER",
                  help='MSSQL Instance to check')

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

    #sampling parameters
    sample_interval = opts.sample_interval
    max_sample = opts.max_sample

    # Try to get numeic warning/critical values
    s_warning = opts.warning or DEFAULT_WARNING
    s_critical = opts.critical or DEFAULT_CRITICAL

    # get PErformance counter
    # if opts.sql_script is None:
    #    raise Exception("You must specify a SQL script to check")

    alp_group_name = opts.hostname
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

        sql_script = SQL_QUERY.format(group_name=alp_group_name)

        #sampling parameters
        check_parameters = {
            "mssqlinstance_to_check": mssqlinstance_to_check,
            "sql_script": sql_script
        }

        
        #prepare the script
        #executable_ps_script = MSSQLHelpers.generate_ps(
        #    check_parameters
        #)
        executable_ps_script = PowerShellHelpers.generate_ps(
            MSSQLHelpers.PS_SCRIPT_MSSQL_QUERY,
            check_parameters
        )

        if debug:
            print("Script to execute")
            print("-----------------")
            print(executable_ps_script)

        #execute the scripte
        raw_sample = PowerShellHelpers.ececute_powershell(
            client,
            executable_ps_script,
            debug
        )

        if debug:
            print("check output")
            print("------------")
            print(raw_sample)

        #Process data
        #five_sec_load_average = mean(raw_sample)

        measurement_time = sample_interval * max_sample

        #Format perf data string
        con_perf_data_string = OutputFormatHelpers.perf_data_string(
            label="DB Health",
            value=raw_sample,
            warn=s_warning,
            crit=s_critical,
            min='0',
            max='1',
            UOM=''
        )

        #check logic
        status = 'OK'
        avg_message = "{l} Database health".format(
            l=raw_sample        
        )
        if raw_sample >= s_warning:
            status = 'Warning'
        if raw_sample >= s_critical:
            status = 'Critical'

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