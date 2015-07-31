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

DEFAULT_OK = frozenset(
    [
        "Running"
    ]
)

START_MODE = frozenset(
    [
        'Auto'
    ]
)

AUTO_EXCLUDE_LIST = frozenset(
    [
        'sppsvc',
        'ShellHWDetection',
        'BMR Boot Service',
        'NetBackup SAN Client Fibre Transport Service',
        'clr_optimization',
        'Sophos Web Intelligence Update',
        'Check_MK_Agent',
        'TeamViewer9',
        'SysmonLog',
        'gupdate',
        'swi_update_64',
        'swi_service',
        'stisvc',
        'vimPBSM',
        'vimQueryService',
        'Citrix Licensing',
        'CitrixXenAppCommandsRemoting',
        'RemoteRegistry',
        'TrustedInstaller'

    ]
)

MANUAL_OK_EXIT_CODE = frozenset(
    [
        0,
        1077
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
$CheckOutputObj = Get-WmiObject -Class Win32_Service


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
parser.add_option('--debug',
                  dest="debug", default=False, action="store_true",
                  help='Enable debug')

parser.add_option('--manual-error-warning',
                  dest="manual_error_warning", default=False, action="store_true",
                  help='Warning if manual service have a non 0 exit code')
parser.add_option('--manual-error-critical',
                  dest="manual_error_critical", default=False, action="store_true",
                  help='Critical if manual service have a non 0 exit code')
parser.add_option('--manual-started-warning',
                  dest="manual_warning", default=False, action="store_true",
                  help='Warning if service started manualy')

parser.add_option('--auto-exclude-list',
                  dest="auto_exclude_list", default='',
                  help='Service name to exclude from automatic but not running service list to check. '
                       'Define service list as a space delimited list. Ex: "service_a service_b"')
parser.add_option('--auto-include-list',
                  dest="auto_include_list", default='',
                  help='Service name to include into automatic but not running service list to check. '
                       'Define service list as a space delimited list. Ex: "service_d service_e"')


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

    #manual service check options
    manual_error_warning = opts.manual_error_warning
    manual_error_critical = opts.manual_error_critical
    manual_warning = opts.manual_warning

    #automatic services list
    auto_exclude_list = opts.auto_exclude_list.split(' ')
    auto_include_list = opts.auto_include_list.split(' ')

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
        services_state = PowerShellHelpers.ececute_powershell(
            client,
            executable_ps_script,
            debug
        )
        if debug:
            print("check output")
            print("------------")
            pprint(services_state)

        messages = []

        #check logic
        status = 'OK'
        service_message = "{mode} {name} current state is {state}"

        #manual services check_logic
        #---------------------------
        manual_services_list = [
            service for service in services_state if service['StartMode'] == 'Manual'
        ]
        manual_services_running_list = [
            service for service in manual_services_list if service['State'] in DEFAULT_OK
        ]
        manual_services_error_list = [
            service for service in manual_services_list if service['ExitCode'] not in MANUAL_OK_EXIT_CODE
        ]

        if manual_error_warning and len(manual_services_running_list) >= 1:
            status = 'Warning'

            for service in manual_services_running_list:
                messages.append(service_message.format(
                    mode='Manual',
                    name=service['Name'],
                    state=['running']
                ))

        if (manual_error_warning or manual_error_critical) and len(manual_services_error_list) >= 1:
            for service in manual_services_error_list:
                messages.append(service_message.format(
                    mode='Manual',
                    name=service['Name'],
                    state='ExitCode {e}'.format(e=service['ExitCode'])
                ))

            if manual_error_warning:
                status = 'Warning'

            if manual_error_critical:
                status = 'Critical'

        #automatic services check logic
        #------------------------------
        auto_exclude_list = AUTO_EXCLUDE_LIST.union(
            auto_include_list
        ).difference(
            auto_exclude_list
        )

        if debug:
            print("Automatic service exclusion list")
            print("--------------------------------")
            pprint(auto_exclude_list)

        auto_not_started_services_list = [service for service in services_state if (
            service['StartMode'] == 'Auto' and
            service['Name'] not in auto_exclude_list and
            service['State'] not in DEFAULT_OK
        )]

        if len(auto_not_started_services_list) >= 1:
            status = 'Critical'
            for service in auto_not_started_services_list:
                messages.append(service_message.format(
                    mode='Auto',
                    name=service['Name'],
                    state='not running'
                ))

        #formating output
        if len(messages) > 0:
            message = ','.join(messages)
        else:
            message = 'Everything fine'

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

    finally:
        if status == "Critical":
            sys.exit(2)
        if status == "Warning":
            sys.exit(1)
        sys.exit(0)
