#-*- coding: utf-8 -*-
from Components.ConfigList import ConfigListScreen
from Screens.Screen import Screen
from Tools.Directories import fileExists, resolveFilename, SCOPE_PLUGINS
from Components.ActionMap import NumberActionMap, ActionMap
from Components.Button import Button
from Components.Label import Label
from Screens.MessageBox import MessageBox
from Components.ScrollLabel import ScrollLabel
from Tools.LoadPixmap import LoadPixmap
from Components.config import config, ConfigSelection, getConfigListEntry, ConfigText, ConfigDirectory, ConfigYesNo, ConfigSelection, ConfigSubsection, ConfigPIN, configfile, ConfigInteger, NoSave, ConfigNothing, ConfigClock
from Components.UsageConfig import preferredTimerPath, preferredInstantRecordPath
from Tools.Directories import resolveFilename, SCOPE_HDD
from enigma import eTimer
import re
import os
import sys
import shutil
import time

# our custom classes
from SkyMainFunctions import getPluginPath, getCurrentTimestamp, getDateTimeFromTimestamp2, setWecker
from SkyGetTvGuide import SkyGetTvGuide
from SkyRunAutocheck import SkyRunAutocheck
from SkySelectAnytimeFolder import SkySelectAnytimeFolder
from SkySelectSkydbFolder import SkySelectSkydbFolder
from SkyAddedEdit import SkyAddedEdit
from SkySql import *
# popup screen
from SkyPopUp import SkyHelpAll
# moved from main
from SkyChannelSelect import SkyChannelSelect
from SkyGenreSelect import SkyGenreSelect


pluginName = "SkyRecorder"
pluginVersion = "v1.7.1"
contentSize = 20

pluginfolder = getPluginPath()

defaultmoviefolder = resolveFilename(SCOPE_HDD)
recordings_base_folder = "SkyRecorder"
anytimefolder = defaultmoviefolder  #+ recordings_base_folder + "/"

### start config
config.plugins.skyrecorder = ConfigSubsection()
config.plugins.skyrecorder.auto_recordtimer_entries = ConfigYesNo(default = False)
config.plugins.skyrecorder.pluginname = ConfigText(pluginName)
config.plugins.skyrecorder.version = ConfigText(pluginVersion)
config.plugins.skyrecorder.contentsize = ConfigInteger(20)
config.plugins.skyrecorder.timerdays_allowed = ConfigSelection(
			default = "['all']",
			choices = [
				("['all']", _("jeden Wochentag")),
				("['Mon','Tue','Wed','Thu','Fri']", _("Montag bis Freitag")),
				("['Sun','Sat']", _("Samstag und Sonntag")),
				("['Sun','Fri','Sat']", _("Freitag, Samstag und Sonntag"))])
config.plugins.skyrecorder.guide_days_to_scan = ConfigSelection(
			default = "1",
			choices = [
				("1", _("einen Tag (empfohlen)")),
				("2", _("zwei Tage")),
				("3", _("drei Tage")),
				("4", _("vier Tage")),
				("5", _("fünf Tage")),
				("6", _("sechs Tage")),
				("7", _("eine Woche")),
				("14", _("zwei Wochen"))])
config.plugins.skyrecorder.fromtime = ConfigInteger(00, (00,23))
config.plugins.skyrecorder.totime = ConfigInteger(23, (00,23))
config.plugins.skyrecorder.autoupdate_database = ConfigYesNo(default = False)
config.plugins.skyrecorder.database_update_time = ConfigClock(default = ((9 * 60 + 0) * 60))
config.plugins.skyrecorder.anytime_skin = ConfigSelection(
			default = "original",
			choices = [
				("elgato", _("elgato")),
				("metrix", _("metrix")),
				("original", _("original")),
				("ax_blue_fhd", _("ax_blue_fhd")),
				("blue_line_fhd", _("blue_line_fhd")),
				("universal_fhd", _("universal_fhd"))])
				
				
# store our last check-timestamp. needed for our wakeMeUp function (see below at the end of this script)
config.plugins.skyrecorder.lastchecked = ConfigInteger(0)
config.plugins.skyrecorder.next_update = ConfigInteger(-1)
config.plugins.skyrecorder.wakeup = ConfigYesNo(default = False)
config.plugins.skyrecorder.after_update = ConfigSelection(
			default = "none",
			choices = [
				("none", ("nichts")),
				("standby", ("Standby")),
				("deepstandby", ("STB herunterfahren"))])

