#!/usr/bin/python
# -*- coding: utf-8 -*-

import os
import sys
import time
import xbmc
import xbmcgui
import xbmcaddon

import subprocess
import json
import urllib2
import socket
import codecs
#import pyxbmct
import pyxbmct.addonwindow as pyxbmct

from datetime import datetime
import _strptime
from contextlib import closing


__addon__ = xbmcaddon.Addon()
__setting__ = __addon__.getSetting
__addon_id__ = __addon__.getAddonInfo('id')
__addon_path__ = __addon__.getAddonInfo('path')
__check_icon__ = os.path.join(__addon_path__, 'check.png') # Don't decode _path to utf-8!!!
__checked_icon__ = os.path.join(__addon_path__, 'checked.png') # Don't decode _path to utf-8!!!
__unchecked_icon__ = os.path.join(__addon_path__, 'unchecked.png') # Don't decode _path to utf-8!!!
__localize__ = __addon__.getLocalizedString


# Enable or disable Estuary-based design explicitly
pyxbmct.skin.estuary = True


def convert_date(t_str, t_fmt_in, t_fmt_out):
    ##Legacy check, Python 2.4 does not have strptime attribute, introduced in 2.5
    #if hasattr(datetime, 'strptime'):
    #    strptime = datetime.strptime
    #else:
    #    strptime = lambda date_string, format: datetime(*(time.strptime(date_string, format)[0:6]))

    try:
        t = datetime.strptime(t_str, t_fmt_in)
    except TypeError:
        t = datetime(*(time.strptime(t_str, t_fmt_in)[0:6]))

    return t.strftime(t_fmt_out)


class MultiChoiceDialog(pyxbmct.AddonDialogWindow):
    def __init__(self, title="", items=None, selected=None):
        super(MultiChoiceDialog, self).__init__(title)
        self.setGeometry(1000, 350, 6, 10)
        self.selected = selected or []
        self.set_controls()
        self.listing.addItems(items or [])
        if (self.listing.size() > 0):
            for index in xrange(self.listing.size()):
                if index in self.selected:
                    self.listing.getListItem(index).setIconImage(__checked_icon__)
                    self.listing.getListItem(index).setLabel2("checked")
                else:
                    self.listing.getListItem(index).setIconImage(__unchecked_icon__)
                    self.listing.getListItem(index).setLabel2("unchecked")
        else:
            self.listing.addItems([__localize__(30053)])
        self.place_controls()
        self.connect_controls()
        self.set_navigation()

    def set_controls(self):
        self.listing = pyxbmct.List(_imageWidth=15)
        self.placeControl(self.listing, 0, 0, rowspan=5, columnspan=10)
        self.ok_button = pyxbmct.Button(__localize__(30051))
        self.cancel_button = pyxbmct.Button(__localize__(30052))

    def connect_controls(self):
        self.connect(self.listing, self.check_uncheck)
        self.connect(self.ok_button, self.ok)
        self.connect(self.cancel_button, self.close)
        self.connect(pyxbmct.ACTION_NAV_BACK, self.close)

    def place_controls(self):
        if (self.listing.getListItem(0).getLabel2()):
            self.placeControl(self.ok_button, 5, 3, columnspan=2)
            self.placeControl(self.cancel_button, 5, 5, columnspan=2)
        else:
            self.placeControl(self.cancel_button, 5, 4, columnspan=2)

    def set_navigation(self):
        if (self.listing.getListItem(0).getLabel2()):
            self.listing.controlUp(self.ok_button)
            self.listing.controlDown(self.ok_button)
            self.ok_button.setNavigation(self.listing, self.listing, self.cancel_button, self.cancel_button)
            self.cancel_button.setNavigation(self.listing, self.listing, self.ok_button, self.ok_button)
            self.setFocus(self.listing)
        else:
            self.setFocus(self.cancel_button)

    def check_uncheck(self):
        list_item = self.listing.getSelectedItem()
        if list_item.getLabel2() == "checked":
            list_item.setIconImage(__unchecked_icon__)
            list_item.setLabel2("unchecked")
        else:
            list_item.setIconImage(__checked_icon__)
            list_item.setLabel2("checked")

    def ok(self):
        self.selected = [index for index in xrange(self.listing.size())
                                if self.listing.getListItem(index).getLabel2() == "checked"]
        super(MultiChoiceDialog, self).close()

    def close(self):
        self.selected = None
        super(MultiChoiceDialog, self).close()


def mixed_decoder(unicode_error):

    err_str = unicode_error[1]
    err_len = unicode_error.end - unicode_error.start
    next_position = unicode_error.start + err_len
    replacement = err_str[unicode_error.start:unicode_error.end].decode('cp1252')

    return u'%s' % replacement, next_position

codecs.register_error('mixed', mixed_decoder)

