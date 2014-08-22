honeypot-ssh
============

SSH Honeypot

Features:
 * SSH with simple Linux-OS
 * Catch used credentials
 * Catch actions

Dependencies:
 * Twisted
 * PyCrypto
 * My site-packages(3) --> common-modules

Usage:
```bash
# Generate Config
python ssh.py -d config.xml
# Run
python ssh.py
```

TODO:
 * Implement OS-neutral solution (linux, windows, ...)
 * merge logic with my telnet-honeypot
 * implement more interactions (wget, curl, pipe, ...)
 
Contributions welcome.

All rights reserved.
(c) 2014 by Alexander Bredo