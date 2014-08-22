#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Copyright (c) 2014 Alexander Bredo
# All rights reserved.
# 
# Redistribution and use in source and binary forms, with or 
# without modification, are permitted provided that the 
# following conditions are met:
# 
# 1. Redistributions of source code must retain the above 
# copyright notice, this list of conditions and the following 
# disclaimer.
# 
# 2. Redistributions in binary form must reproduce the above 
# copyright notice, this list of conditions and the following 
# disclaimer in the documentation and/or other materials 
# provided with the distribution.
# 
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND 
# CONTRIBUTORS "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, 
# INCLUDING, BUT NOT LIMITED TO, THE IMPLIED WARRANTIES OF 
# MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE 
# DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR 
# CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, 
# INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES 
# (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE 
# GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR 
# BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF 
# LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT 
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT 
# OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE 
# POSSIBILITY OF SUCH DAMAGE.

'''
Dependencies: Twisted, PyCrypto
'''

from twisted.cred import portal 
from twisted.conch import error, avatar, recvline, interfaces as conchinterfaces
from twisted.conch.ssh import factory, session
from twisted.conch.insults import insults
from zope.interface import implements
from twisted.conch.ssh.keys import Key
from twisted.cred.portal import Portal
from twisted.cred.checkers import FilePasswordDB
from twisted.internet import reactor
import os, sys, time
from path import Path

from base.applog import *
from base.appconfig import Configuration
from handler.manager import HandlerManager

class SSHConfig(Configuration):
	def setup(self, *args, **kwargs): # Defaults: 
		self.__version = '0.1.0'
		self.__appname = 'honeypot_ssh'
		self.port=22
		self.passwdfile='passwd'
		self.keyprivate='keys/id_rsa'
		self.keypublic='keys/id_rsa.pub'
		self.filesystem='filesystem.xml'
		self.enabled_handlers = {
			'elasticsearch': True, 
			'screen': True,
			'file': True
		}
		self.elasticsearch = {
			'host': '127.0.0.1', 
			'port': 9200, 
			'index': 'honeypot'
		}
		self.filename = 'honeypot_output.txt'
		
config = SSHConfig()
handler = HandlerManager(config)
clientip = '0.0.0.0' # ugly global (todo)

def logInfo(type, command, successful=True):
	data = {
		'module': 'SSH', 
		'@timestamp': int(time.time() * 1000), # in milliseconds
		'sourceIPv4Address': clientip, 
		'sourceTransportPort': config.port,
		'type': type,
		'command': command, 
		'success': successful
	}
	handler.handle(data)
		
with open(os.path.join(os.path.dirname(sys.argv[0]), config.keyprivate)) as privateBlobFile:
	privateBlob = privateBlobFile.read()
	privateKey  = Key.fromString(data=privateBlob)

with open(os.path.join(os.path.dirname(sys.argv[0]), config.keypublic)) as publicBlobFile:
	publicBlob = publicBlobFile.read()
	publicKey  = Key.fromString(data=publicBlob)
	
class SSHDemoProtocol(recvline.HistoricRecvLine):
	def __init__(self, user):
		self.user = user
		self.pseudosys = Path(config.filesystem)

	def connectionMade(self):
		welcomeMessage = '''Linux www01-master 2.6.32-5-amd64 #1 SMP Fri May 10 08:43:19 UTC 2013 x86_64

GNU/Linux comes with ABSOLUTELY NO WARRANTY, to the extent permitted by applicable law.
Last login: Tue Sep 10 13:40:21 2013 from support.microsoft.com'''
		recvline.HistoricRecvLine.connectionMade(self)
		self.terminal.write(welcomeMessage)
		self.terminal.nextLine()
		self.showPrompt()

	def showPrompt(self):
		self.terminal.write(self.pseudosys.whoami() + ":" + self.pseudosys.pwd() + "# ")

	def lineReceived(self, line):
		line = line.strip()
		logInfo('shell', line)
		if line:
			if line in ['exit', 'quit']:
				self.terminal.write("Abgemeldet.")
				self.terminal.nextLine()
				self.terminal.loseConnection()
			elif line == 'clear':
				self.terminal.reset()
			else:
				try:
					scmd = line.split(' ')
					if len(scmd) >= 2:
						result = getattr(self.pseudosys, scmd[0].strip())(scmd[1].strip())
					else:
						if len(scmd[0].strip()) != 0:
							result = getattr(self.pseudosys, scmd[0].strip())()
						else:
							result = ''
					if result:
						self.terminal.write(result.encode('utf-8'))
						self.terminal.nextLine()
				except AttributeError:
					self.terminal.write(self.pseudosys.tryRunExecutable(scmd[0].strip()).encode('utf-8'))
					self.terminal.nextLine()
		self.showPrompt()

class MyAvatar(avatar.ConchUser):
	implements(conchinterfaces.ISession)

	def __init__(self, username):
		avatar.ConchUser.__init__(self)
		self.username = username
		self.channelLookup.update({'session':session.SSHSession})

	def openShell(self, protocol):
		serverProtocol = insults.ServerProtocol(SSHDemoProtocol, self)
		serverProtocol.makeConnection(protocol)
		protocol.makeConnection(session.wrapProtocol(serverProtocol))

	def getPty(self, terminal, windowSize, attrs):
		return None

	def execCommand(self, protocol, cmd):
		raise NotImplementedError

	def closed(self):
		pass
		
	def eofReceived(self):
		logInfo('disconnected', '')
		
class MyRealm:
	implements(portal.IRealm)
	def requestAvatar(self, avatarId, mind, *interfaces):
		return interfaces[0], MyAvatar(avatarId), lambda: None
		
class MySSHFactory(factory.SSHFactory):
	def buildProtocol(self, addr):
		global clientip # Hack, Dirty, Ugly, Buh
		clientip = addr.host
		logInfo('connected', addr.host)
		return factory.SSHFactory.buildProtocol(self, addr)
		
class MyFilePasswordDB (FilePasswordDB):
	def requestAvatarId(self, c):
		logInfo('authentication', 'Credentials: %s:%s' % (c.username, c.password))
		return FilePasswordDB.requestAvatarId(self,c)

if __name__ == "__main__":
	try:
		sshFactory = MySSHFactory()
		sshFactory.portal = Portal(MyRealm())
		sshFactory.portal.registerChecker(MyFilePasswordDB(config.passwdfile))

		sshFactory.privateKeys = { 'ssh-rsa': privateKey }
		sshFactory.publicKeys  = { 'ssh-rsa': publicKey  }

		reactor.listenTCP(
			config.port, 
			sshFactory
		)
		log.info('Server listening on Port %s.' % config.port)
		reactor.run()
	except Exception, e:
		log.error(str(e));
	log.info('Server shutdown.')