#-*- coding: utf-8 -*-
#from Screens.VirtualKeyBoard import VirtualKeyBoard
from Screens.Screen import Screen
from Tools.Directories import fileExists, resolveFilename, SCOPE_PLUGINS
from enigma import gFont, eListboxPythonMultiContent, RT_HALIGN_LEFT, RT_HALIGN_RIGHT, RT_HALIGN_CENTER, RT_VALIGN_CENTER
from Components.ActionMap import NumberActionMap, ActionMap
from Components.MenuList import MenuList
from Components.ConfigList import ConfigListScreen
from Components.Button import Button
from Components.Label import Label
from Tools.LoadPixmap import LoadPixmap
from Components.config import config, KEY_LEFT, KEY_RIGHT, NoSave, getConfigListEntry, ConfigSelection
import re
import shutil
import os
import sys

# our custom classes
from SkyMainFunctions import getPluginPath
from SkySql import *


class SkyGenreSelect(Screen, ConfigListScreen):
	
	def __init__(self, session):
		self.session = session
				
		path = "%s/skins/%s/screen_genre_select.xml" % (getPluginPath(), config.plugins.skyrecorder.anytime_skin.value)
		with open(path, "r") as f:
			self.skin = f.read()
			f.close()

		Screen.__init__(self, session)
		
		self.configlist = []
		ConfigListScreen.__init__(self, self.configlist, session=self.session)
		
		pluginName = config.plugins.skyrecorder.pluginname.value
		contentSize = config.plugins.skyrecorder.contentsize.value

		self["actions"] = ActionMap(["OkCancelActions", "ShortcutActions", "EPGSelectActions", "WizardActions", "ColorActions", "NumberActions", "MenuActions", "MoviePlayerActions"], {
			"ok": self.keyOK,
			"cancel": self.keyCancel,
			"up": self.keyUp,
			"down": self.keyDown,
			"left": self.keyLeft,
			"right": self.keyRight,
			"prevBouquet": self.keyPageDown,
			"nextBouquet": self.keyPageUp
			#"nextService" : self.keyLeft,
			#"prevService" : self.keyRight
			#"green" : self.keyAdd,
			#"red" : self.keyDel,
		}, -1)


		self.channelliste = []
		self.streamMenuList = MenuList([], enableWrapAround=True, content=eListboxPythonMultiContent)
		self.streamMenuList.l.setFont(0, gFont('Regular', 30))
		self.streamMenuList.l.setItemHeight(75)
		self['channelselect'] = self.streamMenuList
		
		self.onLayoutFinish.append(self.readGenre)


	def skyGenreSelectListEntry(self,entry):
		if entry[1] == "True":
			plus = "/usr/lib/enigma2/python/Plugins/Extensions/skyrecorder/images/plus.png"
			return [entry,
				(eListboxPythonMultiContent.TYPE_PIXMAP_ALPHATEST, 15, 5, 60, 18, LoadPixmap(plus)),
				(eListboxPythonMultiContent.TYPE_TEXT, 50, 0, 1000, 45, 0, RT_HALIGN_LEFT, str(entry[0]))
				]
		else:
			minus = "/usr/lib/enigma2/python/Plugins/Extensions/skyrecorder/images/minus.png"
			return [entry,
				(eListboxPythonMultiContent.TYPE_PIXMAP_ALPHATEST, 15, 5, 60, 18, LoadPixmap(minus)),
				(eListboxPythonMultiContent.TYPE_TEXT, 50, 0, 1000, 45, 0, RT_HALIGN_LEFT, str(entry[0]))
				]
			
	def readGenre(self):

		try:
			sql.cur.execute('SELECT SQLITE_VERSION()')
		except Exception:
			sys.exc_clear()
			try:
				sql.connect()
			except Exception:
				return
		
		self.genreliste = None
		self.genreliste = []
		#self.id_genregroup_list = None
		#self.id_genregroup_list = []
		self.configlist = None
		
		templist = None
		templist = sql.readGenreJoinGenregroup()
		templist = sorted(templist, key=lambda s_field: s_field[0])
		
		self.configlist = None
		self.configlist = []
		
		for (genre,status,id_genregroup, id_genre, id_groups) in templist:
			#self.id_genregroup_list.append(id_genregroup)
			self.configlist.append(getConfigListEntry("",ConfigSelection(default=id_groups, choices=sql.readJoindGroupsShort(id_genregroup))))
			self.genreliste.append((genre,status,id_genregroup, id_genre, id_groups))

		print "[skyrecorder] reload genrelist."
		self["config"].setList(self.configlist)
		self.streamMenuList.setList(map(self.skyGenreSelectListEntry, self.genreliste))

	
	def keyLeft(self):
		self["config"].handleKey(KEY_LEFT)
		id_genregroup = self['channelselect'].getCurrent()[0][2]
		id_groups_selected = (self["config"].getCurrent()[1]).value		
		sql.updateGenregroup(id_genregroup, id_groups_selected, True)
		
	
	def keyRight(self):
		self["config"].handleKey(KEY_RIGHT)
		id_genregroup = self['channelselect'].getCurrent()[0][2]
		id_groups_selected = (self["config"].getCurrent()[1]).value
		sql.updateGenregroup(id_genregroup, id_groups_selected, True)
	
	
	def keyOK(self):
		exist = self['channelselect'].getCurrent()
		if exist == None:
			return		
		genre_auswahl = self['channelselect'].getCurrent()[0][0]
		
		#id_genregroup = self['channelselect'].getCurrent()[0][2]
		#id_groups_selected = (self["config"].getCurrent()[1]).value
		#sql.updateGenregroup(id_genregroup, id_groups_selected)
		print genre_auswahl
		sql.changeGenre(genre_auswahl)
		
		self.readGenre()


	def keyPageDown(self):
		self['channelselect'].pageDown()
		self.last_index = self['channelselect'].getSelectionIndex()
		self['config'].setCurrentIndex(self.last_index)

	def keyPageUp(self):
		self['channelselect'].pageUp()
		self.last_index = self['channelselect'].getSelectionIndex()
		self['config'].setCurrentIndex(self.last_index)
		
	def keyUp(self):
		self['channelselect'].up()
		self.last_index = self['channelselect'].getSelectionIndex()
		self['config'].setCurrentIndex(self.last_index)
		
	def keyDown(self):
		self['channelselect'].down()
		self.last_index = self['channelselect'].getSelectionIndex()
		self['config'].setCurrentIndex(self.last_index)
		
	def keyCancel(self):
		#if not self['config'].getCurrent():
		#	self.close()
		#id_groups_list = []
		#for x in self["config"].list:
		#	id_groups_list.append(x[1].value)
		#
		#n = -1
		#for id_genregroup in self.id_genregroup_list:
		#	n += 1
		#	sql.updateGenregroup(id_genregroup, id_groups_list[n], False) # no commit to speed up things
		#sql.updateGenregroup(id_genregroup, id_groups_list[n], True) # one commit for all changes we made right now
			
		id_groups_list = None
		self.close()