config.plugins.skyrecorder.fake_entry = NoSave(ConfigNothing())
config.plugins.skyrecorder.anytimefolder = ConfigText(default=anytimefolder)
config.plugins.skyrecorder.anytimefolder3d = ConfigText(default=anytimefolder)
config.plugins.skyrecorder.create_dirtree = ConfigYesNo(default = True)
#config.plugins.skyrecorder.skydb = ConfigText(default=defaultmoviefolder + "skydb.db")
config.plugins.skyrecorder.skydb = ConfigText(default=pluginfolder + "/skydb.db")
config.plugins.skyrecorder.silent_timer_mode = ConfigYesNo(default = False)
config.plugins.skyrecorder.timer_mode = ConfigSelection(default = "0", choices = [("0", _("Aufnahme")),("1", _("Erinnerung"))])
config.plugins.skyrecorder.msgtimeout = ConfigInteger(3)
config.plugins.skyrecorder.max_per_page = ConfigInteger(10,(1,9999))
config.plugins.skyrecorder.mainlisttype = ConfigSelection(default = "0", choices = [("0", _("einfach")),("1", _("erweitert"))])
# let us set maring_before and margin_after in the plugin itself
# so we have better control of this values if the user change the system margins after adding timers
try:
	default_before = int(config.recording.margin_before.value)
	default_after = int(config.recording.margin_after.value)
except Exception:
	default_before = 0
	default_after = 0
config.plugins.skyrecorder.margin_before = ConfigInteger(default_before, (00,99))
config.plugins.skyrecorder.margin_after = ConfigInteger(default_after, (00,99))
# let us choose from a list of ordering options for the main screen
config.plugins.skyrecorder.main_list_order = ConfigSelection(
			default = "channel",
			choices = [
				("channel", ("Sender gruppiert von A-Z")),
				("status", ("nach Status")),
				("begin_asc", ("Startzeit aufsteigend")),
				("begin_desc", ("Startzeit absteigend")),
				("title", ("Sendungstitel von A-Z")),
				("genre", ("Nach Genre"))])

config.plugins.skyrecorder.short_record_filenames = ConfigYesNo(default = False)
config.plugins.skyrecorder.only_active_genres = ConfigYesNo(default = False)
config.plugins.skyrecorder.only_new_events = ConfigYesNo(default = True)
config.plugins.skyrecorder.only_active_channels = ConfigYesNo(default = True)
config.plugins.skyrecorder.max_parallel_timers = ConfigSelection(
			default = "1000",
			choices = [
				("1000", _("automatisch")),
				("1", _("eine Aufnahme gleichzeitig")),
				("2", _("zwei Aufnahmen gleichzeitig")),
				("3", _("drei Aufnahmen gleichzeitig")),
				("4", _("vier Aufnahmen gleichzeitig"))])
config.plugins.skyrecorder.rename_matched_movies = ConfigYesNo(default = True)
config.plugins.skyrecorder.autoupdate_tmdb = ConfigYesNo(default = True)
config.plugins.skyrecorder.apikey = ConfigText("00000000000000000000000000000000")
### end config



