#-*- coding: utf-8 -*-
from Screens.VirtualKeyBoard import VirtualKeyBoard
from Screens.Screen import Screen
from Tools.Directories import fileExists, resolveFilename, SCOPE_PLUGINS
from enigma import gFont, eListboxPythonMultiContent, RT_HALIGN_LEFT, RT_HALIGN_RIGHT, RT_HALIGN_CENTER, RT_VALIGN_CENTER
from Components.ActionMap import NumberActionMap, ActionMap
from Components.MenuList import MenuList
from Components.Button import Button
from Components.Label import Label
from Tools.LoadPixmap import LoadPixmap
from Components.config import config
import re
import shutil
import os
import sys

# our custom classes
from SkyMainFunctions import getPluginPath
from SkySql import *

class SkySkipWordsSelect(Screen):
	
	def __init__(self, session):
		self.session = session
		
		path = "%s/skins/%s/screen_skipwords.xml" % (getPluginPath(), config.plugins.skyrecorder.anytime_skin.value)
		with open(path, "r") as f:
			self.skin = f.read()
			f.close()
			
		Screen.__init__(self, session)
		
		pluginName = config.plugins.skyrecorder.pluginname.value
		contentSize = config.plugins.skyrecorder.contentsize.value

		self["actions"] = ActionMap(["OkCancelActions", "ShortcutActions", "EPGSelectActions", "WizardActions", "ColorActions", "NumberActions", "MenuActions", "MoviePlayerActions"], {
			"ok": self.keyOK,
			"cancel": self.keyCancel,
			"green": self.keyAdd,
			"red": self.keyDel,
		}, -1)
				
		self.skipwordliste = []
		self.streamMenuList = MenuList([], enableWrapAround=True, content=eListboxPythonMultiContent)
		self.streamMenuList.l.setFont(0, gFont('Regular', 30))
		self.streamMenuList.l.setItemHeight(75)
		self['skipwordselect'] = self.streamMenuList
		
		self.sky_skipwords_path = "/usr/lib/enigma2/python/Plugins/Extensions/skyrecorder/sky_skipwords"
		self.sky_skipwords_path_tmp = "/usr/lib/enigma2/python/Plugins/Extensions/skyrecorder/sky_skipwords.tmp"
	
		self.onLayoutFinish.append(self.readSkipWords)
	
	
	def skySkipWordSelectListEntry(self, entry):
		if entry[1] == "True":
			plus = "/usr/lib/enigma2/python/Plugins/Extensions/skyrecorder/images/plus.png"
			return [entry,
				(eListboxPythonMultiContent.TYPE_PIXMAP_ALPHATEST, 15, 5, 20, 18, LoadPixmap(plus)),
				(eListboxPythonMultiContent.TYPE_TEXT, 50, 0, 850, 25, 0, RT_HALIGN_LEFT, str(entry[0]))
				]
		else:
			minus = "/usr/lib/enigma2/python/Plugins/Extensions/skyrecorder/images/minus.png"
			return [entry,
				(eListboxPythonMultiContent.TYPE_PIXMAP_ALPHATEST, 15, 5, 20, 18, LoadPixmap(minus)),
				(eListboxPythonMultiContent.TYPE_TEXT, 50, 0, 850, 25, 0, RT_HALIGN_LEFT, str(entry[0]))
				]
	
	def readSkipWords(self):
		try:
			sql.cur.execute('SELECT SQLITE_VERSION()')
		except Exception:
			sys.exc_clear()
			try:
				sql.connect()
			except Exception:
				return
		
		self.skipwordliste = []
		for (skipword, status) in sql.readSkipSelect():
			self.skipwordliste.append((skipword, status))
		print "[skyrecorder] reload skips."
		self.skipwordliste.sort()
		self.streamMenuList.setList(map(self.skySkipWordSelectListEntry, self.skipwordliste))
	
	
	def keyOK(self):
		exist = self['skipwordselect'].getCurrent()
		if exist == None:
			return
		skipword_auswahl = self['skipwordselect'].getCurrent()[0][0]
		print skipword_auswahl
		sql.changeSkip(skipword_auswahl)
		self.readSkipWords()
		
		#exist = self['skipwordselect'].getCurrent()
		#if exist == None:
		#	return

	def keyAdd(self):
		print "add"
		self.session.openWithCallback(self.addSkipWord, VirtualKeyBoard, title=("Skip word eintragen:"))

	def addSkipWord(self, word=None):
		if word != None or word == "":
			sql.addSkip(word)
			print "[skyrecorder] add skip: %s" % word
		self.readSkipWords()
	
	def keyDel(self):
		exist = self['skipwordselect'].getCurrent()
		if exist == None:
			return
		skipword_auswahl = self['skipwordselect'].getCurrent()[0][0]
		sql.delSkip(skipword_auswahl)
		print "[skyrecorder] del skip: %s" % skipword_auswahl
		self.readSkipWords()
		
		#print "del"
		#exist = self['skipwordselect'].getCurrent()
		#if exist == None:
		#	return
			
	def keyCancel(self):
		self.close()

