#-*- coding: utf-8 -*-
from Components.Label import Label
from Components.ScrollLabel import ScrollLabel
from Components.Sources.StaticText import StaticText
from Components.ActionMap import NumberActionMap, ActionMap
from Components.config import config
from Components.MenuList import MenuList
from Components.Pixmap import Pixmap, MovingPixmap
from Components.AVSwitch import AVSwitch
from enigma import gFont, eTimer, ePicLoad, loadPNG, getDesktop, eListboxPythonMultiContent, RT_HALIGN_LEFT, RT_HALIGN_RIGHT, RT_HALIGN_CENTER, RT_VALIGN_CENTER
from enigma import eEPGCache
from Screens.Screen import Screen
from Screens.VirtualKeyBoard import VirtualKeyBoard
from Screens.MessageBox import MessageBox
from Tools.Directories import fileExists, SCOPE_PLUGINS
from Tools import Directories
from Tools.LoadPixmap import LoadPixmap
from twisted.web.client import downloadPage, getPage, error
from twisted.internet import defer
import re, shutil, datetime, time
import os
import sys
import socket
from urllib2 import Request, urlopen, URLError
# our custom classes
from SkySkipWordsSelect import SkySkipWordsSelect
from SkyRecorderSettings import SkyRecorderSettings
from SkyTimerRec import SkyTimerRec
from SkySql import *
#from SkyMainFunctions import nonHDeventList, buildSkyChannellist, decodeHtml, getHttpHeader, getHttpHeader2, getUserAgent, getPluginPath, checkForInternet
from SkyMainFunctions import *

# TODO Archiv Screen
from SkyRecorderArchiv import SkyRecorderArchiv

# New Whitelist
from SkyWhitelist import SkyWhitelist

# SkyTheMovieDB
from SkyTheMovieDB import SkyTheMovieDB


