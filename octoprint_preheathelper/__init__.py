# coding=utf-8
from __future__ import absolute_import

import copy
import sys, traceback
import re, math
import time
import octoprint.plugin

from octoprint.events import eventManager, Events

class PreheathelperPlugin(  octoprint.plugin.SettingsPlugin,
                            octoprint.plugin.AssetPlugin,
                            octoprint.plugin.TemplatePlugin,
                            octoprint.plugin.EventHandlerPlugin ):

    def parse_heater_command(self, command):
        try:
            temperature = float(re.search(r"[RS]([0-9]+)", line).group(1))
        except:
            temperature = None
        return temperature

    def do_preheat(self, nozzle, bed, chamber):
        if nozzle:
            self._printer.commands("M104 S"+ nozzle)
        if bed:
            self._printer.commands("M140 S"+ bed)
        if chamber:
            self._printer.commands("M141 S"+ chamber)

    def preprocess_loaded_file(self, full_filename):
        """
            Find first occurence of Nozzle, Bed, and Chamber temperature setpoint

            ToDo: Larger than (t0)

        """
        self._logger.info(f"Preprocessing file: {full_filename}")
        
        nozzle_setpoint = self._settings.get(["nozzle_setpoint_default"])
        bed_setpoint = self._settings.get(["bed_setpoint_default"])
        chamber_setpoint = self._settings.get(["chamber_setpoint_default"])

        search_nozzle = self._settings.get(["find_nozzle_setpoint"])
        search_bed = self._settings.get(["find_bed_setpoint"])
        search_chamber = self._settings.get(["find_chamber_setpoint"])

        max_search_lines = self._settings.get(["max_search_lines"])

        with open(full_filename) as f:
            for index, line in enumerate(f):
                if line.startswith('M'):
                    # Set hotend (and wait)
                    if (line.startswith('M104') or line.startswith('M109')) and search_nozzle:
                        self._logger.info(f"  Nozzle temp: {line}")
                        _setpoint = self.parse_heater_command(line)
                        if _setpoint:
                            nozzle_setpoint = _setpoint
                            search_nozzle = False
                    # Set bed (and wait)
                    elif (line.startswith('M140') or line.startswith('M190')) and search_bed:
                        self._logger.info(f"  Bed temp: {line}")
                        _setpoint = self.parse_heater_command(line)
                        if _setpoint:
                            bed_setpoint = _setpoint
                            search_bed = False
                    # Set bed (and wait)
                    elif (line.startswith('M141') or line.startswith('M191')) and search_chamber:
                        self._logger.info(f"  Chamber temp: {line}")
                        _setpoint = self.parse_heater_command(line)
                        if _setpoint:
                            chamber_setpoint = _setpoint
                            search_chamber = False
                if max_search_lines and index > max_search_lines:
                    break

        return nozzle_setpoint, bed_setpoint, chamber_setpoint


    ##~~ EventHandlerPlugin mixin

    def on_event(self, event, payload):
		if event == Events.FILE_SELECTED:
            if self._settings.get(["preheat_on_file_load"]) and payload["origin"] == "local":
                #   Payload:
                #       name: the file’s name
                #       path: the file’s path within its storage location
                #       origin: the origin storage location of the file, either local or sdcard
                nozzle, bed, chamber = self.preprocess_loaded_file(payload["path"])
                self.do_preheat(nozzle, bed, chamber)

    ##~~ SettingsPlugin mixin

    def get_settings_defaults(self):
        return dict(
            nozzle_setpoint_default=215,
            bed_setpoint_default=60,
            chamber_setpoint_default=None,

            search_nozzle=True,
            search_bed=True,
            search_chamber=False,
            max_search_lines=2500,

            preheat_on_file_load=True
        )

    def on_settings_initialized(self):
        self._logger.debug("on_settings_initialized()")

        
    def on_settings_save(self, data):
        self._logger.debug(f"PreHeatHelper settings saved: {data}")

    ##~~ AssetPlugin mixin

    def get_assets(self):
        # Define your plugin's asset files to automatically include in the
        # core UI here.
        return {
            "js": ["js/preheathelper.js"]
        }

    ##~~ Softwareupdate hook

    def get_update_information(self):
        # Define the configuration for your plugin to use with the Software Update
        # Plugin here. See https://docs.octoprint.org/en/master/bundledplugins/softwareupdate.html
        # for details.
        return {
            "preheathelper": {
                "displayName": "Preheathelper Plugin",
                "displayVersion": self._plugin_version,

                # version check: github repository
                "type": "github_release",
                "user": "RoboMagus",
                "repo": "OctoPrint-PreheatHelper",
                "current": self._plugin_version,

                # update method: pip
                "pip": "https://github.com/RoboMagus/OctoPrint-PreheatHelper/archive/{target_version}.zip",
            }
        }

    ##~~ Plugin Helper functions

    def dummy_func(self):
        return None



__plugin_name__ = "PreHeat Helper"
__plugin_pythoncompat__ = ">=3,<4"  # Only Python 3

def __plugin_load__():
    plugin = PreheathelperPlugin()

    global __plugin_helpers__
    __plugin_helpers__ = dict(
        dummy_func = plugin.dummy_func
    )

    global __plugin_implementation__
    __plugin_implementation__ = plugin

    global __plugin_hooks__
    __plugin_hooks__ = {
        "octoprint.plugin.softwareupdate.check_config": __plugin_implementation__.get_update_information
    }
