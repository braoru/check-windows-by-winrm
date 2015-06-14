# check-windows-by-winrm
Windows check by winrm codebase

#Information

Currently it's only tested with SSL+BasicAuth on 2012R2

##Install check

```Bash
git clone git@git.internal.leshop.ch:IO/check-windows-by-winrm.git
virtualenv check-windows-by-winrm
cd check-windows-by-winrm
source bin/activate
pip install http://github.com/diyan/pywinrm/archive/master.zip
pip install --upgrade pip
pip install -r requirement.txt

```

##Install custom self-signed unsecure anchor

```Bash
#Install the ca-certificates package:
yum install ca-certificates

#Enable the dynamic CA configuration feature:
update-ca-trust enable

#Add it as a new file to /etc/pki/ca-trust/source/anchors/:
cp my_ca_file.crt /etc/pki/ca-trust/source/anchors/

#Then break your security model
update-ca-trust extract

```

##Prerequisites for windows 2008 R2
- Dotnet 4.5 (https://www.microsoft.com/fr-fr/download/details.aspx?id=30653)
- Windows Management Framework 4 (http://www.microsoft.com/fr-fr/download/details.aspx?id=40855 - Windows6.1-KB2819745-x64-MultiPkg.msu)

##Enable auth on Windows 2008 R2 and 2012r2 +
```PowerShell
winrm set winrm/config/client/auth @{Basic="true"}
winrm set winrm/config/service/auth @{Basic="true"}

```

