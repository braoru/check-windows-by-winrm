# -*- coding: utf-8 -*-

# Copyright (C) 2013:
#     Sébastien Pasche, sebastien.pasche@leshop.c
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
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMEsNT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
# FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER
# DEALINGS IN THE SOFTWARE.
#

author = "Sebastien Pasche"
maintainer = "Sebastien Pasche"
version = "0.0.1"

import json
import base64
import optparse
from pprint import pprint

class PowerShellHelpers(object):


    @classmethod
    def ececute_powershell(
            cls,
            client,
            script,
            debug=False
    ):
        """
        Execute powershel `script` on `client`
        This function is build to receive Base64(Json(data)) output from the
            powershell script
        :param client: connection
        :type client: pywinrm object
        :param script: powershell script to execute
        :type script: str
        :return: Dict with returned values
        """
        response = client.run_ps(script)

        if debug:
            print("raw output")
            print("----------")
            print(response)
            print(response.std_err)

        if not response:
            raise Exception("cannot fetch values from host")
        #normalize result
        result = base64.decodestring(response.std_out)
        #pprint(result)
        result = json.loads(result)
        #pprint(result)
        return result

    PS_INPUT_JSON = """
#Format input
$CheckInputJsonBytes = [System.Convert]::FromBase64String("{data}")
$CheckInputJson = [System.Text.Encoding]::UTF8.GetString($CheckInputJsonBytes)
$CheckInputDaTa = $CheckInputJson | ConvertFrom-Json
"""

    @classmethod
    def generate_ps(
            cls,
            script,
            input_data={}
    ):
        """
        Generate the powershell script by resolving `{palceholder}` with `input_data` and
        Constant {placeholéder}
        :param input_data: data to include within the script
        :type input_data: Dict
        :param script: The powershell script
        :type script: str
        :return: Fullfiled script
        """
        output_script = script
        
        json_data = json.dumps(
            input_data,
            sort_keys=True
        )
        
        json_data = base64.encodestring(json_data)
        data_string = cls.PS_INPUT_JSON.format(data=json_data)

        output_script = output_script.format(
            check_input_json=data_string
        )

        return output_script


class WindowsSystemHelpers(object):

    PS_SCRIPT_MOUNTED_VOLUME = """
#Functions
#---------

#check input data
#----------------
{check_input_json}


#Obtain data
#-----------
$TotalGB = @{{Name="Capacity(GB)";expression={{[math]::round(($_.Capacity/ 1073741824),2)}}}}
$FreeGB = @{{Name="FreeSpace(GB)";expression={{[math]::round(($_.FreeSpace / 1073741824),2)}}}}
$UsedPerc = @{{Name="Used(%)";expression={{[math]::round(((($_.Capacity / 1073741824)-($_.FreeSpace / 1073741824))/($_.Capacity / 1073741824)*100),0)}}}}

$volumes = Get-WmiObject win32_volume | Where-object {{$_.DriveLetter -eq $null}}
$CheckOutputObj = $volumes | Select  Label, $TotalGB, $FreeGB, $UsedPerc

#Format output
$CheckOuputJson = $CheckOutputObj | ConvertTo-Json
$CheckOuputJsonBytes  = [System.Text.Encoding]::UTF8.GetBytes($CheckOuputJson)
$CheckOuputJsonBytesBase64 = [System.Convert]::ToBase64String($CheckOuputJsonBytes)
Write-Host $CheckOuputJsonBytesBase64
"""

    @classmethod
    def add_winrm_parser_options(
        cls,
        parser
    ):
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
        return parser

