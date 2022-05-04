# coding=utf-8
from __future__ import absolute_import

import copy
import sys, traceback
import time
import octoprint.plugin

from octoprint.events import eventManager, Events

class PreheathelperPlugin(  octoprint.plugin.SettingsPlugin,
                            octoprint.plugin.AssetPlugin,
                            octoprint.plugin.TemplatePlugin,
                            octoprint.plugin.EventHandlerPlugin ):

    def preprocess_loaded_file(self, full_filename):
        self._logger.info(f"Preprocessing file: {full_filename}")

    ##~~ EventHandlerPlugin mixin

    def on_event(self, event, payload):
		if event == Events.FILE_SELECTED:
            if self._settings.get(["preheat_on_file_load"]) and payload["origin"] == "local":
                #   Payload:
                #       name: the file’s name
                #       path: the file’s path within its storage location
                #       origin: the origin storage location of the file, either local or sdcard
                self.preprocess_loaded_file(payload["path"])

    ##~~ SettingsPlugin mixin

    def get_settings_defaults(self):
        return {
            # put your plugin's default settings here
        }

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
