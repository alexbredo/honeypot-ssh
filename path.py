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


import sys
import xml.etree.ElementTree as ET
from xml.etree.ElementTree import SubElement

class Path(object):
	currentPath = []

	def __init__(self, xmlfile):
		self.tree = ET.parse(xmlfile)
		self.root = self.tree.getroot()

	def whoami(self):
		return "root"

	def pwd(self):
		return '/' + '/'.join(self.currentPath)

	def cd(self, arg='.'):
		arg = arg.strip()
		
		#try:
		if arg == '..':
			self.currentPath.pop()
		elif arg == '/':
			self.currentPath = []
		elif arg.startswith('/'):
			newpath = []
			newpath += arg[1:].split('/')
			if self.__getFolder(newpath) is None:
				return "-bash: cd: %s: Datei oder Verzeichnis nicht gefunden" % arg
			else:
				self.currentPath = newpath
		else:
			folders = arg.split('/')
			newpath = self.currentPath + folders
			if self.__getFolder(newpath) is None:
				return "-bash: cd: %s: Datei oder Verzeichnis nicht gefunden" % arg
			else:
				self.currentPath = newpath
		#except:
		#	print "eerr"
		#	pass

	def dir(self, arg='.'):
		return self.ls(arg)

	def ls(self, arg='.'):
		arg = arg.strip()
		result = ''
		for child in self.__getFolder(self.currentPath).findall('./'):
			result += child.attrib['name'] + '\n'
		return result

	def mkdir(self, arg):
		attrib = {'name': arg, 'user': 'root', 'group': 'root', 'filesize': "4096", 'mode': 'drwxr-xr-x', 'date': "10. Sep 11:39"}
		child = SubElement(self.__getFolder(self.currentPath), 'folder', attrib)

	def touch(self, arg):
		attrib = {'name': arg, 'user': 'root', 'group': 'root', 'filesize': "0", 'mode': '-rw-r--r--', 'date': "10. Sep 11:39"}
		child = SubElement(self.__getFolder(self.currentPath), 'file', attrib)

	def which(self, arg):
		executable = self.__getFolder(['bin']).find("./file[@name='%s']" % arg)
		if executable is not None:
			return '/bin/%s' % arg

	def tryRunExecutable(self, arg):
		if arg.startswith('./'):
			return "-bash: %s: Keine Berechtigung" % arg
		try: 
			executable = self.__getFolder(['bin']).find("./file[@name='%s']" % arg)
			if executable is not None:
				try:
					return executable.text.strip()
				except:
					return "-bash: fork: Cannot allocate memory" # Bäh :-)
			else:
				executable = self.__getFolder(['usr', 'bin']).find("./file[@name='%s']" % arg)
				if executable is not None:
					try:
						return executable.text.strip()
					except:
						return "3 [main] bash 2216 child_info_fork::abort: data segment start: parent(0x26D000) != child(0x38D000)" # Bäh :-)
			return "-bash: %s: Kommando nicht gefunden." % arg
		except:
			return "-bash: %s: Datei oder Verzeichnis nicht gefunden" % arg

	def cat(self, arg):
		file = self.__getFile(arg)
		if file is not None:
			return file.text.strip()
		else:
			return "cat: %s: Datei oder Verzeichnis nicht gefunden" % arg

	def echo(self, arg):
		return arg

	def rm(self, arg):
		cf = self.__getFolder(self.currentPath)
		item = cf.find("./*[@name='%s']" % arg)
		if item is not None:
			cf.remove(item)
		else:
			return "rm: Entfernen von %s nicht moeglich: Datei oder Verzeichnis nicht gefunden" % arg

	def __getFolder(self, path):
		try:
			if path:
				xpathfolder = './' + '/'.join([("folder[@name='" + item + "']") for item in path])
				return self.root.find(xpathfolder)
			else:
				return self.root
		except:
			return self.root

	def __getFile(self, file):
		return self.__getFolder(self.currentPath).find("./file[@name='%s']" % file)

def main():
	p = Path()
	cmd = raw_input('$ ').strip()
	while (cmd not in ['exit', 'quit']):
		try:
			scmd = cmd.split(' ')
			if len(scmd) >= 2:
				result = getattr(p, scmd[0].strip())(scmd[1].strip())
			else:
				if len(scmd[0].strip()) != 0:
					result = getattr(p, scmd[0].strip())()
				else:
					result = ''
			if result:
				print result
		except AttributeError:
			print p.tryRunExecutable(scmd[0].strip())
		try:
			cmd = raw_input('$ ').strip()
		except KeyboardInterrupt:
			sys.exit(0) # temp

if __name__ == '__main__':
	main()