class MSSQLHelpers(object):

    PS_SCRIPT_MSSQL_QUERY = """
#Functions
#---------

#check input data
#----------------
{check_input_json}

#Obtain data
#-----------
Import-Module sqlps -WarningAction Ignore
$CheckOutputObj = Invoke-Sqlcmd -Query $CheckInputDaTa.sql_script -SuppressProviderContextWarning  -serverInstance ("localhost\\" + $CheckInputDaTa.mssqlinstance_to_check) | foreach-object {{$_.nb_db_errors}}
$CheckOutputObj = [double]$CheckOutputObj
#Format output
$CheckOuputJson = $CheckOutputObj | ConvertTo-Json
$CheckOuputJsonBytes  = [System.Text.Encoding]::UTF8.GetBytes($CheckOuputJson)
$CheckOuputJsonBytesBase64 = [System.Convert]::ToBase64String($CheckOuputJsonBytes)
Write-Host $CheckOuputJsonBytesBase64
"""


    PS_SCRIPT_MSSQL_COUNTER = """
#Functions
#---------

#check input data
#----------------
{check_input_json}

#Obtain data
#-----------
$CheckOutputObj = Get-counter -Counter ("\MSSQL`$" + $CheckInputDaTa.mssqlinstance_to_check + $CheckInputDaTa.perfcounter_to_check) | Select-Object -ExpandProperty CounterSamples | foreach {{$_.CookedValue}}
#Format output
$CheckOuputJson = $CheckOutputObj | ConvertTo-Json
$CheckOuputJsonBytes  = [System.Text.Encoding]::UTF8.GetBytes($CheckOuputJson)
$CheckOuputJsonBytesBase64 = [System.Convert]::ToBase64String($CheckOuputJsonBytes)
Write-Host $CheckOuputJsonBytesBase64
"""


    @classmethod
    def add_mssql_perfmon_parser_options(
            cls,
            parser
    ):
       
        parser.add_option('--property',
                          dest="property_script", default=None,
                          help='property id to display')
        parser.add_option('-I',
                          dest="mssqlinstance_to_check", default="MSSQLSERVER",
                          help='MSSQL Instance to check')

        return parser



class OutputFormatHelpers(object):

    @classmethod
    def perf_data_string(
            cls,
            label,
            value,
            warn,
            crit,
            UOM='',
            min='',
            max=''

    ):
        """
        Generate perf data string from perf data input
        http://docs.icinga.org/latest/en/perfdata.html#formatperfdata
        :param label: Name of the measured data
        :type label: str
        :param value: Value of the current measured data
        :param warn: Warning level
        :param crit: Critical level
        :param UOM: Unit of the value
        :param min: Minimal value
        :param max: maximal value
        :return: formated perf_data string
        """
        if UOM:
            perf_data_template = "'{label}'={value}[{UOM}];{warn};{crit};{min};{max};"
        else:
            perf_data_template = "'{label}'={value};{warn};{crit};{min};{max};"

        return perf_data_template.format(
            label=label,
            value=value,
            warn=warn,
            crit=crit,
            UOM=UOM,
            min=min,
            max=max
        )

    @classmethod
    def check_output_string(
            cls,    
            state,
            message,
            perfdata
    ):
        """
        Generate check output string with perf data
        :param state: State of the check in  ['Critical', 'Warning', 'OK', 'Unknown']
        :type state: str
        :param message: Output message
        :type message: str
        :param perfdata: Array of perf data string
        :type perfdata: Array
        :return: check output formated string
        """
        if state not in  ['Critical', 'Warning', 'OK', 'Unknown']:
            raise Exception("bad check output state")

        if not message:
            message = '-'

        if perfdata is not None:
            if not hasattr(perfdata, '__iter__'):
                raise Exception("Submited perf data list is not iterable")
            perfdata_string = ''.join(' {s} '.format(s=data) for data in perfdata)
            output_template = "{s}: {m} |{d}"
        else:
            output_template = "{s}: {m} "
            perfdata_string = ''

        return output_template.format(
            s=state,
            m=message,
            d=perfdata_string
        )



#toujours_tout_en_minuscul
#sauf LeNomDesCLass
#et des CONSTANTE
#_PS_SCRIPT_COUNTER     

if __name__ == '__main__':
   pass