#-*- coding: utf-8 -*-
from Screens.Screen import Screen
from Screens.VirtualKeyBoard import VirtualKeyBoard
from Screens.MessageBox import MessageBox
from Screens.InfoBar import MoviePlayer
from Components.Label import Label
from Components.ScrollLabel import ScrollLabel
from Components.Sources.StaticText import StaticText
from Components.ActionMap import NumberActionMap, ActionMap
from Components.config import config
from Components.MenuList import MenuList
from Components.Pixmap import Pixmap, MovingPixmap
from Components.AVSwitch import AVSwitch
from enigma import gFont, eTimer, ePicLoad, loadPNG, getDesktop, eListboxPythonMultiContent, RT_HALIGN_LEFT, RT_HALIGN_RIGHT, RT_HALIGN_CENTER, RT_VALIGN_CENTER, eServiceReference
from ServiceReference import ServiceReference
from enigma import eServiceCenter, iServiceInformation
#from Components.Sources.ServiceEvent import ServiceEvent
from Tools.Directories import fileExists, resolveFilename, SCOPE_PLUGINS, SCOPE_HDD, getSize, getRecordingFilename
from Tools.LoadPixmap import LoadPixmap
import time
import sys
import os
import glob
import socket
from urllib2 import Request, urlopen, URLError

# for sorted lists
from operator import itemgetter, attrgetter
from timer import TimerEntry
from RecordTimer import AFTEREVENT
import NavigationInstance

# our custom classes
from SkyMainFunctions import getPluginPath, getTimedeltaFromTimestamp2, getHttpHeader2
from SkySql import *
# Todo
#from SkyFernsehserien_de import SkyFernsehserien_de
from SkyTheTVDB import SkyTheTVDB

# SkyTheMovieDB
from SkyTheMovieDB import SkyTheMovieDB

#MEDIAFILES_MOVIE = ("ts", "avi", "divx", "mpg", "mpeg", "mkv", "mp4", "mov", "iso")
MEDIAFILES_MOVIE = ("ts")