def json_request(method, params, host, port=8080, username=None, password=None):

    url    =    'http://{}:{}/jsonrpc'.format(host, port)
    header =    {'Content-Type': 'application/json'}

    jsondata = {
        'jsonrpc': '2.0',
        'method': method,
        'id': method}

    if params:
        jsondata['params'] = params

    if username and password:
        base64str = base64.encodestring('{}:{}'.format(username, password))[:-1]
        header['Authorization'] = 'Basic {}'.format(base64str)

    try:
        request = urllib2.Request(url, json.dumps(jsondata), header)
        with closing(urllib2.urlopen(request)) as response:
            data = json.loads(response.read().decode('utf8', 'mixed'))

            if data['id'] == method and data.has_key('result'):
                return data['result']

    except:
        pass

    return False


def find_hosts(port=34890):

    hosts = []

    my_env = os.environ.copy()
    my_env['LC_ALL'] = 'en_EN'
    netstat = subprocess.check_output(['netstat', '-t', '-n'], universal_newlines=True, env=my_env)

    for line in netstat.split('\n')[2:]:
        items = line.split()
        if len(items) < 6 or (items[5] != 'ESTABLISHED'):
            continue

        local_addr, local_port = items[3].rsplit(':', 1)
        remote_addr, remote_port = items[4].rsplit(':', 1)

        if local_addr[0] == '[' and local_addr[-1] == ']':
            local_addr = local_addr[1:-1]

        if remote_addr[0] == '[' and remote_addr[-1] == ']':
            remote_addr = remote_addr[1:-1]

        local_port = int(local_port)

        if local_port == port:
            if remote_addr not in hosts:
                hosts.append(remote_addr)

    return hosts


if __name__ == '__main__':

    items = []
    hosts = []

    for host in find_hosts():

        try:
            hostname = socket.gethostbyaddr(host)[0].split('.')[0]

        except:
            hostname = host

        player = json_request('Player.GetActivePlayers', None, host)
        if player and player[0]['type'] in ['audio', 'video']:
            player_id = player[0]['playerid']
            data = json_request('Player.GetItem',{'properties': ['title', 'file', 'showtitle', 'album', 'artist', 'track'], 'playerid': player_id}, host)
            if data:
                try:
                    if data['item']['type'] == 'channel':
                        item = '{} (IP: {}): \"{}\" ({}: {})'.format(hostname, host, data['item']['title'].encode('utf-8'), ['Radio', 'TV'][player_id], data['item']['label'])
                    elif data['item'].has_key('file') and urllib2.unquote(data['item']['file'].encode('utf-8'))[:6] == 'pvr://':
                        item = '{} (IP: {}): \"{}\" ({})'.format(hostname, host, data['item']['title'].encode('utf-8'), __localize__(30054))
                    elif data['item']['type'] == 'song' and data['item'].has_key('artist') and data['item'].has_key('album') and data['item'].has_key('track'):
                        item = '{} (IP: {}): \"{}: {} - {:02d}: {}\" ({})'.format(hostname, host, data['item']['artist'][0].encode('utf-8') , data['item']['album'].encode('utf-8'), data['item']['track'], data['item']['label'].encode('utf-8'), data['item']['type'])
                    elif data['item']['type'] == 'musicvideo' and data['item'].has_key('artist'):
                        item = '{} (IP: {}): \"{}: {}\" ({})'.format(hostname, host, data['item']['artist'][0].encode('utf-8'), data['item']['label'].encode('utf-8'), data['item']['type'])
                    elif data['item']['type'] == 'episode' and data['item'].has_key('showtitle'):
                        item = '{} (IP: {}): \"{} - {}\" ({})'.format(hostname, host, data['item']['showtitle'].encode('utf-8'), data['item']['label'].encode('utf-8'), data['item']['type'])
                    else:
                        item = '{} (IP: {}): \"{}\" ({})'.format(hostname, host, data['item']['label'].encode('utf-8'), data['item']['type'])

                except:
                    item = '{} (IP: {}): \"{}\" ({})'.format(hostname, host, data['item']['label'].encode('utf-8'), data['item']['type'])

                tdata = json_request('Player.GetProperties',{'properties': ['time', 'totaltime'], 'playerid': player_id}, host)
                if tdata:
                    item = '{} @ {:02d}:{:02d}:{:02d} / {:02d}:{:02d}:{:02d}'.format(item, tdata['time']['hours'], tdata['time']['minutes'], tdata['time']['seconds'], \
                                                           tdata['totaltime']['hours'], tdata['totaltime']['minutes'], tdata['totaltime']['seconds'])

                hosts.append(host)
                items.append(item)

    dialog = MultiChoiceDialog(__localize__(30050), items)
    dialog.doModal()

    if dialog.selected is not None:
        for index in dialog.selected:
            try:
                player = json_request('Player.GetActivePlayers', None, hosts[index])
                if player and player[0]['type'] in ['audio', 'video']:
                    player_id = player[0]['playerid']
                    json_request('Player.Stop', {'playerid': player_id}, hosts[index])
                    json_request('GUI.ShowNotification', {'title': __addon_id__, 'message': __localize__(30055)}, hosts[index])

            except:
                continue

    del dialog
