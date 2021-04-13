#-*- coding: utf-8 -*-
from Screens.VirtualKeyBoard import VirtualKeyBoard
from Screens.Screen import Screen
from Screens.MessageBox import MessageBox
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
from SkyMainFunctions import getPluginPath, buildSkyChannellist
from SkySql import *

class SkyChannelEditor(Screen):
	
	def __init__(self, session, last_index):
		self.session = session
		self.last_index = last_index
		
		path = "%s/skins/%s/screen_channel_editor.xml" % (getPluginPath(), config.plugins.skyrecorder.anytime_skin.value)
		with open(path, "r") as f:
			self.skin = f.read()
			f.close()
			
		Screen.__init__(self, session)
		
		pluginName = config.plugins.skyrecorder.pluginname.value
		contentSize = config.plugins.skyrecorder.contentsize.value
		
		self.sky_chlist = buildSkyChannellist()

		self["actions"]  = ActionMap(["OkCancelActions", "ShortcutActions", "ColorActions", "MenuActions"], {
			"ok"    : self.keyOK,
			"cancel": self.keyCancel,
			"red": self.askDeleteChannels,
			"green": self.askDeleteChannel
		}, -1)
		
		
		self.channellist = []
		self.streamMenuList = MenuList([], enableWrapAround=True, content=eListboxPythonMultiContent)
		self.streamMenuList.l.setFont(0, gFont('Regular', 32))
		self.streamMenuList.l.setItemHeight(75)
		self['channeledit'] = self.streamMenuList
		
		self.sky_skipwords_path = "/usr/lib/enigma2/python/Plugins/Extensions/skyrecorder/sky_skipwords"
		self.sky_skipwords_path_tmp = "/usr/lib/enigma2/python/Plugins/Extensions/skyrecorder/sky_skipwords.tmp"
				
		self.onShown.append(self.readChannellist)
		#self.onLayoutFinish.append(self.readChannellist)
	
	
	def skyChannellistSelectListEntry(self,entry):
		# check, if channel_stb was found in servicelist
		if entry[3]:
			pic = "/usr/lib/enigma2/python/Plugins/Extensions/skyrecorder/images/plus.png"
		else:
			pic = "/usr/lib/enigma2/python/Plugins/Extensions/skyrecorder/images/minus.png"

		icon = LoadPixmap(pic)
		
		return [entry,
				(eListboxPythonMultiContent.TYPE_PIXMAP_ALPHATEST, 15, 5, 40, 18, icon),
				(eListboxPythonMultiContent.TYPE_TEXT, 50, 0, 475, 45, 0, RT_HALIGN_LEFT, str(entry[1])),
				(eListboxPythonMultiContent.TYPE_TEXT, 525, 0, 550, 45, 0, RT_HALIGN_LEFT, str(entry[2]))
				]

	
	def readChannellist(self):
		try:
			sql.cur.execute('SELECT SQLITE_VERSION()')
		except Exception:
			sys.exc_clear()
			try:
				sql.connect()
			except Exception:
				return
				
		self.channellist = []

		for (id_channel,channel,channel_stb,status,position,channel_id_sky) in sql.readChannelAll():
			# check, if channel_stb was found in servicelist
			if not channel_stb:
				continue
			if self.checkChannelByName(channel_stb):
				self.channellist.append((id_channel,channel,channel_stb,True))
			else:
				self.channellist.append((id_channel,channel,channel_stb,False))

		print "[skyrecorder] reload channellist."

		self.streamMenuList.setList(map(self.skyChannellistSelectListEntry, sorted(self.channellist, key=lambda s_channel: s_channel[1])))
		if self.last_index < len(self.channellist):
			self['channeledit'].moveToIndex(self.last_index)
			
	
	def checkChannelByName(self, channel):
		for (channelname,channelref) in self.sky_chlist:
			if channelname.lower() == channel.lower():
				return True
		return False
	
	def keyOK(self):
		exist = self['channeledit'].getCurrent()
		if exist == None:
			return
		self.id_channel = self['channeledit'].getCurrent()[0][0]
		channel_stb = self['channeledit'].getCurrent()[0][2]
		self.last_index = self['channeledit'].getSelectionIndex()
		if not channel_stb:
			return
		self.session.openWithCallback(self.changeChannelName, VirtualKeyBoard, title = ("Sendername eingeben, wie er\nin der STB-Kanalliste benannt ist:"), text = channel_stb)


	def changeChannelName(self, word):
		if not self.id_channel:
			return
		if word and len(word) > 0:
			sql.updateChannelnameSTB(self.id_channel,word)
			print "[skyrecorder] channel_stb changed: %s" % word
		self.readChannellist()


	def askDeleteChannel(self):
		exist = self['channeledit'].getCurrent()
		if exist == None:
			return
		self.id_channel = self['channeledit'].getCurrent()[0][0]
		self.last_index = self['channeledit'].getSelectionIndex()
		mymsg = "Eintrag wirklich löschen?"
		self.session.openWithCallback(self.deleteChannel,  MessageBox, _(mymsg), MessageBox.TYPE_YESNO, timeout=-1, default=False)
	
	def deleteChannel(self,cleanUp=False):
		if cleanUp is not True:
			return
		sql.deleteChannel(self.id_channel)
		self.readChannellist()


	def askDeleteChannels(self):
		exist = self['channeledit'].getCurrent()
		if exist == None:
			return
		mymsg = "Soll die Senderliste zurückgesetzt werden?\n\nHinweis:\nDie Liste wird bei einem Datenbankupdate\nneu erstellt, aber es müssen die Sendernamen neu überprüft werden."
		self.session.openWithCallback(self.deleteChannels,  MessageBox, _(mymsg), MessageBox.TYPE_YESNO, timeout=-1, default=False)
	
	def deleteChannels(self,cleanUp=False):
		if cleanUp is not True:
			return
		sql.truncateTableChannel()
		self.session.openWithCallback(self.keyCancel,  MessageBox, "Senderliste gelöscht.", MessageBox.TYPE_INFO, timeout=-1, default=False)
		
	def keyCancel(self,cleanUp=False):
		self.close()

