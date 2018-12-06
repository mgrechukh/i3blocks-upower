#!/usr/bin/env python
# vim:fileencoding=utf-8:ts=4:sw=4:sta:et:sts=4:fdm=marker:ai:ft=python

try:
    from gi.repository import GObject
except ImportError:
    import gobject as GObject

import sys, os
import json
import dbus
import dbus.mainloop.glib
import subprocess

UPOWER_NAME = "org.freedesktop.UPower"
UPOWER_PATH = "/org/freedesktop/UPower"
DBUS_PROPERTIES = "org.freedesktop.DBus.Properties"

def get_display_device(bus):
    upower_proxy = bus.get_object(UPOWER_NAME, UPOWER_PATH) 
    upower_interface = dbus.Interface(upower_proxy, UPOWER_NAME)
    dispdev = upower_interface.GetDisplayDevice()
    return dispdev

def dbus_to_python(data):
    '''
        convert dbus data types to python native data types
    '''
    if isinstance(data, dbus.String):
        data = str(data)
    elif isinstance(data, dbus.Boolean):
        data = bool(data)
    elif isinstance(data, (dbus.UInt64, dbus.Int64, dbus.UInt32, dbus.Int32)):
        data = int(data)
    elif isinstance(data, dbus.Double):
        data = float(data)
    elif isinstance(data, dbus.Array):
        data = [dbus_to_python(value) for value in data]
    elif isinstance(data, dbus.Dictionary):
        new_data = dict()
        for key, val in data.iteritems():
            key = dbus_to_python(key)
            val = dbus_to_python(val)
            new_data[key] = val
        data = new_data
    return data

def properties_changed(interface, changed, invalidated):
    if not interface == "org.freedesktop.UPower.Device":
        return
    changed = dbus_to_python(changed)
    for p in props_list:
        if p in changed:
            battery_info[p] = changed[p]
    # signal received before props reported
    if len(battery_info) == len(props_list):
        output_info()

def format_time(s):
    return "%02d:%02d" % ( s // 3600, s % 3600 / 60)

# stands for charging
FA_LIGHTNING = u"<span color='yellow'><span font='FontAwesome'>\uf0e7</span></span>".encode('utf-8')

# stands for plugged in
FA_PLUG = u"<span font='FontAwesome'>\uf1e6</span>".encode('utf-8')

# stands for using battery
FA_BATTERY = u"<span font='FontAwesome'>%s</span>".encode('utf-8')

    # stands for unknown status of battery
FA_QUESTION = u"<span font='FontAwesome'>\uf128</span>".encode('utf-8')

def output_info():
    print >>sys.stderr, battery_info
    global awaiting_message

    percentage = float(battery_info['Percentage'])

    color = None
    if percentage < 20:
        battery_icon = u'\uf244'
        color = "#FF0000"
    elif percentage < 40:
        battery_icon = u'\uf243'
        color = "#FFAE00"
    elif percentage < 60:
        battery_icon = u'\uf242'
        color = "#FFF600"
    elif percentage < 80:
        battery_icon = u'\uf241'
        color = "#A8FF00"
    else:
        battery_icon = u'\uf240'

    if color:
        full_text = '<span color="%s">%.1f%%</span>' % (color, percentage)
    else:
        full_text = '%.1f%%' % percentage

    if battery_info['State'] == 1:
        # charging 
        full_text += " " + FA_LIGHTNING + " " + format_time(battery_info['TimeToFull'])
    elif battery_info['State'] == 2:
        # discharging
        full_text += " " + FA_BATTERY % battery_icon.encode('utf-8') + " " + format_time(battery_info['TimeToEmpty'])
    elif battery_info['State'] == 4:
        full_text += " " + FA_PLUG
    else:
        full_text += " " + FA_QUESTION
        time_left = 0

    if  battery_info['State'] in (1,4) and awaiting_message:
        full_text += " - killed %s" % awaiting_message
        try:
            awaiting_message.kill()
            awaiting_message.wait()
        except Exception:
            pass
        awaiting_messsage = None
        full_text += " - %s" % awaiting_message

    if percentage < 20 and battery_info['State'] == 2:
        if not awaiting_message:
            #full_text += " - starting yad"
            awaiting_message = subprocess.Popen("exec yad --image gnome-shutdown --button=gtk-ok:0 --splash --timeout 30 --timeout-indicator=right", shell = True)
        elif not awaiting_message.poll() == None:
            #full_text += " - sleeping"
            awaiting_message = None
            os.system("acpi -b | grep -q Discharging && sudo systemctl suspend")
        else:
            #full_text += " - waiting yad"
            pass

    print full_text
    sys.stdout.flush()
    print full_text
    sys.stdout.flush()
    print
    sys.stdout.flush()

    sys.stdout.flush()

props_list = ['State', 'Percentage', 'TimeToEmpty', 'TimeToFull']
battery_info = {}
awaiting_message = None

dbus.mainloop.glib.DBusGMainLoop(set_as_default=True)
bus = dbus.SystemBus()

display_device = get_display_device(bus)

bus.add_signal_receiver(properties_changed,
        dbus_interface = DBUS_PROPERTIES,
        signal_name = "PropertiesChanged",
        arg0 = "org.freedesktop.UPower.Device",
        path = display_device)

dev = bus.get_object(UPOWER_NAME, display_device)
iface = dbus.Interface(dev, DBUS_PROPERTIES)
props = dbus_to_python(iface.GetAll("org.freedesktop.UPower.Device"))

for p in props_list:
    if p in props and not p in battery_info:
        battery_info[p] = props[p]

output_info()

mainloop = GObject.MainLoop()
mainloop.run()
