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
import collections
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
    from winrm_checks import OutputFormatHelpers, PowerShellHelpers, WindowsSystemHelpers
except ImportError:
    print "ERROR : this plugin needs the local winrm lib. Please install it"
    sys.exit(2)

#DEFAULT LIMITS
#--------------
DEFAULT_WARNING = 80.0
DEFAULT_CRITICAL = 90.0


def disk_capacity_array_to_object(
        disk_array,
        element_to_discard
    ):
        #If there is only one element, cast as an array
        if not isinstance(disk_array, list):
            disk_array = [disk_array]

        return {
            element['Label']: {
                "Capacity(GB)": element['FreeSpace(GB)'],
                "FreeSpace(GB)": element['FreeSpace(GB)'],
                "Used(%)": element['Used(%)']
            } for element in disk_array if element['Label'] not in element_to_discard and element['Label'] is not None
        }

def disk_elements_labels_filtering(
    disk_elements,
    labels
):
    return {
        label: disk_elements[label] for label in disk_elements.keys() if label in labels
    }


def disk_elements_threshold_filtering(
    disk_elements,
    threshold
):

    return {
        label : disk_usage_info 
        for label,disk_usage_info in disk_elements.items() if disk_usage_info['Used(%)'] >= threshold
    }    


# OPT parsing
# -----------
parser = optparse.OptionParser(
    "%prog [options]", version="%prog " + version)
usage = """%prog [options]

Monitor mounted disk without drive letter assigned
"""
parser = WindowsSystemHelpers.add_winrm_parser_options(parser)

parser.add_option('-w', '--warning',
                  dest="warning", type="float",
                  help='Warning value for disk usage. In [%]. Default : 80.0 [%]')
parser.add_option('-c', '--critical',
                  dest="critical", type="float",
                  help='Critical value for disk usage. In [%]. Default : 90.0 [%]')
parser.add_option('--disk-labels',
                  dest="labels", 
                  help='Disk labels to check on a comma separated list: "a,b,c"')


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
    labels = opts.labels
    if opts.labels is not None:
        labels = opts.labels.split(',')


    # Try to get numeric warning/critical values
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

        #prepare the script
        executable_ps_script = PowerShellHelpers.generate_ps(
            WindowsSystemHelpers.PS_SCRIPT_MOUNTED_VOLUME            
        )

        if debug:
            print("Script to execute")
            print("-----------------")
            print(executable_ps_script)

        #execute the scripte
        disk_usage = PowerShellHelpers.ececute_powershell(
            client,
            executable_ps_script,
            debug
        )

        if debug:
            print("check output")
            print("------------")
            pprint(disk_usage)

       
        #Prepare all the datas
        #---------------------
        disk_usage_dict = disk_capacity_array_to_object(
            disk_array=disk_usage,
            element_to_discard=['System Reserved']
        )

        #check logic
        #-----------

        #filter on labels
        if labels is not None:
            disk_usage_dict = disk_elements_labels_filtering(disk_usage_dict,labels)

        #filter for  >= critical
        disks_critical = disk_elements_threshold_filtering(
            disk_elements=disk_usage_dict,
            threshold=s_critical
        )

        #filter for >= warning disk
        disks_warning = disk_elements_threshold_filtering(
            disk_elements=disk_usage_dict,
            threshold=s_warning
        )

        #prepare check output
        #--------------------
        status = 'OK'
        disk_report_message_format="[{l}] usage >= {t}%"
        message="All mounted disk usage within the limits"

        if len(disks_warning):
            status='Warning'
            message_content = ''.join(' {s} '.format(s=label) for label in disks_warning.keys())
            message=disk_report_message_format.format(
                l=message_content,
                t=s_warning
            )

        if len(disks_critical):
            status='Critical'
            message_content = ''.join(' {s} '.format(s=label) for label in disks_critical.keys())
            message=disk_report_message_format.format(
                l=message_content,
                t=s_critical
            )


        #Assembly perf data string
        #-------------------------
        perf_datas = []
        for label,element in disk_usage_dict.items():
            perf_datas.append(
                OutputFormatHelpers.perf_data_string(
                    label="{t}_usage".format(t=label),
                    value=element['Used(%)'],
                    warn=s_warning,
                    crit=s_critical,
                    min='0.0',
                    max='100.0',
                    UOM='%'
                )
            )

        #print output
        #------------
        output = OutputFormatHelpers.check_output_string(
                    status,
                    message,
                    perf_datas
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

