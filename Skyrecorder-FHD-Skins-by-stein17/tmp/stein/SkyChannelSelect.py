#-*- coding: utf-8 -*-
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
from SkyChannelEditor import SkyChannelEditor
from SkySql import *


class SkyChannelSelect(Screen):
	
	def __init__(self, session):
		self.session = session
		
		path = "%s/skins/%s/screen_channel_select.xml" % (getPluginPath(), config.plugins.skyrecorder.anytime_skin.value)
		with open(path, "r") as f:
			self.skin = f.read()
			f.close()
			
		Screen.__init__(self, session)
		
		pluginName = config.plugins.skyrecorder.pluginname.value
		contentSize = config.plugins.skyrecorder.contentsize.value
		
		self["actions"] = ActionMap(["OkCancelActions", "ShortcutActions", "EPGSelectActions", "WizardActions", "ColorActions", "NumberActions", "MenuActions", "MoviePlayerActions"], {
			"ok": self.keyOK,
			"cancel": self.keyCancel,
			"green": self.keyChange
		}, -1)
				
		self.channelliste = []
		self.streamMenuList = MenuList([], enableWrapAround=True, content=eListboxPythonMultiContent)
		self.streamMenuList.l.setFont(0, gFont('Regular', 30))
		self.streamMenuList.l.setItemHeight(75)
		self['channelselect'] = self.streamMenuList
		
		self.sky_channel_path = "/usr/lib/enigma2/python/Plugins/Extensions/skyrecorder/sky_channels"
		self.sky_channel_path_tmp = "/usr/lib/enigma2/python/Plugins/Extensions/skyrecorder/sky_channels.tmp"
		
		self.last_index = 0
		
		self.onLayoutFinish.append(self.readChannels)
	
	def skyChannelSelectListEntry(self, entry):
		if entry[1] == "True":
			plus = "/usr/lib/enigma2/python/Plugins/Extensions/skyrecorder/images/plus.png"
			return [entry,
				(eListboxPythonMultiContent.TYPE_PIXMAP_ALPHATEST, 15, 5, 40, 18, LoadPixmap(plus)),
				(eListboxPythonMultiContent.TYPE_TEXT, 50, 0, 850, 45, 0, RT_HALIGN_LEFT, str(entry[0]))
				]
		else:
			minus = "/usr/lib/enigma2/python/Plugins/Extensions/skyrecorder/images/minus.png"
			return [entry,
				(eListboxPythonMultiContent.TYPE_PIXMAP_ALPHATEST, 15, 5, 40, 18, LoadPixmap(minus)),
				(eListboxPythonMultiContent.TYPE_TEXT, 50, 0, 850, 45, 0, RT_HALIGN_LEFT, str(entry[0]))
				]
			
	def readChannels(self):
		try:
			sql.cur.execute('SELECT SQLITE_VERSION()')
		except Exception:
			sys.exc_clear()
			try:
				sql.connect()
			except Exception:
				return
		
		self.channelliste = []
		for (channel, status) in sql.readChannel():
			self.channelliste.append((channel, status))
		print "[skyrecorder] reload channelSelectListe."
		self.channelliste.sort()
		self.streamMenuList.setList(map(self.skyChannelSelectListEntry, self.channelliste))
		if self.last_index < len(self.channelliste):
			self['channelselect'].moveToIndex(self.last_index)
			#self['channelselect'].selectionChanged()
		
	def keyChange(self):
		print "change"
		self.last_index = self['channelselect'].getSelectionIndex()
		self.session.openWithCallback(self.readChannels, SkyChannelEditor, self.last_index)
		
	def keyOK(self):
		exist = self['channelselect'].getCurrent()
		if exist == None:
			return

		channel_auswahl = self['channelselect'].getCurrent()[0][0]
		self.last_index = self['channelselect'].getSelectionIndex()
		print channel_auswahl
		sql.changeChannel(channel_auswahl)
		self.readChannels()
		
	def keyCancel(self):
		self.close()