class SkyRecorderMainScreen(Screen):

    def __init__(self, session):
        self.session = session

        self.agent = getUserAgent()
        self.headers = getHttpHeader()
        self.headers1 = getHttpHeader1()
        self.headers2 = getHttpHeader2()

        # set current agent to header, too
        self.headers.update({'User-Agent': self.agent})
        self.headers1.update({'User-Agent': self.agent})
        self.headers2.update({'User-Agent': self.agent})

        self.path_to_me = getPluginPath()
        path = "%s/skins/%s/screen_main.xml" % (self.path_to_me, config.plugins.skyrecorder.anytime_skin.value)
        with open(path, "r") as f:
            self.skin = f.read()
            f.close()

        Screen.__init__(self, session)

        self.pluginName = config.plugins.skyrecorder.pluginname.value
        self.contentSize = config.plugins.skyrecorder.contentsize.value

        self.onlyIsNew = True

        self.sky_chlist = buildSkyChannellist()

        self.current_group_idx = 0

        self.haveInternet = True
        if not checkForInternet():
            self.haveInternet = False

        self.popUpIsVisible = False
        self.movieinfoVisible = False
        self.mInfo = SkyTheMovieDB(timeout=10)

        self["mainscreen_actions"]  = ActionMap(["OkCancelActions", "ShortcutActions", "EPGSelectActions", "WizardActions", "ColorActions", "NumberActions", "MenuActions", "MoviePlayerActions"], {
                "ok"    : self.keyOK,
                "cancel": self.keyCancel,
                "up" : self.keyUp,
                "down" : self.keyDown,
                "right" : self.keyRight,
                "left" : self.keyLeft,
                "nextBouquet" : self.keyPageUp,
                "prevBouquet" : self.keyPageDown,
                "red" : self.skipListe,
                "green" : self.openWhitelist,
                "yellow" : self.toggleIsNew,
                "blue"  : self.skyarchive,
                "menu" : self.skysettings,
                "0" : self.toggleEventIgnored,
                "2" : self.addToWhitelist,
                "5" : self.refreshCover,
                "8" : self.deleteEvent,
                "9" : self.nextSort,
                "7" : self.previousSort,
                "nextService" : self.nextGroup,
                "prevService" : self.prevGroup,
                "info" : self.searchMovieInfo,
        }, -1)

        self["popup_actions"] = ActionMap(["OkCancelActions", "ShortcutActions", "EPGSelectActions", "WizardActions", "ColorActions", "NumberActions", "MenuActions", "MoviePlayerActions"],
        {
                "ok": self.setTimerOnOff,
                "cancel": self.keyCancel,
                "up" : self.popUpUp,
                "down" : self.popUpDown,
                "right" : self.ignoreKey,
                "left" : self.ignoreKey,
                "nextBouquet" : self.popUpPageUp,
                "prevBouquet" : self.popUpPageDown
        }, -1)

        self["movieinfo_actions"] = ActionMap(["OkCancelActions", "ShortcutActions", "EPGSelectActions", "WizardActions", "ColorActions", "NumberActions", "MenuActions", "MoviePlayerActions"],
        {
                "ok": self.movieinfoOk,
                "cancel": self.keyCancel,
                "up" : self.movieinfoUp,
                "down" : self.movieinfoDown,
                "right" : self.ignoreKey,
                "left" : self.ignoreKey,
                "red": self.unmatchMovieInfo,
                "green": self.customSearchMovieInfo,
                "nextBouquet" : self.ignoreKey,
                "prevBouquet" : self.ignoreKey
        }, -1)

        self["popup_actions"].setEnabled(False)
        self["movieinfo_actions"].setEnabled(False)


        self['title'] = Label(self.pluginName)

        self['name'] = Label("lade Sky TV-Guide ...")
        self['handlung'] = ScrollLabel("")
        self['image'] = Pixmap()
        self['image'].hide()

        self['hd'] = Pixmap()
        self['hd'].hide()

        self['169'] = Pixmap()
        self['169'].hide()

        self['dolby'] = Pixmap()
        self['dolby'].hide()

        self['dualch'] = Pixmap()
        self['dualch'].hide()

        self['sub'] = Pixmap()
        self['sub'].hide()

        self.ck = {}
        self.keyLocked = True

        self.read_system_timers = True
        self.limit_count = 10
        self.limit_offset = 1
        self.listtype = 0

        try:
            self.default_before = int(config.recording.margin_before.value)
        except Exception:
            self.default_before = 0

        self.red = 0xf23d21
        self.green = 0x389416
        self.blue = 0x0064c7
        self.yellow = 0xbab329
        self.white = 0xffffff

        self.streamMenuList = MenuList([], enableWrapAround=True, content=eListboxPythonMultiContent)
        self.streamMenuList.l.setFont(0, gFont('Regular', 30))
        self.streamMenuList.l.setFont(1, gFont('Regular', 27))
        self.streamMenuList.l.setItemHeight(75) #40
        self['filmliste'] = self.streamMenuList

        self.timerSelectList = MenuList([], enableWrapAround=True, content=eListboxPythonMultiContent)
        self.timerSelectList.l.setFont(0, gFont('Regular', 30))
        self.timerSelectList.l.setItemHeight(75)
        self['filmliste_event'] = self.timerSelectList
        self['filmliste_event'].hide()
        self['filmliste_event_bg'] = Pixmap()
        self['filmliste_event_bg'].hide()

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

        for n in range(0,10):
            star = "star{0}".format(n)
            self[star] = Pixmap()
            self[star].hide()

        self.last_index = 0
        self.retry_count = 0
        self.current_page_number = 1

        self['filmliste'].onSelectionChanged.append(self.loadDetailsAndCover)

        self.tempTimer = eTimer()
        self.tempTimer.callback.append(self.getMainEventList)
        #self.onShown.append(self.delayedGetMainEventList)
        self.onLayoutFinish.append(self.delayedGetMainEventList)

        # check if we are ready to go
        self.show_skydb_warning = True
        self.skydb_warning_shown = False
        if config.plugins.skyrecorder.skydb and config.plugins.skyrecorder.skydb.saved_value:
            skydb_path = config.plugins.skyrecorder.skydb.saved_value
            if not re.match('^/usr/.*', skydb_path, re.I) and not (skydb_path == (self.path_to_me + "/skydb.db")):
                self.show_skydb_warning = False


    def delayedGetMainEventList(self, infotext="lade ..."):
        self['title'].setText(infotext)
        self.tempTimer.start(50, True)


    def getTimerlist(self):

        self.timerList = SkyTimerRec.getTimersList()

        #make sure we are in sync with the system timerlist
        #that's why we reset our record status in the database, before updating
        sql.resetEventListStatusAdded()

        need_commit = None
        for t_record in self.timerList:
            if not t_record['channel']:
                continue
            res = sql.getIdChannel(t_record['channel'],stb=True)
            if not res:
                continue
            id_channel = res
            t_record['id_channel'] = id_channel

            starttime = int(t_record['begin'])
            starttime += (config.plugins.skyrecorder.margin_before.value) * 60 # in eventslist we stored the original starttime
            res = sql.getEventsForTimerlist(t_record['title'], t_record['description'], starttime, id_channel)
            #if not res:
            #       continue
            if not res or len(res) < 1:
                if self.default_before != 0:
                    # second check with system margin_before
                    starttime += (self.default_before * 60)
                    res = sql.getEventsForTimerlist(t_record['title'], t_record['description'], starttime, id_channel)
                    if not res or len(res) < 1:
                        continue

            #with open("/tmp/sql_debug.txt","a") as debug:
            #       debug.write(t_record['title'] + " " + t_record['description'] + " " + str(starttime) + " " + str(id_channel) + "\n" + str(res) + "\n")
            id_events = None
            id_eventslist = None
            for id_events, id_genre, channel, id_eventslist in res:
                t_record['id_genre'] = id_genre
                t_record['channel'] = channel
                break

            if not id_eventslist or not id_events:
                continue
            #if not sql.checkAdded(t_record['title'], t_record['description'], t_record['id_channel'],t_record['id_genre']):
            if not sql.checkAdded(t_record['title'], t_record['description'], t_record['id_channel'],None):
            #if not sql.checkAdded(t_record['title'], t_record['description'], None,None):
                sql.addAdded(
                                        t_record['title'],
                                        t_record['description'],
                                        t_record['id_channel'],
                                        t_record['id_genre'],
                                        t_record['begin'],
                                        t_record['end'],
                                        t_record['serviceref'],
                                        t_record['location'],
                                        t_record['recordedfile'],
                                        t_record['eit'],
                                        int(id_eventslist))
            # if we still have timers in system timerlist, we want to know about it
            sql.updateEventListStatus(id_events,starttime,status="True",commit=False)
            need_commit = True

        # commit database changes
        if need_commit:
            sql.sqlCommit()
            need_commit = None

    def getMainEventList(self):
        # check if need to show the mean-popup again and again and again...
        if self.show_skydb_warning and not self.skydb_warning_shown:
            from Screens.MessageBox import MessageBox
            message = self.session.open(MessageBox, _("Achtung!\nBitte zuerst den Speicherort der skydb.db Datenbank in den Einstellungen (menu) anpassen.\nDer Pfad sollte zu einem Ort auf einer angeschlossenen Festplatte verweisen."), MessageBox.TYPE_INFO, timeout=-1)
            self.skydb_warning_shown = True

        if config.plugins.skyrecorder.mainlisttype and int(config.plugins.skyrecorder.mainlisttype.value) == 0:
            self.listtype = 0
            self.streamMenuList.l.setFont(1, gFont('Regular', 28))
            self.streamMenuList.l.setItemHeight(65)
        else:
            self.listtype = 1
            self.streamMenuList.l.setFont(1, gFont('Regular', 28))
            self.streamMenuList.l.setItemHeight(65)


        # events.id_events, events.title, events.description,
        # events.id_channel, genre.genre, genre.id_genre, events.status,channel.channel,
        # events.image, events.sky_id, eventslist.starttime, eventslist.endtime
        # eventdetails.is_new, anz
        if config.plugins.skyrecorder.max_per_page and config.plugins.skyrecorder.max_per_page.value:
            self.limit_count = config.plugins.skyrecorder.max_per_page.value
        else:
            self.limit_count = 10

        try:
            sql.cur.execute('SELECT SQLITE_VERSION()')
        except Exception:
            sys.exc_clear()
            try:
                sql.connect()
            except Exception:
                return

        self.groupnames = None
        self.groupnames = []
        self.groupnames.append([0,"Alle"])
        rows = sql.readGroupsShort()
        for t_row in rows:
            row = list(t_row)
            self.groupnames.append(row)
        self.current_group = self.groupnames[self.current_group_idx][1]

        if self.read_system_timers:
            self.getTimerlist()
        self.read_system_timers = False

        filmliste = None
        filmliste = []

        self.clearFilmInfoScreen()

        whitelist = sql.readWhitelist(status="True")

        current_timestamp = getCurrentTimestamp()

        if config.plugins.skyrecorder.only_active_genres and config.plugins.skyrecorder.only_active_genres.value:
            only_active_genres = True
        else:
            only_active_genres = False

        if config.plugins.skyrecorder.main_list_order:
            self.sort_type = str(config.plugins.skyrecorder.main_list_order.value)
            self.sort_info = config.plugins.skyrecorder.main_list_order.getText()

        try:
            rows = sql.getEventsMain("ASC", self.onlyIsNew, self.current_group_idx, current_timestamp, only_active_genres,limit_count=self.limit_count,limit_offset=self.limit_offset,sort_type=self.sort_type,check_endtime=True)
        except Exception, e:
            print "[skyrecorder] ERROR: {0}".format(e)
            sys.exc_clear()
            return

        resultCount = 0
        if rows:
            resultCount = len(rows)
        canskip = False

        # uniq sort_idx needed for correct sorting order
        sort_idx = 0
        if resultCount > 0:
            self.retry_count = 0

            need_commit = None
            for t_row in rows:
                row = list(t_row)

                # let us see if we have completed recordings. if so, we update status to "Done"
                # id_added, title, description, id_channel, id_genre, begin, end, serviceref, location, recordedfile
                #addedlist_raw = sql.checkAddedReturnEntry(row[1], row[2], row[3], row[5])
                #addedlist_raw = sql.checkAddedReturnEntry(row[1], row[2], row[3], None)
                addedlist_raw = sql.checkAddedReturnEntry(row[1].lower(), row[2].lower(), row[3], None)
                if addedlist_raw and len(addedlist_raw) != 0:
                    for addedlist_raw_row in addedlist_raw:
                        addedlist = list(addedlist_raw_row)
                        if str(addedlist[9]) == "Hidden":
                            #if sql.updateEventListStatus(row[0],e_starttime,status="Hidden",commit=True):
                            if sql.updateEventListStatus(row[0],None,status="Hidden",commit=False):
                                row[6] = "Hidden"
                                need_commit = True
                            break
                        if int(addedlist[6]) > 0 and int(addedlist[6]) <= current_timestamp:
                            if config.plugins.skyrecorder.margin_before and config.plugins.skyrecorder.margin_before.value:
                                e_starttime = int(addedlist[5]) + config.plugins.skyrecorder.margin_before.value * 60
                            else:
                                e_starttime = int(addedlist[5])
                            if sql.updateEventListStatus(row[0],e_starttime,status="Done",commit=False):
                            #if sql.updateEventListStatus(row[0],0,"Done"):
                                row[6] = "Done"
                                need_commit = True
                            break
                addedlist = None

                # maybe we have some whitelist entries and want to mark them
                if row[6] != "True":
                    for whitelist_event in whitelist:
                        escaped1 = str(whitelist_event[2]).lower().replace("[","\[").replace("]","\]").replace("(","\(").replace(")","\)")
                        escaped2 = str(row[1]).lower().replace("[","\[").replace("]","\]").replace("(","\(").replace(")","\)")
                        if re.match(escaped1 + '.*?', escaped2, re.I):
                            row[6] = "Xallowed"
                            break

                # append sort index
                sort_idx += 1
                row.append(sort_idx)
                filmliste.append(row)

            # commit database changes
            if need_commit:
                sql.sqlCommit()
                need_commit = None

            self.streamMenuList.setList(map(self.skyAnytimeListEntry, filmliste))
        else:
            self.limit_offset = 1
            self.current_page_number = 1
            self.retry_count += 1
            if self.retry_count < 2:
                self.delayedGetMainEventList()
                return
            else:
                self.retry_count = 0

        if self.last_index < resultCount:
            self['filmliste'].moveToIndex(self.last_index)
        elif resultCount > 1:
            self['filmliste'].moveToIndex(resultCount -1)

        try:
            newnew = ""
            if self.onlyIsNew:
                newnew = " (Neu)"

            self['title'].setText("""Seite: {0}{1}, {2}, {3}""".format(self.current_page_number, newnew, self.current_group, self.sort_info))
        except Exception:
            sys.exc_clear()

        self.keyLocked = False


    def skyAnytimeListEntry(self,entry):
        icon = None
        new = None
        if entry[6] == "True":
            icon = "/usr/lib/enigma2/python/Plugins/Extensions/skyrecorder/images/neu_timer.png"
        elif entry[6] == "Done":
            icon = "/usr/lib/enigma2/python/Plugins/Extensions/skyrecorder/images/neu_done.png"
        elif entry[6] == "Hidden":
            icon = "/usr/lib/enigma2/python/Plugins/Extensions/skyrecorder/images/neu_hidden.png"
        elif str(entry[12]) == "1" and entry[6] == "False":
            icon = "/usr/lib/enigma2/python/Plugins/Extensions/skyrecorder/images/neu_is_new.png"
        elif entry[6] == "Xallowed":
            icon = "/usr/lib/enigma2/python/Plugins/Extensions/skyrecorder/images/neu_whitelist.png"
        else:
            icon = "/usr/lib/enigma2/python/Plugins/Extensions/skyrecorder/images/neu_new.png"
        if icon:
            new = LoadPixmap(icon)
        stime = "ab: {0}".format(getDateTimeFromTimestamp2(entry[10]))
        # show episode-name if this row is in group serie
        if self.current_group_idx == 2 and entry[4] == "Serie":
            desc = entry[2]
        else:
            desc = entry[4]

        if self.listtype == 0:
            return [entry,
            (eListboxPythonMultiContent.TYPE_TEXT, 3, 0, 22, 30, 0, RT_HALIGN_RIGHT, str(entry[13])),
            (eListboxPythonMultiContent.TYPE_PIXMAP_ALPHATEST, 30, 8, 28, 17, new),
            (eListboxPythonMultiContent.TYPE_TEXT, 65, 0, 300, 40, 0, RT_HALIGN_LEFT, entry[7]),
            (eListboxPythonMultiContent.TYPE_TEXT, 380, 0, 490, 40, 0, RT_HALIGN_LEFT, entry[1]),
            (eListboxPythonMultiContent.TYPE_TEXT, 910, 0, 270, 40, 0, RT_HALIGN_LEFT, desc)
            ]
        else:
            return [entry,
            (eListboxPythonMultiContent.TYPE_TEXT, 3, 0, 22, 30, 0, RT_HALIGN_RIGHT, str(entry[13])),
            (eListboxPythonMultiContent.TYPE_PIXMAP_ALPHATEST, 30, 4, 28, 17, new),
            (eListboxPythonMultiContent.TYPE_TEXT, 65, 0, 300, 40, 0, RT_HALIGN_LEFT, entry[7]),
            (eListboxPythonMultiContent.TYPE_TEXT, 65, 40, 360, 35, 1, RT_HALIGN_LEFT, stime, self.green),
            (eListboxPythonMultiContent.TYPE_TEXT, 450, 0, 610, 40, 0, RT_HALIGN_LEFT, entry[1]),
            (eListboxPythonMultiContent.TYPE_TEXT, 450, 40, 610, 35, 1, RT_HALIGN_LEFT, entry[2], self.red),
            (eListboxPythonMultiContent.TYPE_TEXT, 900, 0, 270, 40, 0, RT_HALIGN_LEFT, desc)
            ]


    def dataError(self, error):
        self.clearFilmInfoScreen()
        self['name'].setText("Konnte Sky TV-Guide nicht laden.")
        self['handlung'].setText("%s" % error)
        print error

    def clearFilmInfoScreen(self):
        self.streamMenuList.setList([])
        self['name'].setText("Keine neuen Sendungen gefunden")
        self['image'].hide()
        self['hd'].hide()
        self['169'].hide()
        self['dolby'].hide()
        self['dualch'].hide()
        self['sub'].hide()
        self['handlung'].setText("")
        for n in range(0,10):
            star = "star{0}".format(n)
            self[star].hide()


    def loadDetailsAndCover(self):
        try:
            id_events = self['filmliste'].getCurrent()[0][0]
        except Exception:
            return

        for n in range(0,10):
            star = "star{0}".format(n)
            self[star].hide()

        self['image'].hide()
        self['hd'].hide()
        self['169'].hide()
        self['dolby'].hide()
        self['dualch'].hide()
        self['sub'].hide()

        name = self['filmliste'].getCurrent()[0][1]
        if not id_events and name:
            self['handlung'].setText("")
            self['name'].setText(name)
            return

        # get country and year from details
        country = ""
        year = ""
        try:
            rows = sql.getEventCountryYear(id_events)
            if rows:
                for t_row in rows:
                    if t_row[0] and str(t_row[0]) != "NULL":
                        country = str(t_row[0])
                    if t_row[1] and str(t_row[1]) != "NULL":
                        year = str(t_row[1])
                    break
        except Exception:
            sys.exc_clear()

        # maybe we have some info in our themoviedb-table
        #[id_themoviedb], [id_events], [m_id_movie], [m_name], [m_year], [m_title_org],[m_rating],[m_description], [m_genre], [sky_title]
        self.m_id_movie = None
        got_movieinfo = False
        sky_title = self['filmliste'].getCurrent()[0][1]
        rows = sql.getMovieInfo(id_events=None, m_id_movie=None, m_name=None,sky_title=sky_title)
        for t_row in rows:
            got_movieinfo = True
            if float(t_row[6]) > 0:
                max_star = float(t_row[6])
                max_star = int(round(max_star,0))
                for n in range(0,max_star):
                    star = "star{0}".format(n)
                    self[star].show()

            m_name = str(t_row[3]) + " (" + str(t_row[4]) + ")"
            self['name'].setText(m_name)

            m_description = "{0}\n{1} {2}".format(str(t_row[7]),country,year)
            if m_description:
                self['handlung'].setText(m_description)
            else:
                self['handlung'].setText("Keine infos gefunden.")
            # get poster
            m_id_movie = int(t_row[2])
            self.m_id_movie = "tmdb_id:{0}".format(m_id_movie) # need this class-wide for timer tags
            poster = None
            if m_id_movie > 0:
                poster = sql.getMovieInfoPoster(None, m_id_movie,pos=0)
            else:
                poster = sql.getMovieInfoPoster(id_events, None,pos=0)
            if poster:
                cover_file = "/tmp/skyrecorder_tempcover.png"
                with open(cover_file, "wb") as f:
                    f.write(poster)
                try:
                    self.ShowCover(cover_file)
                except Exception:
                    return

        if not got_movieinfo:
            image = self['filmliste'].getCurrent()[0][8]
            sky_id = self['filmliste'].getCurrent()[0][9]

            self['name'].setText(name)

            cover = None
            cover_file = None
            if image and image == "http://www.skygo.sky.de/bin/EPGEvent/web/event_default.png":
                cover_file = "/tmp/skyrecorder_cover_event_default.png"
            else:
                cover_file = "/tmp/skyrecorder_tempcover.png"

            cover = sql.getEventCover(id_events)
            if cover:
                with open(cover_file, "wb") as f:
                    f.write(cover)
                try:
                    self.ShowCover(cover_file)
                except Exception:
                    return
            else:
                try:
                    if self.haveInternet:
                        downloadPage(image, "/tmp/skyrecorder_tempcover.png", headers=self.headers2, agent=self.agent).addCallback(self.downloadImage, "/tmp/skyrecorder_tempcover.png", id_events)
                except Exception, e:
                    self.dataError(e)

        gotData = False
        rows = sql.getEventDetails(id_events)
        if rows:
            # TODO: we got some new fields. What should we do with them?
            for handlung, is_hd, is_169, is_dolby, is_dualch, highlight, live, is_last, is_3d, is_ut, is_new in rows:
                gotData = True
                if not got_movieinfo or not m_description or m_description == "N/A" or len(m_description) < 20:
                    if handlung:
                        handlung = "{0}\n{1} {2}".format(handlung,country,year)
                        self['handlung'].setText(handlung)
                    else:
                        self['handlung'].setText("Keine infos gefunden.")
                if int(is_hd) > 0:
                    self['hd'].show()
                if int(is_169) > 0:
                    self['169'].show()
                if int(is_dolby) > 0:
                    self['dolby'].show()
                if int(is_dualch) > 0:
                    self['dualch'].show()
                if int(is_ut) > 0:
                    self['sub'].show()


    def downloadImage(self, data, imagedata, id_events):
        if id_events:
            #time.sleep(0.123)
            with open(imagedata, "rb") as f:
                cover = f.read()
                res = sql.addEventCover(id_events, cover)
        self.ShowCover(imagedata)

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

    def poster_resize(self, poster_path):
        self["poster"].instance.setPixmap(None)
        self["poster"].hide()
        sc = AVSwitch().getFramebufferScale() # Maybe save during init
        self.picload = ePicLoad()
        size = self["poster"].instance.size()
        self.picload.setPara((size.width(), size.height(), sc[0], sc[1], False, 1, "#00000000")) # Background
        if self.picload.startDecode(poster_path, 0, 0, False) == 0:
            ptr = self.picload.getData()
            if ptr != None:
                self["poster"].instance.setPixmap(ptr)
                self["poster"].show()


    # button actions
    def nextGroup(self):
        self.current_group_idx += 1
        if self.current_group_idx > len(self.groupnames) -1:
            self.current_group_idx = 0
        self.delayedGetMainEventList()

    def prevGroup(self):
        self.current_group_idx -= 1
        if self.current_group_idx < 0:
            self.current_group_idx = len(self.groupnames) -1
        self.delayedGetMainEventList()

    def nextSort(self):
        if not config.plugins.skyrecorder.main_list_order or self.keyLocked:
            return
        config.plugins.skyrecorder.main_list_order.handleKey(1)
        config.plugins.skyrecorder.main_list_order.save()
        self.delayedGetMainEventList()

    def previousSort(self):
        if not config.plugins.skyrecorder.main_list_order or self.keyLocked:
            return
        config.plugins.skyrecorder.main_list_order.handleKey(0)
        config.plugins.skyrecorder.main_list_order.save()
        self.delayedGetMainEventList()

    def toggleEventIgnored(self):
        if self.keyLocked:
            return
        exist = self['filmliste'].getCurrent()
        if exist == None:
            return
        id_events = self['filmliste'].getCurrent()[0][0]
        if not id_events:
            return
        title = self['filmliste'].getCurrent()[0][1]
        desc = self['filmliste'].getCurrent()[0][2]
        id_channel = self['filmliste'].getCurrent()[0][3]
        id_genre = self['filmliste'].getCurrent()[0][5]
        self.last_index = self['filmliste'].getSelectionIndex()

        check_state = sql.getEventListStatus(id_events, None)
        if check_state and check_state == "Hidden":
            sql.updateEventListStatus(id_events, None, status="False",commit=True)

            #sql.removeFromAdded(title,desc,id_channel,None,hidden=True)
            sql.removeFromAdded(title.lower(), desc.lower(),None,None,hidden=True)
            # maybe we should delete this title from our skipword-list instead of disabling?
            if title and len(title) >= 3:
                #sql.delSkip(title)
                sql.setSkipStatus(title, "False")

        elif check_state and check_state != "Hidden":
            if check_state == "True":
                addedlist_raw = None
                #addedlist_raw = sql.checkAddedReturnEntry(title.lower(), desc.lower(), id_channel, id_genre)
                addedlist_raw = sql.checkAddedReturnEntry(title.lower(), desc.lower(), id_channel, None)
                #addedlist_raw = sql.checkAddedReturnEntry(title.lower(), desc.lower(), None, None)
                if addedlist_raw and len(addedlist_raw) != 0:
                    for addedlist_raw_row in addedlist_raw:
                        addedlist = list(addedlist_raw_row)
                        id_added = addedlist[0]

                        entry_dict = None
                        entry_dict = {}
                        entry_dict['name'] = title
                        entry_dict['description'] = desc
                        entry_dict['timer_starttime'] = addedlist[5]
                        entry_dict['channelref'] = addedlist[7]

                        retval = SkyTimerRec.removeTimerEntry(entry_dict)
                        if not retval:
                            return
                        # force Hidden and Delete, if we delete a recording timer
                        if id_added:
                            sql.resetAddedUpdateHidden(id_added,None)
                            res = sql.deleteEventById(id_events)
            sql.updateEventListStatus(id_events, None, status="Hidden",commit=True)

            # append this title to our skipword-list, but mark it as disabled (-)
            if title and len(title) >= 3:
                sql.addSkip(title, "False")

        self.delayedGetMainEventList()


    def deleteEvent(self):
        if self.keyLocked:
            return
        exist = self['filmliste'].getCurrent()
        if exist == None:
            return
        id_events = self['filmliste'].getCurrent()[0][0]
        if not id_events:
            return
        title = self['filmliste'].getCurrent()[0][1]
        desc = self['filmliste'].getCurrent()[0][2]
        id_channel = self['filmliste'].getCurrent()[0][3]
        id_genre = self['filmliste'].getCurrent()[0][5]
        status = self['filmliste'].getCurrent()[0][6]
        self.last_index = self['filmliste'].getSelectionIndex()

        check_state = sql.getEventListStatus(id_events, False)
        if check_state and (status == "Hidden" or status == "Done"):
            res = sql.deleteEventById(id_events)
            #if res and not sql.checkAdded(title.lower(), desc.lower(), id_channel, id_genre):
            if res and not sql.checkAdded(title.lower(), desc.lower(), id_channel, None):
            #if res and not sql.checkAdded(title.lower(), desc.lower(), None, None):
                sql.addAdded(title, desc, id_channel, id_genre, 0, 0, '-', '-', 'Hidden',0,0)
            self.delayedGetMainEventList()


    def refreshCover(self,id_events=None,coverurl=None):
        if self.keyLocked:
            return
        exist = self['filmliste'].getCurrent()
        if exist == None:
            return
        if not id_events:
            id_events = self['filmliste'].getCurrent()[0][0]
            if not id_events:
                return
        self.last_index = self['filmliste'].getSelectionIndex()
        if coverurl:
            # update the cover url for this event in our database
            sql.updateEventCoverUrlByIdEvents(id_events,coverurl)

        sql.deleteEventCoverByIdEvents(id_events)
        self.delayedGetMainEventList("lade Bild neu ...")


    def toggleIsNew(self):
        if self.keyLocked:
            return
        exist = self['filmliste'].getCurrent()
        if exist == None:
            self.last_index = 0
        if self.onlyIsNew == True:
            self.onlyIsNew = False
        else:
            self.onlyIsNew = True
        self.limit_offset = 1
        self.current_page_number = 1
        self.delayedGetMainEventList()


    def addToWhitelist(self):
        if self.keyLocked:
            return
        exist = self['filmliste'].getCurrent()
        if exist == None:
            return
        id_events = self['filmliste'].getCurrent()[0][0]
        if not id_events:
            return
        title = self['filmliste'].getCurrent()[0][1]
        desc = self['filmliste'].getCurrent()[0][2]
        id_channel = self['filmliste'].getCurrent()[0][3]
        self.last_index = self['filmliste'].getSelectionIndex()

        #check_state = sql.addToWhitelist(id_channel,title,desc, status="True")
        check_state = sql.addToWhitelist(id_channel,title,None, status="True")
        self.delayedGetMainEventList()

    def openWhitelist(self):
        if self.keyLocked:
            return
        self.session.openWithCallback(self.delayedGetMainEventList, SkyWhitelist)


    def skipListe(self):
        self.session.openWithCallback(self.delayedGetMainEventList, SkySkipWordsSelect)


    def skysettings(self):
        self.read_system_timers = True
        self.session.openWithCallback(self.delayedGetMainEventList, SkyRecorderSettings)

    def skyarchive(self):
        self.session.openWithCallback(self.timerCallback, SkyRecorderArchiv)

    def keyPageDown(self):
        if self.keyLocked:
            return
        self['handlung'].pageDown()

    def keyPageUp(self):
        if self.keyLocked:
            return
        self['handlung'].pageUp()

    def keyLeft(self):
        if self.keyLocked:
            return
        if self.limit_offset > self.limit_count:
            self.limit_offset -= self.limit_count
            self.current_page_number -= 1
        else:
            self.limit_offset = 1
            self.current_page_number = 1
        self.delayedGetMainEventList()

    def keyRight(self):
        if self.keyLocked:
            return
        self.limit_offset += self.limit_count
        self.current_page_number += 1
        self.delayedGetMainEventList()


    def keyUp(self):
        if self.keyLocked:
            return
        self['filmliste'].up()
        self.last_index = self['filmliste'].getSelectionIndex()

    def keyDown(self):
        if self.keyLocked:
            return
        self['filmliste'].down()
        self.last_index = self['filmliste'].getSelectionIndex()


    def popUpPageDown(self):
        self['filmliste_event'].pageDown()

    def popUpPageUp(self):
        self['filmliste_event'].pageUp()

    def popUpDown(self):
        self['filmliste_event'].down()

    def popUpUp(self):
        self['filmliste_event'].up()

    def movieinfoDown(self):
        self['movieinfo'].down()

    def movieinfoUp(self):
        self['movieinfo'].up()

    def movieinfoOk(self):
        exist = self['filmliste'].getCurrent()
        if exist == None:
            return
        exist = self['movieinfo'].getCurrent()
        if exist == None:
            return
        movieURL = self['movieinfo'].getCurrent()[0][0]
        title = self['movieinfo'].getCurrent()[0][2]
        posterUrl = None
        #posterUrl = self['movieinfo'].getCurrent()[0][5]
        id_events = self['movieinfo'].getCurrent()[0][6]
        title = self['movieinfo'].getCurrent()[0][7]
        self.getMovieInfo(movieURL=movieURL,movieTitle=title,posterUrl=posterUrl,id_events=id_events,sky_title=title)
        self['movieinfo_bg'].hide()
        self['movieinfo'].hide()
        self.movieinfoVisible = False
        self['movieinfo_red_label'].hide()
        self['movieinfo_green_label'].hide()
        self['movieinfo_red'].hide()
        self['movieinfo_green'].hide()
        self["movieinfo_actions"].setEnabled(False)
        self["mainscreen_actions"].setEnabled(True)
        self.timerCallback()

    def keyOK(self):
        if self.keyLocked:
            return

        exist = self['filmliste'].getCurrent()
        if exist == None:
            return
        self.id_events = None
        self.id_events = self['filmliste'].getCurrent()[0][0]
        if not self.id_events:
            return
        self.id_channel = self['filmliste'].getCurrent()[0][3]
        self.id_genre = self['filmliste'].getCurrent()[0][5]
        self.is_new = self['filmliste'].getCurrent()[0][12]
        self.last_index = self['filmliste'].getSelectionIndex()
        check_state = sql.getEventListStatus(self.id_events, False)
        if check_state and check_state == "Hidden":
            return

        self["mainscreen_actions"].setEnabled(False)
        self["popup_actions"].setEnabled(True)
        self['filmliste_event'].show()
        self['filmliste_event_bg'].show()
        self.popUpIsVisible = True
        self.getTimerEventList()


    def timerCallback(self,status=True):
        self.read_system_timers = status
        self.delayedGetMainEventList()

    def ignoreKey(self):
        return

    def keyCancel(self):
        if self.popUpIsVisible:
            self['filmliste_event'].hide()
            self['filmliste_event_bg'].hide()
            self.popUpIsVisible = False
            self["popup_actions"].setEnabled(False)
            self["mainscreen_actions"].setEnabled(True)
        elif self.movieinfoVisible:
            self['movieinfo_bg'].hide()
            self['movieinfo'].hide()
            self['movieinfo_red_label'].hide()
            self['movieinfo_green_label'].hide()
            self['movieinfo_red'].hide()
            self['movieinfo_green'].hide()
            self.movieinfoVisible = False
            self["movieinfo_actions"].setEnabled(False)
            self["mainscreen_actions"].setEnabled(True)
        else:
            self.close()


    def skyAnytimerListEntry(self,entry):
        if entry[5] == "True":
            icon = "/usr/lib/enigma2/python/Plugins/Extensions/skyrecorder/images/neu_timer.png"
        elif entry[5] == "Done":
            icon = "/usr/lib/enigma2/python/Plugins/Extensions/skyrecorder/images/neu_done.png"
        elif entry[5] == "Hidden":
            icon = "/usr/lib/enigma2/python/Plugins/Extensions/skyrecorder/images/neu_hidden.png"
        elif self.is_new == 1:
            icon = "/usr/lib/enigma2/python/Plugins/Extensions/skyrecorder/images/neu_is_new.png"
        else:
            icon = "/usr/lib/enigma2/python/Plugins/Extensions/skyrecorder/images/neu_new.png"
        # FIXME
        stime = getTimeFromTimestamp(entry[2])
        etime = getTimeFromTimestamp(entry[3])

        new = LoadPixmap(icon)
        return [entry,
                (eListboxPythonMultiContent.TYPE_PIXMAP_ALPHATEST, 20, 4, 28, 17, new),
                (eListboxPythonMultiContent.TYPE_TEXT, 70, 0, 280, 40, 0, RT_HALIGN_LEFT, entry[0]),
                (eListboxPythonMultiContent.TYPE_TEXT, 360, 0, 180, 40, 0, RT_HALIGN_LEFT, entry[1]),
                (eListboxPythonMultiContent.TYPE_TEXT, 550, 0, 120, 40, 0, RT_HALIGN_LEFT, stime),
                (eListboxPythonMultiContent.TYPE_TEXT, 690, 0, 120, 40, 0, RT_HALIGN_LEFT, etime),
                (eListboxPythonMultiContent.TYPE_TEXT, 830, 0, 350, 40, 0, RT_HALIGN_LEFT, entry[4])
                ]


    def getTimerEventList(self):
        # eventslist.dayname,eventslist.datum, eventslist.starttime, eventslist.endtime,
        # channel.channel, eventslist.status, events.title, events.description, eventslist.id_eventslist
        try:
            sql.cur.execute('SELECT SQLITE_VERSION()')
        except Exception:
            sys.exc_clear()
            try:
                sql.connect()
            except Exception:
                return

        myList = None
        myList = []
        self.timerSelectList.setList(myList)

        rows = sql.getEventsTimer(self.id_events,"ASC", getCurrentTimestamp(),check_endtime=True)
        resultCount = len(rows)
        if resultCount > 0:
            for t_row in rows:
                row = list(t_row)
                myList.append(row)

            self.timerSelectList.setList(map(self.skyAnytimerListEntry, sorted(myList, key=lambda stime: stime[2])))

    def getChannelref(self, channel):
        for (channelname,channelref) in self.sky_chlist:
            if channelname.lower() == channel.lower():
                return channelref


    def getEPGevent(self,query,channeref,title,starttime):
        if not query or len(query) != 2:
            return
        epgmatches = []
        epgcache = eEPGCache.getInstance()
        #serviceHandler = eServiceCenter.getInstance()
        allevents = epgcache.lookupEvent(query) or []

        for serviceref, eit, name, begin, duration, shortdesc, extdesc in allevents:
            if channeref == serviceref and name.lower() == title.lower() and begin == starttime:
                epgmatches.append( (serviceref, eit, name, begin, duration, shortdesc, extdesc) )
        return epgmatches

    def setTimerOnOff(self):

        datum = self['filmliste_event'].getCurrent()[0][1]
        starttime = self['filmliste_event'].getCurrent()[0][2]
        endtime = self['filmliste_event'].getCurrent()[0][3]
        channel = self['filmliste_event'].getCurrent()[0][4]
        title = self['filmliste_event'].getCurrent()[0][6]
        desc = self['filmliste_event'].getCurrent()[0][7]
        status = self['filmliste_event'].getCurrent()[0][5]
        id_eventslist = self['filmliste_event'].getCurrent()[0][8]
        idx = self['filmliste_event'].getSelectionIndex()

        dirname = None
        recordings_base_folder = None
        try:
            if channel == "Sky 3D":
                if config.plugins.skyrecorder.anytimefolder3d.value:
                    recordings_base_folder = config.plugins.skyrecorder.anytimefolder3d.value
            else:
                if config.plugins.skyrecorder.anytimefolder.value:
                    recordings_base_folder = config.plugins.skyrecorder.anytimefolder.value
        except Exception:
            sys.exc_clear()
            recordings_base_folder = None

        # use settings "margin_before" and "margin_after"
        # for the timers starttime and endtime adjustment
        timer_starttime = starttime - config.plugins.skyrecorder.margin_before.value * 60
        timer_endtime = endtime + config.plugins.skyrecorder.margin_after.value * 60

        stb_channel = sql.getChannelFromChannel(channel,stb=True)
        channelref = self.getChannelref(stb_channel)

        print datum, starttime, endtime, stb_channel, channelref

        # try to delete this recordtimer-entry
        if status == "True":
            entry_dict = None
            entry_dict = {}
            entry_dict['name'] = title
            entry_dict['description'] = desc
            entry_dict['timer_starttime'] = timer_starttime
            entry_dict['channelref'] = channelref

            retval = SkyTimerRec.removeTimerEntry(entry_dict)
            if not retval and self.default_before != 0:
                entry_dict['timer_starttime'] -= (self.default_before * 60)
                retval = SkyTimerRec.removeTimerEntry(entry_dict)
            #id_added = sql.checkAdded(title.lower(), desc.lower(), self.id_channel, self.id_genre)
            id_added = sql.checkAdded(title.lower(), desc.lower(), self.id_channel, None)
            #id_added = sql.checkAdded(title.lower(), desc.lower(), None, None)
            if retval:
                if id_added:
                    sql.resetAdded(id_added,id_eventslist)
                res = sql.updateEventListStatus(self.id_events,starttime,status="False")
                if config.plugins.skyrecorder.silent_timer_mode.value == False:
                    message = self.session.open(MessageBox, _("Timer gelöscht!"), MessageBox.TYPE_INFO, timeout=3)
            self.timerCallback(True)
            self.getTimerEventList()
            self['filmliste_event'].moveToIndex(idx)
            return

        if channelref != None:

            # try to get eventID (eit) from epgCache
            eit = 0
            event_matches = self.getEPGevent(['RITBDSE',(channelref,0, starttime, -1)],channelref,title,starttime)
            if event_matches and len(event_matches) > 0:
                for event_entry in event_matches:
                    eit = int(event_entry[1])
                    break

            justplay = False
            if config.plugins.skyrecorder.timer_mode.value == "1":
                justplay = True

            if recordings_base_folder:
                if not config.plugins.skyrecorder.create_dirtree.value:
                    dirname = recordings_base_folder
                else:
                    # get our groupfoldername
                    a_dir = sql.getGenregroupByGenreId(self.id_genre)
                    if a_dir:
                        group_dir = os.path.join(recordings_base_folder, a_dir + "/")
                        if not os.path.exists(group_dir):
                            try:
                                os.makedirs(group_dir, mode=0777)
                                dirname = group_dir
                            except Exception:
                                sys.exc_clear()
                        else:
                            dirname = group_dir

            if not config.plugins.skyrecorder.short_record_filenames or not config.plugins.skyrecorder.short_record_filenames.value:
                file = getRecordFilename(title,desc,timer_starttime,stb_channel) # "%s - %s - %s.ts" % (begin_date,channel,title)
            else:
                # for short filenames only need the description field for group "serie" or "series" or "tv shows"
                group = sql.getGenregroupByGenreId(self.id_genre)
                if group.lower() == "serie" or group.lower() == "series" or group.lower() == "tv shows":
                    file_base = getRecordFilenameBase(title,desc,timer_starttime,stb_channel)
                else:
                    file_base = getRecordFilenameBase(title,"",timer_starttime,stb_channel)

                file = file_base
                ccn = 2
                while 1:
                    if not os.path.exists(dirname + file + ".ts"):
                        break
                    file = file_base + " (" +  str(ccn) +")"
                    ccn += 1

            # the suffix ".ts" will be added by the system Timerfunction
            recordfile = Directories.getRecordingFilename(file, dirname)
            #recordfile += ".ts"

            # tags?
            tags = []
            if self.m_id_movie:
                tags.append(self.m_id_movie)

            result = SkyTimerRec.addTimer(self.session, channelref, timer_starttime, timer_endtime, title, desc, 0, justplay, 3, dirname, tags, 0, None, eit=eit, recordfile=recordfile)
            if result["result"]:
                sql.updateEventListStatus(self.id_events,starttime,status="True")

                # id_added,title,description,id_channel,id_genre,begin,end,serviceref,location,recordedfile
                #if not sql.checkAdded(title.lower(), desc.lower(), self.id_channel, self.id_genre):
                if not sql.checkAdded(title.lower(), desc.lower(), self.id_channel, None):
                #if not sql.checkAdded(title.lower(), desc.lower(), None, None):
                    sql.addAdded(title, desc, self.id_channel, self.id_genre, timer_starttime, timer_endtime, channelref, dirname, file,result["eit"],id_eventslist)

                self.timerCallback(True)
                self.getTimerEventList()
                self['filmliste_event'].moveToIndex(idx)
            else:
                message = self.session.open(MessageBox, _("Fehler!\n%s") % (result["message"]), MessageBox.TYPE_INFO, timeout=-1)


    def customSearchMovieInfo(self):
        pass
        #exist = self['filmliste'].getCurrent()
        #if exist:
        #       title = self['filmliste'].getCurrent()[0][1]
        #else:
        #       title = ""
        #info_title = "Film suchen"
        #self.session.openWithCallback(self.gotMovieSearchName, VirtualKeyBoard, title = info_title, text = title)


    def gotMovieSearchName(self,title):
        if not title or len(title) < 3:
            return
        self.searchMovieInfo(language="de",title=title)

    def unmatchMovieInfo(self):
        exist = self['filmliste'].getCurrent()
        if exist:
            title = self['filmliste'].getCurrent()[0][1]
            sql.resetMovieInfoActive(id_events=None, m_id_movie=None, m_name="",sky_title=title,id_themoviedb=None)
            self['movieinfo_bg'].hide()
            self['movieinfo'].hide()
            self['movieinfo_red_label'].hide()
            self['movieinfo_green_label'].hide()
            self['movieinfo_red'].hide()
            self['movieinfo_green'].hide()
            self.movieinfoVisible = False
            self["movieinfo_actions"].setEnabled(False)
            self["mainscreen_actions"].setEnabled(True)
            self.timerCallback()
        else:
            return

    def movieinfoListEntry(self,entry):
        return [entry,
                (eListboxPythonMultiContent.TYPE_TEXT, 20, 0, 980, 40, 0, RT_HALIGN_LEFT, entry[2]),
                (eListboxPythonMultiContent.TYPE_TEXT, 1010, 0, 120, 40, 0, RT_HALIGN_LEFT, entry[3])
                ]

    def searchMovieInfo(self,language="de",title=""):
        if self.keyLocked:
            return
        exist = self['filmliste'].getCurrent()
        if not exist:
            return
        if not title or len(title) < 3:
            title = self['filmliste'].getCurrent()[0][1]
        self.id_events = None
        self.id_events = self['filmliste'].getCurrent()[0][0]
        if not self.id_events:
            return

        #self.last_index = self['filmliste'].getSelectionIndex()

        title = self['filmliste'].getCurrent()[0][1]

        # try some fallbacks, if we did not find anything
        try:
            res = self.mInfo.getListFor(searchStr=title,split=False,language=language)
            if not res or len(res) < 1:
                res = self.mInfo.getListFor(searchStr=title.split("-")[0].strip(),split=False,language=language)
                if not res or len(res) < 1:
                    res = self.mInfo.getListFor(searchStr=title.split(":")[0].strip(),split=False,language=language)
                    if not res or len(res) < 1:
                        res = self.mInfo.getListFor(searchStr=title.split("...")[0].strip(),split=False,language=language)
                        if not res or len(res) < 1:
                            # ok, we give up
                            #self.session.open(MessageBox, "Keine Info gefunden für:\n{0}".format(title), MessageBox.TYPE_INFO, timeout=-1)
                            #return
                            res = []
        except Exception:
            sys.exc_clear()
            res = []
        # for now, we do not want single matches.
        # This is why we show our resultlist even we have just one match

        #self.getMovieInfo(movieURL=res[0]["m_movie_url"],movieTitle=title)
        #if len(res) == 1:
        #       self.getMovieInfo(movieURL=res[0]["m_movie_url"],movieTitle=title)
        #else:
        #       self["mainscreen_actions"].setEnabled(False)
        #       self["movieinfo_actions"].setEnabled(True)
        #       self['movieinfo'].show()
        #       self['movieinfo_bg'].show()
        #       self.movieinfoVisible = True
        #       self.getMovieSearchList(searchlist=res)

        self["mainscreen_actions"].setEnabled(False)
        self["movieinfo_actions"].setEnabled(True)
        self['movieinfo'].show()
        self['movieinfo_bg'].show()
        self['movieinfo_red_label'].show()
        #self['movieinfo_green_label'].show()
        self['movieinfo_red'].show()
        #self['movieinfo_green'].show()
        self.movieinfoVisible = True
        self.getMovieSearchList(searchlist=res,id_events=self.id_events,sky_title=title)
        return


    def getMovieSearchList(self,searchlist=None,id_events=0,sky_title=""):
        #if not searchlist or len(searchlist) < 1:
        #       return
        myList = None
        myList = []
        self.movieinfoSelectList.setList(myList)
        for t_row in searchlist:
            myList.append([t_row["m_movie_url"],t_row["m_title_org"],t_row["m_title"],t_row["m_date"],t_row["m_id_movie"],t_row["m_poster_url"],id_events,sky_title])
        self.movieinfoSelectList.setList(map(self.movieinfoListEntry, myList))


    def getMovieInfo(self,movieURL=None,movieTitle="",posterUrl="",id_events=0,sky_title=""):
        if not movieURL:
            return
        movieinfo = None
        movieinfo = self.mInfo.getInfoFor(movieURL=movieURL,movieTitle=movieTitle,idMovie="",language="de",lastlang=-1)
        if not movieinfo or len(movieinfo) < 1:
            # fallback language english
            movieinfo = self.mInfo.getInfoFor(movieURL=movieURL,movieTitle=movieTitle,idMovie="",language="en",lastlang=-1)
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
        res = sql.addNewMovieInfo(id_events, m_id_movie, m_name, m_year, m_title_org, m_rating, m_description, m_genre,sky_title)

        if not res:
            return

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
                req = Request(coverurl,None,self.headers2)
                response = urlopen(req)
                data = response.read()
                self.gotPoster(data,id_events, m_id_movie, coverurl)

    def gotPoster(self, data, id_events, m_id_movie, coverurl):
        if data:
            time.sleep(0.123)
            sql.addMovieInfoPoster(id_events, m_id_movie, coverurl, data)

    def dataErrorPage(self, error):
        self.clearFilmInfoScreen()
        self['name'].setText("Fehler beim Laden.")
        self['handlung'].setText("%s" % error)
        print error