class SkyRecorderArchiv(Screen):

	def __init__(self, session):
		self.session = session
		path = "%s/skins/%s/screen_archiv.xml" % (getPluginPath(), config.plugins.skyrecorder.anytime_skin.value)
		with open(path, "r") as f:
			self.skin = f.read()
			f.close()

		Screen.__init__(self, session)

		pluginName = config.plugins.skyrecorder.pluginname.value
		contentSize = config.plugins.skyrecorder.contentsize.value

		try:
			anytimefolder = config.plugins.skyrecorder.anytimefolder.value
		except Exception:
			sys.exc_clear()
			anytimefolder = resolveFilename(SCOPE_HDD)

		self.headers2 = getHttpHeader2()

		self.anytimefolder = anytimefolder

		self.popUpIsVisible = False

		self.serviceHandler = eServiceCenter.getInstance()
		self.sInfo = SkyTheTVDB(timeout=10)
		self.mInfo = SkyTheMovieDB(timeout=10)

		self["mainscreen_actions"] = ActionMap(["OkCancelActions", "ShortcutActions", "EPGSelectActions", "WizardActions", "ColorActions", "NumberActions", "MenuActions", "MoviePlayerActions"], {
			"ok": self.keyOK,
			"cancel": self.keyCancel,
			"up": self.keyUp,
			"down": self.keyDown,
			"right": self.keyRight,
			"left": self.keyLeft,
			"red": self.keyRed,
			"green": self.keyGreen,
			"yellow": self.selectSearchType,
			"prevBouquet": self.keyPageDown,
			"nextBouquet": self.keyPageUp,
			"nextService": self.keySwitchList,
			"prevService": self.keySwitchList,
			"info": self.selectSearchType
			#"info" : self.showEventInformation
			#"info" : self.searchMovieInfo
		}, -1)

		self["popup_actions_result"] = ActionMap(["OkCancelActions", "ShortcutActions", "EPGSelectActions", "WizardActions", "ColorActions", "NumberActions", "MenuActions", "MoviePlayerActions"], {
			"ok": self.enableRename,
			"cancel": self.keyCancel,
			"up": self.popUpUp,
			"down": self.popUpDown,
			"right": self.popUpRight,
			"left": self.popUpLeft,
			"red": self.keyBackTo,
			"green": self.doRename,
			"yellow": self.editResultList,
			"prevBouquet": self.ignoreKey,
			"nextBouquet": self.ignoreKey,
			"nextService": self.ignoreKey,
			"prevService": self.ignoreKey,
			"info": self.ignoreKey
		}, -1)

		self["popup_actions_search"] = ActionMap(["OkCancelActions", "ShortcutActions", "EPGSelectActions", "WizardActions", "ColorActions", "NumberActions", "MenuActions", "MoviePlayerActions"], {
			"ok": self.gotSerienUrl,
			"cancel": self.keyCancel,
			"up": self.popUpUp,
			"down": self.popUpDown,
			"right": self.popUpRight,
			"left": self.popUpLeft,
			"red": self.keyCancel,
			"green": self.ignoreKey,
			"yellow": self.ignoreKey,
			"prevBouquet": self.ignoreKey,
			"nextBouquet": self.ignoreKey,
			"nextService": self.ignoreKey,
			"prevService": self.ignoreKey,
			"info": self.ignoreKey
		}, -1)

		self["movieinfo_actions"] = ActionMap(["OkCancelActions", "ShortcutActions", "EPGSelectActions", "WizardActions", "ColorActions", "NumberActions", "MenuActions", "MoviePlayerActions"],
		{
			"ok": self.movieinfoOk,
			"cancel": self.movieinfoCancel,
			"up": self.movieinfoUp,
			"down": self.movieinfoDown,
			"right": self.ignoreKey,
			"left": self.ignoreKey,
			"red": self.unmatchMovieInfo,
			"green": self.customSearchMovieInfo,
			"nextBouquet": self.ignoreKey,
			"prevBouquet": self.ignoreKey
		}, -1)

		self["searchtype_actions"] = ActionMap(["OkCancelActions", "ShortcutActions", "EPGSelectActions", "WizardActions", "NumberActions", "MenuActions", "MoviePlayerActions"],
		{
			"ok": self.searchTypeOk,
			"cancel": self.searchTypeCancel,
			"up": self.popUpUp,
			"down": self.popUpDown,
			"right": self.ignoreKey,
			"left": self.ignoreKey
		}, -1)

		self["searchtype_actions"].setEnabled(False)
		self["popup_actions_result"].setEnabled(False)
		self["popup_actions_search"].setEnabled(False)
		self["movieinfo_actions"].setEnabled(False)
		self.searchResultListSerien = None
		self.sTitle = None
		self.need_reload = False
		self.return_state = False

		self['image'] = Pixmap()
		self['image'].hide()

		#self['hd'] = Pixmap()
		#self['hd'].hide()
		#self['169'] = Pixmap()
		#self['169'].hide()
		#self['dolby'] = Pixmap()
		#self['dolby'].hide()
		#self['dualch'] = Pixmap()
		#self['dualch'].hide()
		#self['sub'] = Pixmap()
		#self['sub'].hide()
		for n in range(0, 10):
			star = "star{0}".format(n)
			self[star] = Pixmap()
			self[star].hide()

		self.red = 0xf23d21
		self.green = 0x389416
		self.blue = 0x0064c7
		self.yellow = 0xbab329
		self.white = 0xffffff

		# Genrelist
		self.showGenreList = MenuList([], enableWrapAround=True, content=eListboxPythonMultiContent)
		self.showGenreList.l.setFont(0, gFont('Regular', 30))
		self.showGenreList.l.setItemHeight(40)
		self['genreselect'] = self.showGenreList
		self['genreselect'].setList([])

		#Movielist
		self.showMovieList = MenuList([], enableWrapAround=True, content=eListboxPythonMultiContent)
		self.showMovieList.l.setFont(0, gFont('Regular', 30))
		self.showMovieList.l.setFont(1, gFont('Regular', 27))
		self.showMovieList.l.setItemHeight(75) #25
		self['movieselect'] = self.showMovieList
		self['movieselect'].setList([])

		self.movieinfoSelectList = MenuList([], enableWrapAround=True, content=eListboxPythonMultiContent)
		self.movieinfoSelectList.l.setFont(0, gFont('Regular', 30))
		self.movieinfoSelectList.l.setItemHeight(75)
		self['movieinfo'] = self.movieinfoSelectList
		self['movieinfo'].hide()
		self['movieinfo_bg'] = Pixmap()
		self['movieinfo_bg'].hide()
		self['movieinfo_red'] = Pixmap()
		self['movieinfo_red'].hide()
		self['movieinfo_green'] = Pixmap()
		self['movieinfo_green'].hide()
		self['movieinfo_red_label'] = Label("Unmatch")
		self['movieinfo_red_label'].hide()
		self['movieinfo_green_label'] = Label("Suche")
		self['movieinfo_green_label'].hide()

		# Infoliste/Suchliste
		self.searchList = MenuList([], enableWrapAround=True, content=eListboxPythonMultiContent)
		self.searchList.l.setFont(0, gFont('Regular', 30))
		self.searchList.l.setItemHeight(75)
		self['searchlist'] = self.searchList
		self['searchlist'].setList([])
		self['searchlist'].hide()
		self['searchlist_red'] = Pixmap()
		self['searchlist_red'].hide()
		self['searchlist_green'] = Pixmap()
		self['searchlist_green'].hide()
		self['searchlist_yellow'] = Pixmap()
		self['searchlist_yellow'].hide()
		self['searchlist_bg'] = Pixmap()
		self['searchlist_bg'].hide()

		self['searchlist_red_label'] = Label("Exit")
		self['searchlist_red_label'].hide()
		self['searchlist_green_label'] = Label("Ok")
		self['searchlist_green_label'].hide()
		self['searchlist_yellow_label'] = Label("Edit")
		self['searchlist_yellow_label'].hide()

		self.tempTimer = eTimer()
		self.tempTimer.callback.append(self.gotSearchTypeOk)

		# Auswahl der liste welche als erstes angezeigt werden soll
		self.currentList = "movieselect"
		self["genreselect"].selectionEnabled(0)
		self["movieselect"].selectionEnabled(1)
		self["searchlist"].selectionEnabled(0)

		self['title'] = Label("SkyRecorder Archiv")
		self['name'] = Label("")
		self['handlung'] = ScrollLabel("")

		self.onLayoutFinish.append(self.getGenreList)
		self['movieselect'].onSelectionChanged.append(self.showDetails)

	def ignoreKey(self):
		return

	def selectSearchType(self):
		self['searchlist_bg'].show()
		self['searchlist'].show()
		self["searchtype_actions"].setEnabled(True)
		self["mainscreen_actions"].setEnabled(False)
		self.searchList.setList(map(self.infoSelectSearchType, ['Filmsuche', 'Seriensuche']))

	def searchTypeOk(self):
		self['searchlist_bg'].hide()
		self['searchlist'].hide()
		self["searchtype_actions"].setEnabled(False)
		self["mainscreen_actions"].setEnabled(True)
		self.tempTimer.start(100, True)

	def gotSearchTypeOk(self):
		exist = self['searchlist'].getCurrent()
		if exist == None:
			return
		searchType = self['searchlist'].getCurrent()[0]
		self.searchList.setList([])
		if searchType == "Filmsuche":
			self.searchMovieInfo()
		elif searchType == "Seriensuche":
			self.searchSerienInfo()
		else:
			return

	def searchTypeCancel(self):
		self['searchlist_bg'].hide()
		self['searchlist'].hide()
		self["searchtype_actions"].setEnabled(False)
		self["mainscreen_actions"].setEnabled(True)

	def toggleSearchList(self, show=False, listType="result"):
		if show:
			self['searchlist_bg'].show()
			self['searchlist'].show()
			self['searchlist_red'].show()
			if listType == "result":
				self['searchlist_green'].show()
				self['searchlist_yellow'].show()
				self['searchlist_red_label'].show()
				self['searchlist_green_label'].show()
				self['searchlist_yellow_label'].show()
				self["popup_actions_search"].setEnabled(False)
				self["popup_actions_result"].setEnabled(True)
			else:
				self["popup_actions_result"].setEnabled(False)
				self["popup_actions_search"].setEnabled(True)

			self["mainscreen_actions"].setEnabled(False)
			self.popUpIsVisible = True
		else:
			self['searchlist_bg'].hide()
			self['searchlist'].hide()
			self['searchlist_red'].hide()
			self['searchlist_green'].hide()
			self['searchlist_yellow'].hide()
			self['searchlist_red_label'].hide()
			self['searchlist_green_label'].hide()
			self['searchlist_yellow_label'].hide()
			self["popup_actions_result"].setEnabled(False)
			self["popup_actions_search"].setEnabled(False)
			self["mainscreen_actions"].setEnabled(True)
			self.popUpIsVisible = False

	def skyAnytimeGenreListEntry(self, entry):
		return [entry,
			(eListboxPythonMultiContent.TYPE_TEXT, 5, 0, 210, 40, 0, RT_HALIGN_CENTER, str(entry))
			]

	def skyAnytimeMovieListEntry(self, entry):
		icon = None
		new = None
		if entry[5] == 'Timer':
			icon = "/usr/lib/enigma2/python/Plugins/Extensions/skyrecorder/images/neu_timer.png"
		elif entry[5] == 'Done':
			icon = "/usr/lib/enigma2/python/Plugins/Extensions/skyrecorder/images/neu_done.png"
		else:
			icon = "/usr/lib/enigma2/python/Plugins/Extensions/skyrecorder/images/neu_done_2.png"
		if icon:
			new = LoadPixmap(icon)

		begin_date = time.strftime("%d.%m.%Y %H:%M", time.localtime(float(entry[2])))

		return [entry,
			(eListboxPythonMultiContent.TYPE_PIXMAP_ALPHATEST, 0, 5, 28, 17, new),
			(eListboxPythonMultiContent.TYPE_TEXT, 25, 0, 270, 35, 0, RT_HALIGN_LEFT, str(begin_date)),
			(eListboxPythonMultiContent.TYPE_TEXT, 25, 40, 260, 30, 1, RT_HALIGN_LEFT, str(entry[6]), self.green),
			(eListboxPythonMultiContent.TYPE_TEXT, 330, 0, 860, 35, 0, RT_HALIGN_LEFT, str(entry[0])),
			(eListboxPythonMultiContent.TYPE_TEXT, 330, 40, 520, 30, 1, RT_HALIGN_LEFT, str(entry[1]), self.red),
			(eListboxPythonMultiContent.TYPE_TEXT, 1220, 0, 815, 35, 0, RT_HALIGN_LEFT, str(entry[1])),
			(eListboxPythonMultiContent.TYPE_TEXT, 875, 40, 210, 30, 1, RT_HALIGN_LEFT, entry[8], self.blue),
			(eListboxPythonMultiContent.TYPE_TEXT, 1035, 40, 205, 30, 1, RT_HALIGN_LEFT, entry[7], self.yellow)
			]

	def infoResultListEntry(self, entry):
		icon = None
		new = None
		status = None
		if entry[9] == 'none':
			icon = "/usr/lib/enigma2/python/Plugins/Extensions/skyrecorder/images/not_done_8bit.png"
		elif entry[9] == 'todo':
			icon = "/usr/lib/enigma2/python/Plugins/Extensions/skyrecorder/images/neu_new_2.png"
		else:
			icon = "/usr/lib/enigma2/python/Plugins/Extensions/skyrecorder/images/done_8bit.png"
		if icon:
			new = LoadPixmap(icon)

		if entry[10] == True:
			status = LoadPixmap("/usr/lib/enigma2/python/Plugins/Extensions/skyrecorder/images/selected.png")
		else:
			status = LoadPixmap("/usr/lib/enigma2/python/Plugins/Extensions/skyrecorder/images/minus.png")
		#if entry[10] == True:
		#	status = LoadPixmap("/usr/lib/enigma2/python/Plugins/Extensions/skyrecorder/images/selected.png")
		#elif entry[10] == False and entry[9] == 'none':
		#	status = LoadPixmap("/usr/lib/enigma2/python/Plugins/Extensions/skyrecorder/images/minus.png")
		#else:
		#	status = LoadPixmap("/usr/lib/enigma2/python/Plugins/Extensions/skyrecorder/images/done_3_8bit.png")
		old_name = "{0} - {1}".format(entry[2], entry[3])
		episode_idx = "{0}{1}".format(entry[4], entry[5])
		return [entry,
			(eListboxPythonMultiContent.TYPE_PIXMAP_ALPHATEST, 5, 1, 35, 25, status),
			(eListboxPythonMultiContent.TYPE_PIXMAP_ALPHATEST, 55, 1, 35, 25, new),
			(eListboxPythonMultiContent.TYPE_TEXT, 190, 0, 865, 40, 0, RT_HALIGN_LEFT, old_name),
			(eListboxPythonMultiContent.TYPE_TEXT, 870, 0, 190, 40, 0, RT_HALIGN_LEFT, episode_idx)
			]

	def infoSearchListEntry(self, entry):
		return [entry,
			(eListboxPythonMultiContent.TYPE_TEXT, 5, 0, 400, 40, 0, RT_HALIGN_LEFT, entry[2]),
			(eListboxPythonMultiContent.TYPE_TEXT, 430, 0, 400, 40, 0, RT_HALIGN_LEFT, entry[3]),
			(eListboxPythonMultiContent.TYPE_TEXT, 840, 0, 220, 40, 0, RT_HALIGN_LEFT, entry[4])
			]

	def infoSelectSearchType(self, entry):
		return [entry,
			(eListboxPythonMultiContent.TYPE_TEXT, 5, 0, 1060, 40, 0, RT_HALIGN_CENTER, str(entry))
			]

	def showDetails(self):
		self['handlung'].setText(" ")
		if len(self.movielist) < 1:
			return
		try:
			serviceref = self['movieselect'].getCurrent()[0][4]
		except Exception:
			return
		if not serviceref:
			return

		filminfo = "Keine infos gefunden."
		try:
			info = self.serviceHandler.info(serviceref)
			title = info.getName(serviceref)
			filminfo = info.getEvent(serviceref).getExtendedDescription()
		except Exception:
			return

		self['name'].setText(" ")
		self['image'].hide()
		for n in range(0, 10):
			star = "star{0}".format(n)
			self[star].hide()

		# maybe we have some info in our themoviedb-table
		#[id_themoviedb], [id_events], [m_id_movie], [m_name], [m_year], [m_title_org],[m_rating],[m_description], [m_genre], [sky_title]
		got_movieinfo = False
		# maybe we have and id_key?
		sky_title = title
		self.current_m_id_movie = None
		tags = self['movieselect'].getCurrent()[0][9]
		if tags.has_key("tmdb_id"):
			self.current_m_id_movie = tags["tmdb_id"]
			sky_title = None
		rows = sql.getMovieInfo(id_events=None, m_id_movie=self.current_m_id_movie, m_name=None, sky_title=sky_title)
		for t_row in rows:
			got_movieinfo = True
			if float(t_row[6]) > 0:
				max_star = float(t_row[6])
				max_star = int(round(max_star, 0))
				for n in range(0, max_star):
					star = "star{0}".format(n)
					self[star].show()

			m_name = str(t_row[3]) + " (" + str(t_row[4]) + ")"
			self['name'].setText(m_name)

			m_description = str(t_row[7])
			if m_description and m_description != "N/A" and len(m_description) >= 20:
				self['handlung'].setText(m_description)
			else:
				self['handlung'].setText(filminfo)
			# get poster
			self.current_m_id_movie = int(t_row[2])
			poster = None
			if self.current_m_id_movie and self.current_m_id_movie > 0:
				poster = sql.getMovieInfoPoster(None, self.current_m_id_movie, pos=0)
			else:
				poster = sql.getMovieInfoPoster(id_events, None, pos=0)
			if poster:
				cover_file = "/tmp/skyrecorder_tempcover.png"
				with open(cover_file, "wb") as f:
					f.write(poster)
				try:
					self.ShowCover(cover_file)
				except Exception:
					return

		if not got_movieinfo:
			self['handlung'].setText(filminfo)
			self['name'].setText(title)

	def ShowCover(self, image_path):
		if fileExists(image_path):
			#self.session.open(MessageBox, "show_cover", MessageBox.TYPE_INFO, timeout=3)
			self['image'].instance.setPixmap(None)
			self.scale = AVSwitch().getFramebufferScale()
			self.picload = ePicLoad()
			size = self['image'].instance.size()
			self.picload.setPara((size.width(), size.height(), self.scale[0], self.scale[1], False, 1, "#FF000000"))
			if self.picload.startDecode(image_path, 0, 0, False) == 0:
				ptr = self.picload.getData()
				if ptr != None:
					self['image'].instance.setPixmap(ptr.__deref__())
					self['image'].show()
					del self.picload

	def getMyDirs(self, my_folder=None, max_depth=3, my_group="A-Z"):
		self.need_reload = False
		self.movielist = []

		if not my_folder or not os.path.isdir(my_folder):
			my_folder = self.anytimefolder

		my_dirs = []
		my_dirs.append(my_folder) # append base folder
		n = 0
		for root, dirs, files in os.walk(my_folder):
			if len(dirs) != 0:
				n += 1
				for a_dir in dirs:
					if a_dir[-1:] != "/":
						a_dir += "/"
					my_dirs.append(os.path.join(root, a_dir))
			if n == max_depth:
				break

		self.loadFiles(my_dirs, my_group)

	def loadFiles(self, my_dirs=None, my_group="A-Z"):

		self['handlung'].setText(" ")
		self.movielist = []
		if not my_dirs:
			return
		my_list = None
		tags = set()

		for a_dir in my_dirs:
			if not os.path.isdir(a_dir):
				continue
			root = eServiceReference("2:0:1:0:0:0:0:0:0:0:" + a_dir)
			my_list = self.serviceHandler.list(root)
			if my_list is None:
				#print "listing of movies failed"
				continue
			# get current folder name for group mapping
			if a_dir[-1:] != "/":
				basedir_name = a_dir.split('/')[-1:][0]
			else:
				basedir_name = a_dir.split('/')[-2:-1][0] # -2 is true, because we have a leading slash in a_dir string

			while 1:
				serviceref = my_list.getNext()
				if not serviceref.valid():
					break

				filetype = serviceref.toString().split('.')
				filetype = filetype[-1].lower()
				if not filetype in MEDIAFILES_MOVIE:
					continue

				moviefile = os.path.realpath(serviceref.getPath())
				#sref_moviefile = eServiceReference(1, 0, moviefile)
				sref_moviefile = serviceref

				info = self.serviceHandler.info(sref_moviefile)
				if info is None:
					continue
				#event = info.getEvent(serviceref)

				# check for recording state
				is_recording = "False"
				timer = self.checkTimerState(sref_moviefile)
				if timer:
					is_recording = "Timer"
				#begin = info.getInfo(serviceref, iServiceInformation.sTimeCreate)
				description = info.getInfoString(sref_moviefile, iServiceInformation.sDescription)
				title = info.getName(sref_moviefile)
				channel = ServiceReference(info.getInfoString(serviceref, iServiceInformation.sServiceref)).getServiceName()	# Sender
				try:
					event = info.getEvent(sref_moviefile)
					begin = event.getBeginTime()
					#begin = event.getBeginTimeString()
					d_m, d_s = divmod(event.getDuration(), 60)
					duration = "{0:d}:{1:02d} min".format(d_m, d_s)
				except Exception:
					sys.exc_clear()
					begin = info.getInfo(serviceref, iServiceInformation.sTimeCreate)
					duration = ""
				try:
					#moviesize = os.path.getsize(moviefile)
					moviesize = info.getInfoObject(sref_moviefile, iServiceInformation.sFileSize)
					moviesize = "{0:.0f} MB".format(moviesize / (1024 * 1024))
				except Exception:
					sys.exc_clear()
					moviesize = ""
				if my_group != "A-Z":
					if not basedir_name == my_group: # skip this folder, if the name does not match our group and we are not in A-Z
						group_check = None
						group_check = sql.getGenregroupByGenre(description)
						if not group_check or my_group != group_check:
							continue

				# convert space-seperated list of tags into a set
				# Fixme
				this_tags = info.getInfoString(sref_moviefile, iServiceInformation.sTags).split(' ')
				if this_tags == ['']:
					this_tags = []
				#this_tags = set(this_tags)
				#tags |= this_tags

				tags = {}
				for i in range(0, len(this_tags)):
					l_tag = this_tags[i].split(":")
					if l_tag and len(l_tag) == 2:
						tags[l_tag[0]] = l_tag[1]
					else:
						continue

				self.movielist.append((title, description, begin, moviefile, sref_moviefile, is_recording, channel, moviesize, duration, tags))

		if len(self.movielist) < 1:
			self.keySwitchList(set_list="genreselect")
			self.showMovieList.setList([])
		else:
			if my_group != "A-Z":
				if my_group.lower() == "serie":
					#self.movielist.sort(key=lambda x: -x[2]) # sort by date and time, if we are not in A-Z
					self.movielist = sorted(self.movielist, key=itemgetter(0, 2))
				else:
					self.movielist.sort(key=lambda x: -x[2]) # sort by date and time, if we are not in A-Z
			else:
				self.movielist = sorted(self.movielist, key=lambda x: x[0], reverse=False)
			self.showMovieList.setList(map(self.skyAnytimeMovieListEntry, self.movielist))
			self.keySwitchList(set_list="movieselect")

	def getGenreList(self):
		# get groupnames
		self.groupnames = []
		self.groupnames.append(("A-Z"))
		rows = sql.readGroupsShort()
		for t_row in rows:
			row = list(t_row)
			self.groupnames.append(row[1])
		self.showGenreList.setList(map(self.skyAnytimeGenreListEntry, self.groupnames))

		#self.loadFiles("A-Z")
		# default genre selected
		self.genre_auswahl = "A-Z"
		self.getMyDirs(self.anytimefolder, 3, self.genre_auswahl)

	def keySwitchList(self, set_list=None):
		if set_list:
			if set_list == "movieselect":
				if len(self.movielist) < 1:
					return
				self["genreselect"].selectionEnabled(0)
				self["movieselect"].selectionEnabled(1)
				self.currentList = set_list
			else:
				self["movieselect"].selectionEnabled(0)
				self["genreselect"].selectionEnabled(1)
				self.currentList = set_list
		else:
			if self.currentList == "genreselect":
				self["genreselect"].selectionEnabled(0)
				self["movieselect"].selectionEnabled(1)
				self.currentList = "movieselect"
			else:
				self["movieselect"].selectionEnabled(0)
				self["genreselect"].selectionEnabled(1)
				self.currentList = "genreselect"

	def keyPageDown(self):
		if len(self.movielist) < 1:
			return
		self['handlung'].pageDown()

	def keyPageUp(self):
		if len(self.movielist) < 1:
			return
		self['handlung'].pageUp()

	def skysettings(self):
		pass

	def keyLeft(self):
		exist = self[self.currentList].getCurrent()
		if exist == None:
			return
		self[self.currentList].pageUp()

	def keyRight(self):
		exist = self[self.currentList].getCurrent()
		if exist == None:
			return
		self[self.currentList].pageDown()

	def keyUp(self):
		exist = self[self.currentList].getCurrent()
		if exist == None:
			return
		self[self.currentList].up()

	def keyDown(self):
		exist = self[self.currentList].getCurrent()
		if exist == None:
			return
		self[self.currentList].down()

	def popUpLeft(self):
		exist = self["searchlist"].getCurrent()
		if exist == None:
			return
		self["searchlist"].pageUp()

	def popUpRight(self):
		exist = self["searchlist"].getCurrent()
		if exist == None:
			return
		self["searchlist"].pageDown()

	def popUpUp(self):
		exist = self["searchlist"].getCurrent()
		if exist == None:
			return
		self["searchlist"].up()

	def popUpDown(self):
		exist = self["searchlist"].getCurrent()
		if exist == None:
			return
		self["searchlist"].down()

	def movieinfoDown(self):
		self['movieinfo'].down()

	def movieinfoUp(self):
		self['movieinfo'].up()

	def keyBackTo(self):
		if not self.searchResultListSerien or not self.sTitle:
			return
		self.getSearchResultListSerien(self.sTitle, self.searchResultListSerien)

	def keyRed(self):
		self.deleteFile()

	def keyGreen(self):
		self.keyOK()

	def movieinfoOk(self):
		exist = self['movieselect'].getCurrent()
		if exist == None:
			return
		exist = self['movieinfo'].getCurrent()
		if exist == None:
			return
		moviefile = self['movieselect'].getCurrent()[0][3]

		movieURL = self['movieinfo'].getCurrent()[0][0]
		title = self['movieinfo'].getCurrent()[0][2]
		year = self['movieinfo'].getCurrent()[0][3]
		m_id_movie = self['movieinfo'].getCurrent()[0][4]
		if m_id_movie:
			tmdb_id = "tmdb_id:{0}".format(m_id_movie)
		posterUrl = None
		#posterUrl = self['movieinfo'].getCurrent()[0][5]
		#id_events = self['movieinfo'].getCurrent()[0][6]
		id_events = None
		sky_title = self['movieinfo'].getCurrent()[0][7]

		res = self.getMovieInfo(movieURL=movieURL, movieTitle=title, posterUrl=posterUrl, id_events=id_events, sky_title=sky_title)
		if res:
			# TODO: ask user before renamning moviefile-name in metadata
			self.updateMetadata(datatext=title, datafield=1, moviefile=moviefile)
			self.updateMetadata(datatext=tmdb_id, datafield=4, moviefile=moviefile)

			# finally rename moviefile
			if config.plugins.skyrecorder.rename_matched_movies and config.plugins.skyrecorder.rename_matched_movies.value:
				serviceref = self['movieselect'].getCurrent()[0][4]
				filepath = self['movieselect'].getCurrent()[0][3]
				info = self.serviceHandler.info(serviceref)
				if info is None:
					return
				title = info.getName(serviceref)
				if year and len(year) > 3:
					self.renameFile(filepath=filepath, serviceref=serviceref, title=title, year=year)
				else:
					self.renameFile(filepath=filepath, serviceref=serviceref, title=title, year=None)

		self['movieinfo_bg'].hide()
		self['movieinfo'].hide()
		self['movieinfo_red_label'].hide()
		self['movieinfo_green_label'].hide()
		self['movieinfo_red'].hide()
		self['movieinfo_green'].hide()
		self.movieinfoVisible = False
		self["movieinfo_actions"].setEnabled(False)
		self["mainscreen_actions"].setEnabled(True)
		self.getMyDirs(self.anytimefolder, 3, self.genre_auswahl)

	def gotSerienUrl(self):
		exist = self['searchlist'].getCurrent()
		if exist == None:
			return
		url = self['searchlist'].getCurrent()[0][0]
		title = self['searchlist'].getCurrent()[0][2]
		self.toggleSearchList(True, "result")
		self.getEpisodenListeSerien(sUrl=url, sTitle=title)

	def getSearchResultListSerien(self, title=None, searchResultListSerien=None):
		if not title:
			return
		self.searchResultListSerien = None
		self.searchResultListSerien = []

		if searchResultListSerien:
			self.searchResultListSerien = searchResultListSerien
			sRes = []
		else:
			sRes = self.sInfo.getListFor(title)
			if not sRes or len(sRes) < 1:
				self.session.open(MessageBox, "Timeout, oder keine Info gefunden für:\n{0}".format(title), MessageBox.TYPE_INFO)
				return

		for res in sRes:
			self.searchResultListSerien.append([res["s_url"], res["s_url_name"], res["s_title"], res["s_subtitle"], res["s_date"], res["s_org"]])

		if self.searchResultListSerien and len(self.searchResultListSerien) > 0:
			if len(self.searchResultListSerien) > 1:
				self.searchList.setList(map(self.infoSearchListEntry, self.searchResultListSerien))
				self.toggleSearchList(True, "search")
			else:
				url = self.searchResultListSerien[0][0]
				title = self.searchResultListSerien[0][2]
				self.toggleSearchList(True, "result")
				self.getEpisodenListeSerien(sUrl=url, sTitle=title)
		return

	def getEpisodenListeSerien(self, sUrl=None, sTitle=None, episodenListeSerien=None):
		if sTitle:
			self.sTitle = sTitle
		else:
			if len(self.local_glob_list) > 0:
				self.sTitle = self.local_glob_list[0][2]
			else:
				return

		if episodenListeSerien:
			self.episodenListeSerien = episodenListeSerien
		else:
			self.episodenListeSerien = self.sInfo.getInfoFor(sUrl, self.sTitle) # for tvdb we need the title as well

		if self.episodenListeSerien and len(self.episodenListeSerien) > 0:
			self.resultlist = None
			self.resultlist = []
			for al in self.local_glob_list:
				#file_dir = os.path.dirname(al[1]) + "/"
				old_basename = os.path.splitext(os.path.basename(al[1]))[0]
				matched = False
				for res in self.episodenListeSerien:
					#if res["s_title"].lower() == self.sTitle.lower() and res["e_name"].lower() == al[3].lower():
					if res["e_name"].lower() == al[3].lower():
						new_basename = "{0} {1}{2}".format(res["s_title"], res["e_s_number"], res["e_e_number"])
						#new_basename = getRecordingFilename(new_basename,file_dir)
						#dst_file = os.path.splitext(new_basename.replace(file_dir,""))[0] # remove the suffix
						if old_basename.lower() == new_basename.lower():
							self.resultlist.append([al[0], al[1], al[2], al[3],
							res["e_s_number"], res["e_e_number"], res["s_title"], res["e_name"], res["s_cover"], 'done', False])
						else:
							self.resultlist.append([al[0], al[1], al[2], al[3],
							res["e_s_number"], res["e_e_number"], res["s_title"], res["e_name"], res["s_cover"], 'todo', True])
						matched = True
						break
				if not matched:
					self.resultlist.append([al[0], al[1], al[2], al[3], "", "", "", "", "", 'none', False])

			self.searchList.setList(map(self.infoResultListEntry, self.resultlist))
			self.toggleSearchList(True)
		else:
			self.session.open(MessageBox, "Timeout, oder keine Info gefunden für:\n{0}".format(self.sTitle), MessageBox.TYPE_INFO)
			self.toggleSearchList(False)
		return

	def searchSerienInfo(self):
		exist = self['movieselect'].getCurrent()
		if exist == None:
			return
		if self.currentList == "movieselect":
			serviceref = self['movieselect'].getCurrent()[0][4]
		else:
			return
		if not serviceref:
			return
		try:
			serviceHandler = self.serviceHandler
			offline = serviceHandler.offlineOperations(serviceref)
			info = serviceHandler.info(serviceref)
			name_info = info and info.getName(serviceref)

			description = info and info.getInfoString(serviceref, iServiceInformation.sDescription)
			full_path = os.path.realpath(serviceref.getPath())
			file_dir = os.path.dirname(full_path) + "/"
			# fix recalculated clean name
			name = getRecordingFilename(name_info, file_dir).replace(file_dir, "")
		except Exception, e:
			sys.exc_clear()
			self.session.open(MessageBox, "Fehler:\n{0}".format(e), MessageBox.TYPE_ERROR)
			return

		# build list with all matching titles of a given event.
		# maybe we are dealing with a single episode and need to fetch the entire season infos
		self.local_glob_list = None
		self.local_glob_list = []

		glob_root = eServiceReference("2:0:1:0:0:0:0:0:0:0:" + file_dir)
		globed = serviceHandler.list(glob_root)
		while 1:
			f_service = globed.getNext()
			if not f_service.valid():
				break
			filetype = serviceref.toString().split('.')
			filetype = filetype[-1].lower()
			if not filetype in MEDIAFILES_MOVIE:
				continue

			f_full_path = f_service.getPath()
			f_info = serviceHandler.info(f_service)
			f_name = f_info.getName(f_service)
			if f_name != name_info:
				continue
			f_desc = f_info.getInfoString(f_service, iServiceInformation.sDescription)
			self.local_glob_list.append([f_service, f_full_path, f_name, f_desc])

		#globed = glob.glob(file_dir + "*" + name_info + "*.ts")
		#for f in sorted(globed):
		#	f_service = eServiceReference(1, 0, f)
		#	f_full_path = f_service.getPath()
		#	f_info = serviceHandler.info(f_service)
		#	f_name = f_info.getName(f_service)
		#	f_desc = f_info.getInfoString(f_service, iServiceInformation.sDescription)
		#	self.local_glob_list.append([f_service,f_full_path,f_name,f_desc])

		if len(self.local_glob_list) > 0:
			self.local_glob_list = sorted(self.local_glob_list)
			self.getSearchResultListSerien(title=name_info, searchResultListSerien=None)
		else:
			self.session.open(MessageBox, "Konnte keine Dateien finden, mit dem Namen:\n{0}".format(name_info), MessageBox.TYPE_INFO, timeout=-1)
		return

	def editResultList(self, newdesc=None):
		exist = self['searchlist'].getCurrent()
		if exist == None:
			return
		self.searchlist_idx = self['searchlist'].getSelectionIndex()
		title = self['searchlist'].getCurrent()[0][2]
		desc = self['searchlist'].getCurrent()[0][3]
		info_title = "Episodenname anpassen für:\n{0}".format(title)
		self.session.openWithCallback(self.doEditResultList, VirtualKeyBoard, title=info_title, text=desc)

	def doEditResultList(self, newdesc=None):
		if not newdesc or len(newdesc) < 1:
			return
		else:
			#serviceHandler = self.serviceHandler
			#f_service = self.local_glob_list[self.searchlist_idx][0]
			#f_info = serviceHandler.info(f_service)
			#check = f_info.setInfoString(f_service, iServiceInformation.sDescription, newdesc)

			# TODO: is there any other way to do this? Why does setInfoString does not work?
			desc = self['searchlist'].getCurrent()[0][3]
			metafile = self.local_glob_list[self.searchlist_idx][1] + ".meta"
			if metafile and os.path.exists(metafile):
				#with open(metafile, "r") as meta:
				#	text=meta.read()
				#	meta.close()
				#with open(metafile, "w") as meta:
				#	meta.write(text.replace(desc,newdesc))
				#	meta.close()

				metalist = []
				with open(metafile, "r") as meta:
					metalist = [line.rstrip() for line in meta]
					meta.close()
				# replace description field with new value
				if len(metalist) > 2:
					metalist[2] = newdesc
					with open(metafile, "w") as meta:
						meta.write('\n'.join(listitem for listitem in metalist))
						meta.write('\n')
						meta.close()
			self.need_reload = True
			self.local_glob_list[self.searchlist_idx][3] = newdesc
			self.getEpisodenListeSerien(episodenListeSerien=self.episodenListeSerien)
			self['searchlist'].moveToIndex(self.searchlist_idx)

	def updateMetadata(self, datatext=None, datafield=None, moviefile=None):
		if not datatext or len(datatext) < 1:
			return
		elif not datafield or int(datafield) < 0:
			return
		elif not moviefile or len(moviefile) < 1:
			return
		else:
			datafield = int(datafield)
			metafile = moviefile + ".meta"
			if metafile and os.path.exists(metafile):
				metalist = []
				with open(metafile, "r") as meta:
					metalist = [line.rstrip() for line in meta]
					meta.close()
				if len(metalist) > 2:
					# TODO: do not delete exsiting Tags
					if datafield == 4:
						if len(metalist[datafield]) < 1:
							metalist[datafield] = datatext
						else:
							tags = metalist[datafield].split(" ")
							newtags = []
							for a in tags:
								if a.split(":")[0] == datatext.split(":")[0]:
									newtags.append(datatext)
								else:
									newtags.append(a)
							datatext = ' '.join(str(x) for x in newtags if x)
							metalist[datafield] = datatext
					else:
						metalist[datafield] = datatext
					with open(metafile, "w") as meta:
						meta.write('\n'.join(listitem for listitem in metalist))
						meta.write('\n')
						meta.close()

	def enableRename(self):
		exist = self['searchlist'].getCurrent()
		if exist == None:
			return
		idx = self['searchlist'].getSelectionIndex()
		valid = self['searchlist'].getCurrent()[0][9]
		if valid == "none":
			return
		status = self['searchlist'].getCurrent()[0][10]
		if status:
			self.resultlist[idx][10] = False
		else:
			self.resultlist[idx][10] = True
		self.searchList.setList(map(self.infoResultListEntry, self.resultlist))
		self['searchlist'].moveToIndex(idx)

	def doRename(self):
		self.session.openWithCallback(self.gotDestination, MessageBox, "Sollen die ausgewählten Dateien jetzt umbenannt werden?", default=True)

	def gotDestination(self, res):
		if res:
			for entry in self.resultlist:
				if entry[9] == 'none':
					continue
				if entry[10] == False:
					continue
				is_timer = self.checkTimerState(entry[0])
				if is_timer is not None:
					continue
				src_file = entry[1]
				src_dir = os.path.dirname(src_file) + "/"
				new_name = "{0} {1}{2}".format(entry[6], entry[4], entry[5])
				if len(new_name) > 0:
					#dst_file = getRecordingFilename(new_name, src_dir)
					#dst_file = os.path.splitext(dst_file)[0] # remove the suffix
					dst_file = src_dir + new_name
					# build list of files
					src_file_list = glob.glob(os.path.splitext(src_file)[0] + ".*?")
					for old_file in src_file_list:
						parts = os.path.splitext(old_file)
						if len(parts) > 1:
							new_file = dst_file + os.path.splitext(parts[0])[1] + parts[1]
						else:
							new_file = dst_file + parts[1]
						if fileExists(old_file) and not fileExists(new_file):
							if old_file != new_file: # little bit paranoid, but just to be sure
								os.rename(old_file, new_file)
			idx = self['movieselect'].getSelectionIndex()
			self.need_reload = True
			self.getMyDirs(self.anytimefolder, 3, self.genre_auswahl)
			self['movieselect'].moveToIndex(idx)
			self.toggleSearchList(False)

	def keyBlue(self):
		self.close(self.return_state)

	def keyOK(self):
		if self.currentList == "genreselect":
			exist = self['genreselect'].getCurrent()
			if exist == None:
				return
			self.genre_auswahl = self['genreselect'].getCurrent()[0]
			#self.loadFiles(genre_auswahl)
			self.getMyDirs(self.anytimefolder, 3, self.genre_auswahl)

		elif self.currentList == "movieselect":
			exist = self['movieselect'].getCurrent()
			if exist == None:
				return
			title = self['movieselect'].getCurrent()[0][0]
			file = self['movieselect'].getCurrent()[0][3]
			if fileExists(file):
				self.play(title, file)
			else:
				print "Aufnahme nicht vorhanden."
				message = self.session.open(MessageBox, _("Die Aufnahme ist noch nicht vorhanden.\n'{0}'".format(file)), MessageBox.TYPE_INFO, timeout=-1)

	def play(self, title, file):
		sref = eServiceReference(1, 0, file)
		sref.setName(title)
		self.mp = self.session.open(MoviePlayer, sref)
		self.mp.leavePlayer = self.leavePlayerForced # overwrite MoviePlayer leave function

	def leavePlayerForced(self):
		self.mp.leavePlayerConfirmed([True, "quit"])

	def movieinfoCancel(self):
		self['movieinfo_bg'].hide()
		self['movieinfo'].hide()
		self['movieinfo_red_label'].hide()
		self['movieinfo_green_label'].hide()
		self['movieinfo_red'].hide()
		self['movieinfo_green'].hide()
		self["movieinfo_actions"].setEnabled(False)
		self["mainscreen_actions"].setEnabled(True)

	def keyCancel(self):
		if self.popUpIsVisible:
			self.toggleSearchList(False)
			if self.need_reload:
				self.getMyDirs(self.anytimefolder, 3, self.genre_auswahl)
		else:
			self.close(self.return_state)

	def deleteFile(self):
		if self.currentList == "movieselect":
			self.service = self['movieselect'].getCurrent()[0][4]
		else:
			return
		if self.service is None:
			return
		try:
			if self.service.type != 4098 and self.session.nav.getCurrentlyPlayingServiceReference() is not None:
				if self.service == self.session.nav.getCurrentlyPlayingServiceReference():
					self.stopEntry()
		except Exception, e:
			sys.exc_clear()
			return
		#serviceHandler = eServiceCenter.getInstance()
		serviceHandler = self.serviceHandler
		offline = serviceHandler.offlineOperations(self.service)
		info = serviceHandler.info(self.service)
		name = info and info.getName(self.service)
		result = False
		if offline is not None:
			# simulate first
			if not offline.deleteFromDisk(1):
				result = True

		self.timer = self.checkTimerState(self.service)

		if result == True and not self.timer:
			self.session.openWithCallback(self.deleteConfirmed_offline, MessageBox, _("Do you really want to delete %s?") % (name), default=False)
		elif result == True and self.timer:
			self.session.openWithCallback(self.confirmRemoveTimer, MessageBox, _("Achtung, laufende Aufnahme!\n%s wirklich löschen?") % (name), default=False)
		else:
			self.session.openWithCallback(self.close, MessageBox, _("You cannot delete this!"), MessageBox.TYPE_ERROR)

	def confirmRemoveTimer(self, confirmed):
		if not confirmed:
			return
		self.timer.afterEvent = AFTEREVENT.NONE
		NavigationInstance.instance.RecordTimer.removeEntry(self.timer)
		self.deleteConfirmed_offline(confirmed)

	def deleteConfirmed_offline(self, confirmed):
		if not confirmed:
			return
		self.return_state = True
		serviceHandler = eServiceCenter.getInstance()
		offline = serviceHandler.offlineOperations(self.service)
		result = False
		if offline is not None:
			if not offline.deleteFromDisk(0):
				result = True
		if result == False:
			self.session.open(MessageBox, _("Delete failed!"), MessageBox.TYPE_ERROR)
		else:
			self.getMyDirs(self.anytimefolder, 3, self.genre_auswahl)

	def checkTimerState(self, service):
		if not service:
			return None
		moviename = os.path.realpath(service.getPath())
		if NavigationInstance.instance.getRecordings():
			for timer in NavigationInstance.instance.RecordTimer.timer_list:
				if timer.state == TimerEntry.StateRunning:
					if timer.justplay:
						pass
					else:
						timerfile = os.path.realpath(timer.Filename + ".ts")
						if timerfile == moviename:
							return timer
		return None

	# alternate infoscreen taken from MovieSelection

	def showEventInformation(self):
		from Screens.EventView import EventViewSimple
		from ServiceReference import ServiceReference
		if self.currentList == "movieselect":
			self.service = self['movieselect'].getCurrent()[0][4]
		else:
			return
		if self.service is None:
			return
		info = self.serviceHandler.info(self.service)
		if info is None:
			return
		#evt = info.getEvent(self.service)
		evt = self.service and info and info.getEvent(self.service)
		if evt:
			self.session.open(EventViewSimple, evt, ServiceReference(self.service))

	def movieinfoListEntry(self, entry):
		return [entry,
			(eListboxPythonMultiContent.TYPE_TEXT, 5, 0, 880, 40, 0, RT_HALIGN_LEFT, entry[2]),
			(eListboxPythonMultiContent.TYPE_TEXT, 1010, 0, 120, 40, 0, RT_HALIGN_LEFT, entry[3])
			]

	def unmatchMovieInfo(self):
		exist = self['movieselect'].getCurrent()
		if exist:
			title = self['movieselect'].getCurrent()[0][0]
			m_id_movie = None
			tags = self['movieselect'].getCurrent()[0][9]
			if tags.has_key("tmdb_id"):
				m_id_movie = tags["tmdb_id"]
				sky_title = None
			sql.resetMovieInfoActive(id_events=None, m_id_movie=m_id_movie, m_name="", sky_title=title, id_themoviedb=None)
			self['movieinfo_bg'].hide()
			self['movieinfo'].hide()
			self['movieinfo_red_label'].hide()
			self['movieinfo_green_label'].hide()
			self['movieinfo_red'].hide()
			self['movieinfo_green'].hide()
			self.movieinfoVisible = False
			self["movieinfo_actions"].setEnabled(False)
			self["mainscreen_actions"].setEnabled(True)
			self.getMyDirs(self.anytimefolder, 3, self.genre_auswahl)
		else:
			return

	def customSearchMovieInfo(self):
		#return
		exist = self['movieselect'].getCurrent()
		if exist:
			title = self['movieselect'].getCurrent()[0][0]
		else:
			title = ""
		info_title = "Film suchen"
		self.session.openWithCallback(self.gotMovieSearchName, VirtualKeyBoard, title=info_title, text=title)

	def gotMovieSearchName(self, title):
		if not title or len(title) < 3:
			return
		self.searchMovieInfo(language="de", title=title)

	def searchMovieInfo(self, language="de", title=""):
		if not title or len(title) < 3:
			exist = self['movieselect'].getCurrent()
			if not exist:
				return
			title = self['movieselect'].getCurrent()[0][0]

		self.id_events = None

		# try some fallbacks, if we did not find anything
		try:
			res = self.mInfo.getListFor(searchStr=title, split=False, language=language)
			if not res or len(res) < 1:
				res = self.mInfo.getListFor(searchStr=title.split("-")[0].strip(), split=False, language=language)
				if not res or len(res) < 1:
					res = self.mInfo.getListFor(searchStr=title.split(":")[0].strip(), split=False, language=language)
					if not res or len(res) < 1:
						res = self.mInfo.getListFor(searchStr=title.split("...")[0].strip(), split=False, language=language)
						if not res or len(res) < 1:
							# ok, we give up
							#self.session.open(MessageBox, "Keine Info gefunden für:\n{0}".format(title), MessageBox.TYPE_INFO, timeout=-1)
							#return
							res = []
		except Exception:
			sys.exc_clear()
			res = []

		self["mainscreen_actions"].setEnabled(False)
		self["movieinfo_actions"].setEnabled(True)
		self['movieinfo'].show()
		self['movieinfo_bg'].show()
		self['movieinfo_red'].show()
		self['movieinfo_green'].show()
		self['movieinfo_red_label'].show()
		self['movieinfo_green_label'].show()
		self.movieinfoVisible = True
		self.getMovieSearchList(searchlist=res, id_events=self.id_events, sky_title=title)
		return

	def getMovieSearchList(self, searchlist=None, id_events=0, sky_title=""):
		#if not searchlist or len(searchlist) < 1:
		#	return
		idx = -1
		sel_idx = -1
		myList = None
		myList = []
		self.movieinfoSelectList.setList(myList)
		for t_row in searchlist:
			idx += 1
			if self.current_m_id_movie and self.current_m_id_movie == int(t_row["m_id_movie"]):
				sel_idx = idx
			myList.append([
					t_row["m_movie_url"],
					t_row["m_title_org"],
					t_row["m_title"],
					t_row["m_date"],
					t_row["m_id_movie"],
					t_row["m_poster_url"],
					id_events,
					sky_title
					])
		self.movieinfoSelectList.setList(map(self.movieinfoListEntry, myList))
		if myList and len(myList) > 0:
			self['movieinfo'].moveToIndex(sel_idx)

	def getMovieInfo(self, movieURL=None, movieTitle="", posterUrl="", id_events=0, sky_title=""):
		if not movieURL:
			return False
		movieinfo = None
		movieinfo = self.mInfo.getInfoFor(movieURL=movieURL, movieTitle=movieTitle, idMovie="", language="de", lastlang=-1)
		if not movieinfo or len(movieinfo) < 1:
			# fallback language english
			movieinfo = self.mInfo.getInfoFor(movieURL=movieURL, movieTitle=movieTitle, idMovie="", language="en", lastlang=-1)
			if not movieinfo or len(movieinfo) < 1:
				self.session.open(MessageBox, "Keine Info für:\n{0}".format(movieURL), MessageBox.TYPE_INFO, timeout=3)
				return False

		if len(movieinfo[0]['m_name']) > 0:
			m_name = str(movieinfo[0]['m_name'])
		else:
			m_name = None

		if len(movieinfo[0]['m_id_movie']) > 0:
			m_id_movie = int(movieinfo[0]['m_id_movie'])
		else:
			m_id_movie = None

		if len(movieinfo[0]['m_title_org']) > 0:
			m_title_org = str(movieinfo[0]['m_title_org'])
		else:
			m_title_org = ""

		if len(movieinfo[0]['m_year']) > 0:
			m_year = str(movieinfo[0]['m_year'])
		else:
			m_year = ""

		if len(movieinfo[0]['m_description']) > 0:
			m_description = str(movieinfo[0]['m_description'])
		else:
			m_description = ""

		if len(movieinfo[0]['m_genre']) > 0:
			m_genre = movieinfo[0]['m_genre']
		else:
			m_genre = []

		if movieinfo[0]['m_rating']:
			m_rating = str(movieinfo[0]['m_rating'])
		else:
			m_rating = "0"

		# got movieinfo, store it
		res = sql.addNewMovieInfo(id_events, m_id_movie, m_name, m_year, m_title_org, m_rating, m_description, m_genre, sky_title)

		if not res:
			return False

		# update cover in database
		if posterUrl and posterUrl != "":
			coverurl = posterUrl
		else:
			if len(movieinfo[0]['m_posters']) > 0:
				coverurl = movieinfo[0]['m_posters']
				# currently we only use the first poster
				#getPage(coverurl, headers=self.headers2, agent=self.agent).addCallback(self.gotPoster, id_events, m_id_movie, coverurl).addErrback(self.dataErrorPage)
				data = None
				socket.setdefaulttimeout(10)
				req = Request(coverurl, None, self.headers2)
				response = urlopen(req)
				data = response.read()
				self.gotPoster(data, id_events, m_id_movie, coverurl)
		return True

	def gotPoster(self, data, id_events, m_id_movie, coverurl):
		if data:
			sql.addMovieInfoPoster(id_events, m_id_movie, coverurl, data)

	def dataErrorPage(self, error):
		self.clearFilmInfoScreen()
		self['name'].setText("Fehler beim Laden.")
		self['handlung'].setText("%s" % error)
		print error

	def renameFile(self, filepath=None, serviceref=None, title=None, year=None):
		if not filepath or not serviceref or not title:
			exist = self['movieselect'].getCurrent()
			if not exist:
				return
			serviceref = self['movieselect'].getCurrent()[0][4]
			filepath = self['movieselect'].getCurrent()[0][3]
			info = self.serviceHandler.info(serviceref)
			if info is None:
				return
			title = info.getName(serviceref)

		is_timer = self.checkTimerState(serviceref)
		if is_timer is not None:
			return
		src_file = filepath
		src_dir = os.path.dirname(src_file) + "/"
		if not year:
			new_name = "{0}".format(title)
		else:
			new_name = "{0} ({1})".format(title, year)
		if len(new_name) > 0:
			# get clean name
			dst_file = getRecordingFilename(new_name, src_dir)
			dst_file = os.path.splitext(dst_file)[0] # remove the suffix
			#dst_file = src_dir + new_name
			# build list of files
			src_file_list = glob.glob(os.path.splitext(src_file)[0] + ".*?")
			for old_file in src_file_list:
				parts = os.path.splitext(old_file)
				if len(parts) > 1:
					new_file = dst_file + os.path.splitext(parts[0])[1] + parts[1]
				else:
					new_file = dst_file + parts[1]
				if fileExists(old_file) and not fileExists(new_file):
					if old_file != new_file: # little bit paranoid, but just to be sure
						os.rename(old_file, new_file)
