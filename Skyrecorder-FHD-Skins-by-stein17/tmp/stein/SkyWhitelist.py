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
import re, shutil
import os
import sys

# our custom classes
from SkyMainFunctions import getPluginPath
from SkySql import *

class SkyWhitelist(Screen):

    def __init__(self, session):
        self.session = session
        self.last_index = -1

        path = "%s/skins/%s/screen_whitelist.xml" % (getPluginPath(), config.plugins.skyrecorder.anytime_skin.value)
        with open(path, "r") as f:
            self.skin = f.read()
            f.close()

        Screen.__init__(self, session)

        pluginName = config.plugins.skyrecorder.pluginname.value
        contentSize = config.plugins.skyrecorder.contentsize.value

        self["actions"]  = ActionMap(["OkCancelActions", "ShortcutActions", "EPGSelectActions", "WizardActions", "ColorActions", "NumberActions", "MenuActions", "MoviePlayerActions"], {
                "ok"    : self.keyOK,
                "cancel": self.keyCancel,
                "green" : self.keyEdit,
                "yellow" : self.keyAdd,
                "red" : self.keyDel,
        }, -1)

        self.whitelistliste = []
        self.streamMenuList = MenuList([], enableWrapAround=True, content=eListboxPythonMultiContent)
        self.streamMenuList.l.setFont(0, gFont('Regular', 28))
        self.streamMenuList.l.setItemHeight(75)
        self['whitelist'] = self.streamMenuList

        self.onLayoutFinish.append(self.readWhitelist)


    def skyWhitelistListEntry(self,entry):
        if entry[4] == "True":
            pic = "/usr/lib/enigma2/python/Plugins/Extensions/skyrecorder/images/plus.png"
        else:
            pic = "/usr/lib/enigma2/python/Plugins/Extensions/skyrecorder/images/minus.png"

        icon = LoadPixmap(pic)
        return [entry,
                        (eListboxPythonMultiContent.TYPE_PIXMAP_ALPHATEST, 15, 5, 20, 18, icon),
                        (eListboxPythonMultiContent.TYPE_TEXT, 50, 0, 850, 25, 0, RT_HALIGN_LEFT, str(entry[2]))
                        ]


    def readWhitelist(self):
        try:
            sql.cur.execute('SELECT SQLITE_VERSION()')
        except Exception:
            sys.exc_clear()
            try:
                sql.connect()
            except Exception:
                return

        self.whitelistliste = []
        for (id_whitelist,id_channel,title,description,status) in sql.readWhitelist():
            self.whitelistliste.append((id_whitelist,id_channel,title,description,status))
        #self.whitelistliste.sort()
        self.whitelistliste = sorted(self.whitelistliste, key=lambda x: x[2], reverse=False)
        self.streamMenuList.setList(map(self.skyWhitelistListEntry, self.whitelistliste))
        if self.last_index < len(self.whitelistliste):
            self['whitelist'].moveToIndex(self.last_index)


    def keyOK(self):
        exist = self['whitelist'].getCurrent()
        if exist == None:
            return
        id_whitelist = self['whitelist'].getCurrent()[0][0]
        self.last_index = self['whitelist'].getSelectionIndex()
        sql.changeWhitelistStatus(id_whitelist)
        self.readWhitelist()


    def keyEdit(self):
        exist = self['whitelist'].getCurrent()
        if exist == None:
            return
        self.id_whitelist = self['whitelist'].getCurrent()[0][0]
        self.last_index = self['whitelist'].getSelectionIndex()
        word = self['whitelist'].getCurrent()[0][2]
        self.session.openWithCallback(self.editWord, VirtualKeyBoard, title = ("Titel bearbeiten:"),text = word)

    def keyAdd(self):
        exist = self['whitelist'].getCurrent()
        if exist:
            self.last_index = self['whitelist'].getSelectionIndex()
        self.session.openWithCallback(self.addWord, VirtualKeyBoard, title = ("Neuer Eintrag:"),text = "")

    def addWord(self, word = None):
        if word != None or word != "":
            check_state = sql.addToWhitelist(None,word,None, status="True")
        self.readWhitelist()

    def editWord(self, word = None):
        if word != None or word != "":
            sql.updateWhitelistEntry(self.id_whitelist,word)
        self.readWhitelist()

    def keyDel(self):
        exist = self['whitelist'].getCurrent()
        if exist == None:
            return
        id_whitelist = self['whitelist'].getCurrent()[0][0]
        self.last_index = self['whitelist'].getSelectionIndex()
        sql.delFromWhitelistById(id_whitelist)
        self.readWhitelist()


    def keyCancel(self):
        self.close()
