#! /usr/bin/python
# -*- coding: utf-8; -*-

"""

Script for running on computers controlling TV screens. Currently
limited to Mac OS X.

"""

# Limit access by IP address
authorizedIPs = ["158.39.172.235", "158.39.165.66"]

# Host and port. Use host = "" to listen on all interfaces
host = ""
port = 9519

# End of configuration
########################################################################

import SocketServer, sys, time, subprocess, os

class TVControlServer(SocketServer.TCPServer):
    allow_reuse_address = True

    vlcSocketPath = '/tmp/.tvcontrol'

    def StartVLC(self):
        "For starting or restarting VLC"

        cmd = ('/Applications/VLC.app/Contents/MacOS/VLC', '--extraintf=rc', '-vvv', '--rc-unix=%s' % self.vlcSocketPath)

        self.vlcProc = subprocess.Popen(cmd, stderr = subprocess.PIPE) #, stdin = subprocess.PIPE, stdout = subprocess.PIPE, stderr = subprocess.PIPE)

    def ShowVLC(self, visible = True):
        "To show or hide VLC's GUI"

        if visible:
            visibleString = "true"
        else:
            visibleString = "false"

        cmd = ('osascript')
        proc = subprocess.Popen(cmd, stdin = subprocess.PIPE, stdout = subprocess.PIPE, stderr = subprocess.PIPE)
        stdout, stderr = proc.communicate('tell application "System Events"\nset visible of process "VLC" to %s\nend tell\n' % visibleString)

    def SendVLCCommand(self, command):
        f = 1

    def __init__(self, address, handler):
        SocketServer.TCPServer.__init__(self, address, handler)

        self.StartVLC()
        self.ShowVLC(False)

    def verify_request(self, req, client_address):
        if client_address[0] in authorizedIPs:
            return True
        else:
            sys.stderr.write("Warning: Ignored connection from unauthorized host: %s\n" % client_address[0])
            return False

class TVControlHandler(SocketServer.StreamRequestHandler):
    def handle(self):
        command = self.rfile.readline().strip()
        
        now = time.time()
        nowS = time.strftime("%Y-%m-%d %H:%M:%S Z", time.gmtime(now))
        sys.stderr.write("-------- %s, from %s --------\n%s\n" % (nowS, self.client_address[0], command))

        # Handle custom commands for showing or hiding VLC's UI
        if command == "tv.show":
            self.server.ShowVLC()
        elif command == "tv.hide":
            self.server.ShowVLC(False)
        else:
            pass

def Main():
    server = TVControlServer((host, port), TVControlHandler)
    server.serve_forever()

if __name__ == "__main__":
    Main()
    
