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
    from winrm_checks import OutputFormatHelpers, PowerShellHelpers
except ImportError:
    print "ERROR : this plugin needs the local winrm lib. Please install it"
    sys.exit(2)

#DEFAULT LIMITS
#--------------
DEFAULT_WARNING = 80.0
DEFAULT_CRITICAL = 95.0


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
$CheckOutputObj = Get-counter -Counter "\Processor(_Total)\% Processor Time" -SampleInterval $CheckInputDaTa.sample_interval -MaxSamples $CheckInputDaTa.max_sample |
    Foreach-Object {{$_.CounterSamples[0].CookedValue}}

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
                  dest="warning", type="float",
                  help='Warning value for connection. In [ms]. Default : 80.0 [%]')
parser.add_option('-c', '--critical',
                  dest="critical", type="float",
                  help='Critical value for connection. In [ms]. Default : 95.0 [%]')
parser.add_option('--sample-interval',
                  dest="sample_interval", type="int", default=1,
                  help='Cpu sampling interval. In [s]. Default : 1 [s]')
parser.add_option('--max-sample',
                  dest="max_sample", type="int", default=5,
                  help='Cpu sampling number. In [number]. Default : 5')
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

    #sampling parameters
    sample_interval = opts.sample_interval
    max_sample = opts.max_sample

    # Try to get numeic warning/critical values
    s_warning = opts.warning or DEFAULT_WARNING
    s_critical = opts.critical or DEFAULT_CRITICAL

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

        #sampling parameters
        sampling_parameters = {
            "sample_interval": sample_interval,
            "max_sample": max_sample
        }

        #prepare the script
        executable_ps_script = PowerShellHelpers.generate_ps(
            ps_script,
            sampling_parameters
        )

        if debug:
            print("Script to execute")
            print("-----------------")
            print(executable_ps_script)

        #execute the scripte
        raw_cpu_sample = PowerShellHelpers.ececute_powershell(
            client,
            executable_ps_script,
            debug
        )

        if debug:
            print("check output")
            print("------------")
            pprint(raw_cpu_sample)

        #Process data
        five_sec_load_average = mean(raw_cpu_sample)

        measurement_time = sample_interval * max_sample

        #Format perf data string
        con_perf_data_string = OutputFormatHelpers.perf_data_string(
            label="{t}s_load_avg".format(t=measurement_time),
            value=five_sec_load_average,
            warn=s_warning,
            crit=s_critical,
            min='0.0',
            max='100.0',
            UOM='%'
        )

        #check logic
        status = 'OK'
        avg_message = "{l}% {t}s load average".format(
            l=five_sec_load_average,
            t=measurement_time
        )
        if five_sec_load_average >= s_warning:
            status = 'Warning'
        if five_sec_load_average >= s_critical:
            status = 'Critical'

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
        print("Error: {m}".format(m=e.message))
        sys.exit(2)
