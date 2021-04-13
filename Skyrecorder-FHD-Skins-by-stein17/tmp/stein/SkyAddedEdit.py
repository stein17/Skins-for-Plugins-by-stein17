#-*- coding: utf-8 -*-
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
from SkyMainFunctions import getPluginPath
from SkySql import *

class SkyAddedEdit(Screen):
	
	def __init__(self, session):
		self.session = session
		
		path = "%s/skins/%s/screen_added_edit.xml" % (getPluginPath(), config.plugins.skyrecorder.anytime_skin.value)
		with open(path, "r") as f:
			self.skin = f.read()
			f.close()
			
		Screen.__init__(self, session)
		
		pluginName = config.plugins.skyrecorder.pluginname.value
		contentSize = config.plugins.skyrecorder.contentsize.value

		self["actions"]  = ActionMap(["OkCancelActions", "ShortcutActions", "EPGSelectActions", "WizardActions", "ColorActions", "NumberActions", "MenuActions", "MoviePlayerActions"], {
			"cancel": self.keyCancel,
			"green": self.keyDel,
			"red": self.askDelAll,
		}, -1)
		
		
		self.addededit_list = []
		self.streamMenuList = MenuList([], enableWrapAround=True, content=eListboxPythonMultiContent)
		self.streamMenuList.l.setFont(0, gFont('Regular', contentSize))
		self.streamMenuList.l.setItemHeight(45)
		self['addededit'] = self.streamMenuList
		
		self.last_index = 0	
	
		self.onLayoutFinish.append(self.readAdded)
	
	
	def skyAddedEditListEntry(self,entry):
		if str(entry[5]) == "Hidden":
			infostr = str(entry[5]) + ": " + str(entry[1]) + " - " + str(entry[2])
		else:
			#infostr = str(entry[5])
			infostr = str(entry[5]) + " - " + str(entry[2])
		return [entry,(eListboxPythonMultiContent.TYPE_TEXT, 0, 0, 1100, 50, 0, RT_HALIGN_LEFT, infostr)]
	
	def readAdded(self):
		try:
			sql.cur.execute('SELECT SQLITE_VERSION()')
		except Exception:
			sys.exc_clear()
			try:
				sql.connect()
			except Exception:
				return
		
		self.addededit_list = []
		# possible fields are:
		# id_added,title,description,id_channel,id_genre,recordedfile,begin,id_eventslist
		rows = sql.readAddedEdit()
		resultCount = len(rows)
		
		for t_row in rows:
			row = list(t_row)
			self.addededit_list.append(row)
		
		#self.addededit_list.sort()
		self.addededit_list = sorted(self.addededit_list, key=lambda x: x[6], reverse=True)
		self.streamMenuList.setList(map(self.skyAddedEditListEntry, self.addededit_list))
		if self.last_index < resultCount:
			self['addededit'].moveToIndex(self.last_index)
	
#	def removeTimer(self):
#		entry_dict = None
#		entry_dict = {}
#		entry_dict['name'] = title
#		entry_dict['description'] = desc
#		entry_dict['timer_starttime'] = timer_starttime
#		entry_dict['channelref'] = channelref
#			
#		retval = SkyTimerRec.removeTimerEntry(entry_dict)
#		if retval:
#			sql.updateEventListStatus(self.id_events,starttime,"False")
#			if config.plugins.skyrecorder.silent_timer_mode.value == False:
#				message = self.session.open(MessageBox, _("Timer gelöscht!"), MessageBox.TYPE_INFO, timeout=3)
#		self.getTimerEventList()
#		return
			
	def keyDel(self):
		exist = self['addededit'].getCurrent()
		if exist == None:
			return
		id_added = self['addededit'].getCurrent()[0][0]
		id_eventslist = self['addededit'].getCurrent()[0][7]
		self.last_index = self['addededit'].getSelectionIndex()
		sql.resetAdded(id_added,id_eventslist)
		print "[skyrecorder] deleted id_added: %s" % id_added
		self.readAdded()

	def askDelAll(self):
		mymsg = "Den kompletten Timerlauf jetzt löschen?"
		self.session.openWithCallback(self.keyDelAll,  MessageBox, _(mymsg), MessageBox.TYPE_YESNO, timeout=-1, default=False)


	def keyDelAll(self,cleanUp=False):
		if cleanUp is not True:
			return
		exist = self['addededit'].getCurrent()
		if exist == None:
			return
		id_added = self['addededit'].getCurrent()[0][0]
		sql.resetAdded()
		print "[skyrecorder] truncated table added"
		self.readAdded()
					
	def keyCancel(self):
		self.close()