class SkyRecorderSettings(Screen, ConfigListScreen):
	
	def __init__(self, session, firstRun=False):
		self.session = session
		
		path = "%s/skins/%s/screen_settings.xml" % (getPluginPath(), config.plugins.skyrecorder.anytime_skin.value)
		with open(path, "r") as f:
			self.skin = f.read()
			f.close()	
		
		Screen.__init__(self, session)
		
		self.createConfigList()
		ConfigListScreen.__init__(self, self.configlist, session = self.session)
		
		self.popUpScreen = self.session.instantiateDialog(SkyHelpAll)
		self.popUpIsVisible = False
		
		self["actions"]  = ActionMap(["OkCancelActions","ShortcutActions", "EPGSelectActions", "WizardActions", "ColorActions", "NumberActions", "MenuActions", "MoviePlayerActions","HelpActions"], {
			"ok": self.keyOK,
			"cancel": self.keyCancel,
			"nextBouquet" : self.log_up,
			"prevBouquet" : self.log_down,
			"blue" : self.askAddRecordimerNow,
			"menu" : self.fullLog,
			"yellow" : self.readAdded,
			"green" : self.saveSettings,
			"red" : self.askCleanUpDatabase,
			"info" : self.askUpdateDatabase,
			"displayHelp" : self.togglePopUp
		}, -1)
		
		self["disabled_actions"] = ActionMap(["OkCancelActions","ShortcutActions", "EPGSelectActions", "WizardActions", "ColorActions", "NumberActions", "MenuActions", "MoviePlayerActions","HelpActions"],
		{
			"ok": self.keyCancel,
			"cancel": self.keyCancel,
			"up" : self.help_page_up,
			"down" : self.help_page_down,
			"right" : self.ignoreKey,
			"left" : self.ignoreKey,
			"nextBouquet" : self.help_page_up,
			"prevBouquet" : self.help_page_down,
			"displayHelp" : self.togglePopUp
		}, -1)

		self["disabled_actions"].setEnabled(False)
		
		self['title'] = Label(pluginName + " " + pluginVersion)
		self["log"] = ScrollLabel()
		
		self.sky_log_path = "/usr/lib/enigma2/python/Plugins/Extensions/skyrecorder/sky_log"
		
		# start reading the last 7 lines from our logfile every second
		self.tempTimer = None
		self.onLayoutFinish.append(self.startReadLog)
		#self.onLayoutFinish.append(self.readLog)
		
		
	def createConfigList(self):
		self.configlist = []
		if config.plugins.skyrecorder.lastchecked and config.plugins.skyrecorder.lastchecked.value:
			lastUpdate = getDateTimeFromTimestamp2(config.plugins.skyrecorder.lastchecked.value)
		else:
			lastUpdate = ""
		if config.plugins.skyrecorder.next_update and config.plugins.skyrecorder.next_update.value > 0:
			nextUpdate = getDateTimeFromTimestamp2(config.plugins.skyrecorder.next_update.value)
		else:
			nextUpdate = ""
		self.configlist.append(getConfigListEntry("----- Datenbank (letztes Update: {0}) -----".format(lastUpdate), config.plugins.skyrecorder.fake_entry))
		self.configlist.append(getConfigListEntry("Datenbank automatisch aktualisieren:", config.plugins.skyrecorder.autoupdate_database))
		self.autoUpdateTime = getConfigListEntry("Uhrzeit für Updates (nächstes Update: {0}):".format(nextUpdate), config.plugins.skyrecorder.database_update_time)
		self.configlist.append(self.autoUpdateTime)
		self.configlist.append(getConfigListEntry("Nur Neuerscheinungen suchen:", config.plugins.skyrecorder.only_new_events))
		self.configlist.append(getConfigListEntry("Nur aktivierte Sender suchen:", config.plugins.skyrecorder.only_active_channels))
		self.configlist.append(getConfigListEntry("Wie weit im Voraus laden:", config.plugins.skyrecorder.guide_days_to_scan))
		
		self.get_skydbfolder = getConfigListEntry("Datenbank:", NoSave(ConfigSelection(default="0", choices = [("0", config.plugins.skyrecorder.skydb.value)])))
		self.configlist.append(self.get_skydbfolder)
		
		self.configlist.append(getConfigListEntry("----- Timereinstellungen -----", config.plugins.skyrecorder.fake_entry))
		self.configlist.append(getConfigListEntry("Timer automatisch hinzufügen:", config.plugins.skyrecorder.auto_recordtimer_entries ))
		self.configlist.append(getConfigListEntry("Timermodus:", config.plugins.skyrecorder.timer_mode))
		self.configlist.append(getConfigListEntry("Timereinträge erlaubt für:", config.plugins.skyrecorder.timerdays_allowed))
		self.configlist.append(getConfigListEntry("Zeitspanne von:", config.plugins.skyrecorder.fromtime))
		self.configlist.append(getConfigListEntry("Zeitspanne bis:", config.plugins.skyrecorder.totime))
		self.configlist.append(getConfigListEntry("Timervorlauf (in min.):", config.plugins.skyrecorder.margin_before))
		self.configlist.append(getConfigListEntry("Timernachlauf (in min.):", config.plugins.skyrecorder.margin_after))
		self.configlist.append(getConfigListEntry("Timerbegrenzung:", config.plugins.skyrecorder.max_parallel_timers))
		self.configlist.append(getConfigListEntry("Keine Timermeldungen anzeigen:", config.plugins.skyrecorder.silent_timer_mode))
		
		self.configlist.append(getConfigListEntry("----- Allgemein -----", config.plugins.skyrecorder.fake_entry))
		self.edit_channellist = getConfigListEntry("Senderliste", config.plugins.skyrecorder.fake_entry)
		self.configlist.append(self.edit_channellist)
		self.edit_genrelist = getConfigListEntry("Genreliste (für automatische Timer)", config.plugins.skyrecorder.fake_entry)
		self.configlist.append(self.edit_genrelist)
		
		self.configlist.append(getConfigListEntry("Nur aktivierte Genre in Hauptliste anzeigen:", config.plugins.skyrecorder.only_active_genres))
		self.configlist.append(getConfigListEntry("Deep Standby beenden für Timerupdates:", config.plugins.skyrecorder.wakeup))
		self.configlist.append(getConfigListEntry("Aktion nach Timerupdates:", config.plugins.skyrecorder.after_update))
		self.get_anytimefolder = getConfigListEntry("Aufnahmeordner (Basis):", NoSave(ConfigSelection(default="0", choices = [("0", config.plugins.skyrecorder.anytimefolder.value)])))
		self.configlist.append(self.get_anytimefolder)
		self.get_anytimefolder3d = getConfigListEntry("Aufnahmeordner (3D):", NoSave(ConfigSelection(default="0", choices = [("0", config.plugins.skyrecorder.anytimefolder3d.value)])))
		self.configlist.append(self.get_anytimefolder3d)
		self.configlist.append(getConfigListEntry("SkyRecorder Ordnerstruktur für Aufnahmen verwenden:", config.plugins.skyrecorder.create_dirtree))
		#self.configlist.append(getConfigListEntry("kurze Dateinamen für Aufnahmen verwenden:", config.plugins.skyrecorder.short_record_filenames))
		self.configlist.append(getConfigListEntry("Filme im Archiv nach TMDb-Name umbenennen:", config.plugins.skyrecorder.rename_matched_movies))
		self.configlist.append(getConfigListEntry("TMDb Infos automatisch beim Datenbankupdate abrufen:", config.plugins.skyrecorder.autoupdate_tmdb))
		self.configlist.append(getConfigListEntry("API-Key f�r TMDB:", config.plugins.skyrecorder.apikey))
		self.configlist.append(getConfigListEntry("Sortierung der Sendungsliste:", config.plugins.skyrecorder.main_list_order))
		self.configlist.append(getConfigListEntry("maximale Einträge pro Seite:", config.plugins.skyrecorder.max_per_page))
		self.configlist.append(getConfigListEntry("Darstellung der Sendungsliste:", config.plugins.skyrecorder.mainlisttype))
		self.configlist.append(getConfigListEntry("Skinauswahl:", config.plugins.skyrecorder.anytime_skin))
		self.reset_logfile = getConfigListEntry("Logdatei zurücksetzen", config.plugins.skyrecorder.fake_entry)
		self.configlist.append(self.reset_logfile)
		self.cleanup_tmdb_data = getConfigListEntry("Alle TMDb-Daten aus skydb.db löschen", config.plugins.skyrecorder.fake_entry)
		self.configlist.append(self.cleanup_tmdb_data)
		self.skydb_vacuum = getConfigListEntry("Datenbank optimieren", config.plugins.skyrecorder.fake_entry)
		self.configlist.append(self.skydb_vacuum)
		
	
	def ignoreKey(self):
		pass

	def togglePopUp(self,hide_me=False):
		if self.popUpIsVisible or hide_me:
			self.popUpScreen.hide()
			self.popUpIsVisible = False
			self["config_actions"].setEnabled(True)
			self["actions"].setEnabled(True)
			self["disabled_actions"].setEnabled(False)
			
			return
		self["config_actions"].setEnabled(False)
		self["actions"].setEnabled(False)
		self["disabled_actions"].setEnabled(True)
		self.popUpScreen.show()
		self.popUpScreen.loadHelpText()
		self.popUpIsVisible = True
		

	def startReadLog(self):
		if not self.tempTimer:
			self.tempTimer = eTimer()
			self.tempTimer.callback.append(self.readLog)
		self.tempTimer.stop()
		self.tempTimer.start(1000, False)
		
	
	def fullLog(self):
		self.readLog(10000)
		
	def readLog(self, maxlines=7):
		try:
			if SkyGetTvGuide.instance:
				if not SkyGetTvGuide.instance.IS_RUNNING:
					self.changedEntry()
					if self.tempTimer:
						self.tempTimer.stop()
		except Exception:
			sys.exc_clear()
				
		if fileExists(self.sky_log_path):
			n = 0
			text = ""
			with open(self.sky_log_path, "r") as f:
				for rawData in reversed(f.readlines()):
					data = re.findall('"(.*?)"', rawData, re.S)
					if data:
						dump = "%s\n" % data[0]
						text += dump
					n += 1
					if n >= maxlines:
						break
			self["log"].setText(text)
			rawData = None
			text = None


	def changeTimer(self):
		self.startReadLog()
		
		if config.plugins.skyrecorder.autoupdate_database.value:
			print "[skyrecorder] checktimer."
			try:
				if SkyGetTvGuide.instance.refreshTimer:
					SkyGetTvGuide.instance.refreshTimer.stop()
					SkyGetTvGuide.instance.refreshTimer = None
					SkyGetTvGuide.instance.refreshTimer = eTimer()
					SkyGetTvGuide.instance.refreshTimer.callback.append(SkyGetTvGuide.instance.start)
					interval = int(config.plugins.skyrecorder.next_update.value) - getCurrentTimestamp()
					if interval > 10 and interval <= 5184000: # 10 seconds buffer, but lower or equal than 1 day
						#SkyGetTvGuide.instance.timerinterval = interval * 1000 # milleseconds
						#SkyGetTvGuide.instance.refreshTimer.start(SkyGetTvGuide.instance.timerinterval)
						SkyGetTvGuide.instance.timerinterval = interval
						SkyGetTvGuide.instance.refreshTimer.startLongTimer(SkyGetTvGuide.instance.timerinterval)
					
				else:
					#config.plugins.skyrecorder.lastchecked.value = getCurrentTimestamp()
					#config.plugins.skyrecorder.lastchecked.save()
					#configfile.save()
					SkyGetTvGuide(self.session, False) # do not start it right now, we can run it manually, if we want to
			except AttributeError:
				# was not running - start it now
				#config.plugins.skyrecorder.lastchecked.value = getCurrentTimestamp()
				#config.plugins.skyrecorder.lastchecked.save()
				#configfile.save()
				SkyGetTvGuide(self.session, False) # do not start it right now, we can run it manually, if we want to
		else:
			try:
				if SkyGetTvGuide.instance.refreshTimer:
					SkyGetTvGuide.instance.refreshTimer.stop()
					SkyGetTvGuide.instance.refreshTimer = None
			except AttributeError:
				# was never running
				print "[skyrecorder] changeTimer did nothing"

	
	def log_up(self):
		self["log"].pageUp()


	def log_down(self):
		self["log"].pageDown()
	
	
	def help_page_up(self):
		self.popUpScreen["text"].pageUp()


	def help_page_down(self):
		self.popUpScreen["text"].pageDown()
	
	
	def readAdded(self):
		self.session.openWithCallback(self.changedEntry, SkyAddedEdit)
		
	
	def keyOK(self):
		self.togglePopUp(True)
		if self["config"].getCurrent() == self.get_anytimefolder:
			self.session.openWithCallback(self.gotAnytimeFolder, SkySelectAnytimeFolder, config.plugins.skyrecorder.anytimefolder.value)
		elif self["config"].getCurrent() == self.get_anytimefolder3d:
			self.session.openWithCallback(self.gotAnytimeFolder3d, SkySelectAnytimeFolder, config.plugins.skyrecorder.anytimefolder3d.value)

		elif self["config"].getCurrent() == self.get_skydbfolder:
			if config.plugins.skyrecorder.autoupdate_database and config.plugins.skyrecorder.autoupdate_database.saved_value:
				message = self.session.open(MessageBox, _("Achtung!\nBitte zuerst die automatische Datenbankaktualisierung beenden und das Plugin neu starten. Danach kann der Speicherort der Datenbank geändert werden."), MessageBox.TYPE_INFO, timeout=-1)
				return
			self.session.openWithCallback(self.gotSkydbFolder, SkySelectSkydbFolder, config.plugins.skyrecorder.skydb.value)

		elif self["config"].getCurrent() == self.cleanup_tmdb_data:
			mymsg = "{0}\nSollen alle TMDb-Daten jetzt gelöscht werden?\nAchtung, der Vorgang kann die STB für eine Zeit lang blockieren.".format(pluginName)
			self.session.openWithCallback(self.cleanupTMDbData,  MessageBox, _(mymsg), MessageBox.TYPE_YESNO, timeout=-1, default=True)
		
		elif self["config"].getCurrent() == self.skydb_vacuum:
			mymsg = "{0}\nSoll die Datenbank jetzt optimiert werden?\nAchtung, der Vorgang kann die STB für eine Zeit lang blockieren.".format(pluginName)
			self.session.openWithCallback(self.skydbVacuum,  MessageBox, _(mymsg), MessageBox.TYPE_YESNO, timeout=-1, default=True)
		
		elif self["config"].getCurrent() == self.reset_logfile:
			mymsg = "{0}\nSoll die Logdatei jetzt gelöscht werden?".format(pluginName)
			self.session.openWithCallback(self.resetLogfile,  MessageBox, _(mymsg), MessageBox.TYPE_YESNO, timeout=-1, default=True)
		
		elif self["config"].getCurrent() == self.edit_channellist:
			self.session.openWithCallback(self.changedEntry, SkyChannelSelect)
			
		elif self["config"].getCurrent() == self.edit_genrelist:
			self.session.openWithCallback(self.changedEntry, SkyGenreSelect)


	def resetLogfile(self,canstart=True):
		if not canstart:
			return
		print "[skyrecorder] reset logfile."
		with open(self.sky_log_path , "w") as f:
			f.write('')
		self.changedEntry()
		self.startReadLog()
		
	def cleanupTMDbData(self,canstart=True):
		if not canstart:
			return
		print "[skyrecorder] cleanup skydb.db TMDb-data"
		sql.cleanupTMDbData(False)
		self.changedEntry()
		self.startReadLog()
		
	def skydbVacuum(self,canstart=True):
		if not canstart:
			return
		print "[skyrecorder] running VACUUM on skydb.db"
		sql.shrinkDatabase()
		self.changedEntry()
		self.startReadLog()
	
	def buildDirTree(self,my_base_folder=None):
		if not my_base_folder:
			return False
		
		if not config.plugins.skyrecorder.create_dirtree.value:
			return True
		
		if not os.path.exists(my_base_folder):
			try:
				os.makedirs(my_base_folder, mode=0777)
			except Exception:
				return False
				
		try:
			sql.cur.execute('SELECT SQLITE_VERSION()')
		except Exception:
			sys.exc_clear()
			try:
				sql.connect()
			except Exception:
				return False
		
		my_dirs = sql.getGroupnames()
		if not my_dirs:
			return False
			
		for t_row in my_dirs:
			a_dir = list(t_row)
			a_dir = str(a_dir[0])
			group_dir = os.path.join(my_base_folder, a_dir)
			if not os.path.exists(group_dir):
				try:
					os.makedirs(group_dir, mode=0777)
				except Exception:
					return False
		return True

	def gotAnytimeFolder(self, res):
		if res is not None:

			if not config.plugins.skyrecorder.create_dirtree.value:
				config.plugins.skyrecorder.anytimefolder.value = res
				config.plugins.skyrecorder.anytimefolder.save()
			else:
				test_str = res.split("/")[-2:-1][0].lower()
				if test_str != recordings_base_folder.lower():
					if test_str == "":
						res += "/" + recordings_base_folder + "/"
					else:
						res += recordings_base_folder + "/"
				
				config.plugins.skyrecorder.anytimefolder.value = res
				config.plugins.skyrecorder.anytimefolder.save()
				# we got a new folder, lets try to build the dirtree for our recordings
				retval = self.buildDirTree(config.plugins.skyrecorder.anytimefolder.value)
				if not retval:
					self.session.open(MessageBox, _("{0}\nKonnte den Verzeichnisbaum für die Aufnahmen nicht erstellen.".format(pluginName)), MessageBox.TYPE_INFO, timeout=-1)
			self.changedEntry()
	
	def gotAnytimeFolder3d(self, res):
		if res is not None:

			if not config.plugins.skyrecorder.create_dirtree.value:
				config.plugins.skyrecorder.anytimefolder3d.value = res
				config.plugins.skyrecorder.anytimefolder3d.save()
			else:
				test_str = res.split("/")[-2:-1][0].lower()
				if test_str != recordings_base_folder.lower():
					if test_str == "":
						res += "/" + recordings_base_folder + "/"
					else:
						res += recordings_base_folder + "/"
				
				config.plugins.skyrecorder.anytimefolder3d.value = res
				config.plugins.skyrecorder.anytimefolder3d.save()
				# we got a new folder, lets try to build the dirtree for our recordings
				retval = self.buildDirTree(config.plugins.skyrecorder.anytimefolder3d.value)
				if not retval:
					self.session.open(MessageBox, _("{0}\nKonnte den Verzeichnisbaum für die Aufnahmen nicht erstellen.".format(pluginName)), MessageBox.TYPE_INFO, timeout=-1)
			self.changedEntry()
	
	def askOverwriteSkydb(self,dbpath):
		mymsg = "{0}\nEs befindet sich schon eine skydb.db in '{1}.'\nSoll sie überschrieben werden?".format(pluginName,dbpath)
		self.session.openWithCallback(self.confirmOverwriteSkydb,  MessageBox, _(mymsg), MessageBox.TYPE_YESNO, timeout=-1, default=True)
	
	def confirmOverwriteSkydb(self,result):
		return result
	
	def gotSkydbFolder(self, res):
		# check if we have to create the database from scratch
		retval = None
		can_delete = True
		if res is not None:
			
			if not os.path.exists(res):
				return
			
			try:
				currentdb = config.plugins.skyrecorder.skydb.value
			except Exception:
				sys.exc_clear()
				currentdb = getPluginPath() + "/skydb.db"
				
			new_db = res + "skydb.db"
			if os.path.exists(new_db):
				can_delete = self.askOverwriteSkydb(res)
			
			retval = True
			if can_delete:
				if os.path.exists(currentdb):
					try:
						shutil.copy2(currentdb, new_db)
					except Exception:
						sys.exc_clear()
						from SkyCreateDatabase import buildSkydb
						retval = buildSkydb(target=new_db,rebuild=True,backup=False)
				else:
					from SkyCreateDatabase import buildSkydb
					retval = buildSkydb(target=new_db,rebuild=True,backup=False)
			
			if retval:
				config.plugins.skyrecorder.skydb.value = new_db
				config.plugins.skyrecorder.skydb.save()
				config.save()
				configfile.save()
			
			try:
				sql.disconnect()
				sql.connect()
			except Exception:
				sys.exc_clear()
				return
			self.changedEntry()


	def changedEntry(self):
		self.createConfigList()
		self["config"].setList(self.configlist)


	def saveSettings(self):
		self.togglePopUp(True)
		print "saved"
		for x in self["config"].list:
			if x == self.autoUpdateTime:
				alarm = setWecker(x[1].value)
				config.plugins.skyrecorder.next_update.value = alarm
				#config.plugins.skyrecorder.next_update.save_forced = True
				config.plugins.skyrecorder.next_update.save()
			#x[1].save_forced = True
			x[1].save()
		config.plugins.skyrecorder.pluginname.save_forced = True
		config.plugins.skyrecorder.pluginname.save()
		config.plugins.skyrecorder.version.save_forced = True
		config.plugins.skyrecorder.version.save()
		config.plugins.skyrecorder.skydb.save_forced = True
		config.plugins.skyrecorder.skydb.save()
		config.save()
		configfile.save()		

		self.changeTimer()
		if self.tempTimer:
			self.tempTimer.stop()
			
		# again, lets try to build the dirtree for our recordings
		retval = self.buildDirTree(config.plugins.skyrecorder.anytimefolder.value) and self.buildDirTree(config.plugins.skyrecorder.anytimefolder3d.value)
		if not retval:
			self.session.open(MessageBox, _("{0}\nKonnte den Verzeichnisbaum für die Aufnahmen nicht erstellen.".format(pluginName)), MessageBox.TYPE_INFO, timeout=-1)

		self.close()


	def killDatabaseUpdate(self):
		try:
			if SkyGetTvGuide.instance:
				SkyGetTvGuide.instance.IS_RUNNING = False
				time.sleep(2.0)
				sql.sqlCommit()
				del(SkyGetTvGuide.instance)
				self.changeTimer()
				#SkyGetTvGuide(self.session, oneShot=False, no_after_event=True)
				self.addLog("Datenbankupdate gestoppt.")
				self.session.open(MessageBox, _("{0}\nDatenbankupdate gestoppt.".format(pluginName)), MessageBox.TYPE_INFO, timeout=3)
		except Exception, e:
			self.session.open(MessageBox, _("{0}\n{1}".format(pluginName, e)), MessageBox.TYPE_ERROR, timeout=-1)
			sys.exc_clear()

		
	def tryToStopDatabseUpdate(self, retval=True):
		if retval:
			self.killDatabaseUpdate()
		return

	def askUpdateDatabase(self):
		self.togglePopUp(True)
		# try to break, if we want so
		try:
			if SkyGetTvGuide.instance:
				if SkyGetTvGuide.instance.IS_RUNNING and SkyGetTvGuide.instance.IS_RUNNING == True:
					mymsg = "Achtung!\nEin Datenbankupdate läuft schon im Hintergrund.\nSoll das Update jetzt abgebrochen werden?"
					self.session.openWithCallback(self.tryToStopDatabseUpdate,  MessageBox, _(mymsg), MessageBox.TYPE_YESNO, timeout=-1, default=False)
					return
		except Exception:
			sys.exc_clear()
		
		if config.plugins.skyrecorder.auto_recordtimer_entries.value: 
			mymsg = "{0}\nSoll die Datenbank jetzt aktualisiert werden?\nAchtung, 'automatische Timer hinzufügen' ist aktiviert und wird im Anschluss ausgeführt.".format(pluginName)
		else:
			mymsg = "{0}\nSoll die Datenbank jetzt aktualisiert werden?".format(pluginName)
		self.session.openWithCallback(self.updateDatabase,  MessageBox, _(mymsg), MessageBox.TYPE_YESNO, timeout=-1, default=True)
	
	
	def updateDatabase(self, canstart=True):
		if not canstart:
			return
		self.startReadLog()
		message = self.session.open(MessageBox, _("{0}\nAktualisiere Datenbank".format(pluginName)), MessageBox.TYPE_INFO, timeout=3)
		try:
			if SkyGetTvGuide.instance.refreshTimer:
				#SkyGetTvGuide.instance.refreshTimer.stop()
				SkyGetTvGuide.instance.start(oneShot=True,no_after_event=True)
				#SkyGetTvGuide.instance.refreshTimer.start()
			else:
				SkyGetTvGuide(self.session, oneShot=False,no_after_event=True)
				SkyGetTvGuide.instance.start(oneShot=True,no_after_event=True)
		except AttributeError:
			SkyGetTvGuide(self.session, oneShot=False, no_after_event=True)
			SkyGetTvGuide.instance.start(oneShot=True,no_after_event=True)

	
	def askAddRecordimerNow(self):
		self.togglePopUp(True)
		mymsg = "{0}\nSollen alle automatischen Timer jetzt hinzugefügt werden?".format(pluginName)
		self.session.openWithCallback(self.addRecordimerNow,  MessageBox, _(mymsg), MessageBox.TYPE_YESNO, timeout=-1, default=True)
	
	
	def addRecordimerNow(self, canstart=True):
		if not canstart:
			return
		SkyRunAutocheck(self.session,no_after_event=True)
	

	def askCleanUpDatabase(self):
		self.togglePopUp(True)
		self.includeAdded = False
		mymsg = "{0}\nSky TV-Guide Datenbank aufräumen.\nSollen auch alle gemerkten Timereinträge aus der Datenbank entfernt werden?".format(pluginName)
		self.session.openWithCallback(self.askCleanUpDatabaseGo,  MessageBox, _(mymsg), MessageBox.TYPE_YESNO, timeout=-1, default=False)
		

	def askCleanUpDatabaseGo(self,includeAdded=False):
		self.togglePopUp(True)
		self.includeAdded = includeAdded
		mymsg = "{0}\nSky TV-Guide Datenbank jetzt leeren?".format(pluginName)
		self.session.openWithCallback(self.cleanUpDatabase,  MessageBox, _(mymsg), MessageBox.TYPE_YESNO, timeout=-1, default=False)

	
	def cleanUpDatabase(self, cleanUp=False):
		if cleanUp is not True:
			return
		
		try:
			sql.cur.execute('SELECT SQLITE_VERSION()')
		except Exception:
			sys.exc_clear()
			try:
				sql.connect()
			except Exception:
				return
		res = sql.truncateDatabase(self.includeAdded)
		if res:
			self.session.open(MessageBox, _("{0}\nDie Datenbank wurde geleert.".format(pluginName)), MessageBox.TYPE_INFO, timeout=5)
		else:
			self.session.open(MessageBox, _("{0}\nDie Datenbank konnte nicht geleert werden.".format(pluginName)), MessageBox.TYPE_ERROR, timeout=-1)
	
	def addLog(self, text):
		if len(text) < 1:
			return
		# check the current file size truncate the file if size is greater than defined limit 200 KB (204800 Bytes)
		sizeb = os.path.getsize(self.sky_log_path)
		if sizeb > 204800:
			# truncate only the first 100 lines in file - delete the oldest ones
			with open(self.sky_log_path, "r+") as f:
				for x in xrange(100):
					f.readline()
					f.truncate()

		lt = time.localtime()
		datum = time.strftime("%d.%m.%Y - %H:%M:%S", lt)
		with open(self.sky_log_path , "a") as write_log:
			write_log.write('"%s - %s"\n' % (datum,text))
	
	def keyCancel(self):
		if self.popUpIsVisible:
			self.popUpScreen.hide()
			self.popUpIsVisible = False
			self["config_actions"].setEnabled(True)
			self["actions"].setEnabled(True)
			self["disabled_actions"].setEnabled(False)
			return
		
		for x in self["config"].list:
			x[1].cancel()
		if self.tempTimer:
			self.tempTimer.stop()
		self.close()
	
	def cancelSave(self):
		self.keyCancel()
