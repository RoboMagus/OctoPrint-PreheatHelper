# coding=utf-8
from __future__ import absolute_import

import copy
import sys, traceback
import re, math
import time
import octoprint.plugin

from octoprint.events import eventManager, Events

MINIMAL_SETPOINT_TEMPERATURE = 20

# Goals:
# - Multiplse auto-preheat options
#   - On octoprint startup (just default setpoints, or last received setpoints)
#   - On printer connected (just default setpoints, or last received setpoints)
#   - On print loaded (Scanned initial setpoints, or last received setpoints if they are higher)
#     --> Provide warning message if setpoints previously were higher?..


class PreheathelperPlugin(  octoprint.plugin.SettingsPlugin,
                            octoprint.plugin.StartupPlugin,
                            octoprint.plugin.ShutdownPlugin,
                            octoprint.plugin.TemplatePlugin,
                            octoprint.plugin.EventHandlerPlugin ):

    def __init__(self):
        self._last_bed_temp_setpoint = None
        self._last_tool_temp_setpoint = None

    def parse_heater_command(self, command):
        try:
            temperature = float(re.search(r"M.*[RS]([0-9]+).*", command).group(1))
        except:
            temperature = None
        return temperature

    def is_bed_ready(self):     
        try:   
            self._logger.debug("Checking if 'Bed Ready'...")
            helpers = self._plugin_manager.get_helpers("bedready")
            if helpers and "check_bed" in helpers:
                bed_ready = helpers["check_bed"]()
                self._logger.debug(f"Bed Ready: {bed_ready['bed_clear']} ({bed_ready})")
                return bed_ready['bed_clear']
            else:
                self._logger.warning("could not check 'Bed Ready'!")
        except Exception as e:
            self._logger.error("TraceBack: {}".format(''.join(x for x in traceback.format_exception(*sys.exc_info()))))
        return False

    def do_preheat(self, nozzle, bed, chamber):
        if self._settings.getBoolean(["check_bedready_before_preheat"]) and not self.is_bed_ready():
            self._logger.info(f"NOT Pre-heating, as bed is not ready!")
        else:
            nozzle_str = f"Nozzle: {nozzle} " if nozzle else ''
            bed_str = f"Bed: {bed} " if bed else ''
            chamber_str = f"Chamber: {chamber} " if chamber else ''
            self._logger.info(f"Pre-heating {nozzle_str}{bed_str}{chamber_str}")

            if nozzle:
                self._printer.commands(f"M104 S{int(nozzle)}")
            if bed:
                self._printer.commands(f"M140 S{int(bed)}")
            if chamber:
                self._printer.commands(f"M141 S{int(chamber)}")

    def preprocess_loaded_file(self, full_filename):
        """
            Find first occurence of Nozzle, Bed, and Chamber temperature setpoint
        """       
        try:  
            nozzle_setpoint = self._settings.get(["nozzle_setpoint_default"])
            bed_setpoint = self._settings.get(["bed_setpoint_default"])
            chamber_setpoint = self._settings.get(["chamber_setpoint_default"])

            search_nozzle = self._settings.get(["search_nozzle"])
            search_bed = self._settings.get(["search_bed"])
            search_chamber = self._settings.get(["search_chamber"])

            max_search_lines = self._settings.get(["max_search_lines"])

            # Ensure integers:
            if nozzle_setpoint:
                nozzle_setpoint = int(nozzle_setpoint)
            if bed_setpoint:
                bed_setpoint = int(bed_setpoint)
            if chamber_setpoint:
                chamber_setpoint = int(chamber_setpoint)
            if max_search_lines:
                max_search_lines = int(max_search_lines)

            _N = 'Nozzle ' if search_nozzle else ''
            _B = 'Bed ' if search_bed else ''
            _C = 'Chamber ' if search_chamber else ''
            self._logger.debug(f"Searching {full_filename} for: {_N}{_B}{_C}")
        
            with open(full_filename) as f:
                for index, line in enumerate(f):
                    # self._logger.debug(f"Line {index}: {line}")
                    if line.startswith('M'):
                        # Set hotend (and wait)
                        if (line.startswith('M104') or line.startswith('M109')) and search_nozzle:
                            self._logger.debug(f"  Nozzle temp: {line}")
                            _setpoint = self.parse_heater_command(line)
                            if _setpoint and _setpoint >= MINIMAL_SETPOINT_TEMPERATURE:
                                self._logger.info(f"  Nozzle temp: {_setpoint}")
                                nozzle_setpoint = _setpoint
                                search_nozzle = False
                        # Set bed (and wait)
                        elif (line.startswith('M140') or line.startswith('M190')) and search_bed:
                            self._logger.debug(f"  Bed temp: {line}")
                            _setpoint = self.parse_heater_command(line)
                            if _setpoint and _setpoint >= MINIMAL_SETPOINT_TEMPERATURE:
                                self._logger.info(f"  Bed temp: {_setpoint}")
                                bed_setpoint = _setpoint
                                search_bed = False
                        # Set bed (and wait)
                        elif (line.startswith('M141') or line.startswith('M191')) and search_chamber:
                            self._logger.debug(f"  Chamber temp: {line}")
                            _setpoint = self.parse_heater_command(line)
                            if _setpoint and _setpoint >= MINIMAL_SETPOINT_TEMPERATURE:
                                self._logger.info(f"  Chamber temp: {_setpoint}")
                                chamber_setpoint = _setpoint
                                search_chamber = False
                    # Stop searching if we've found what we're looking for
                    if not (search_nozzle or search_bed or search_chamber):
                        self._logger.info(f"Found all temperature setpoints after {index} lines")
                        break
                    # Stop searching after parsing N lines
                    if max_search_lines and index > max_search_lines:
                        self._logger.warning(f"Could not find temperature setpoints!")
                        break
        except Exception as e:
            self._logger.error("TraceBack: {}".format(''.join(x for x in traceback.format_exception(*sys.exc_info()))))
            # In case of error, don't preheat!
            nozzle_setpoint = None
            bed_setpoint = None
            chamber_setpoint = None

        return nozzle_setpoint, bed_setpoint, chamber_setpoint


    ##~~ EventHandlerPlugin mixin

    def on_event(self, event, payload):
        try:
            if event == Events.FILE_SELECTED:
                if self._settings.get(["preheat_on_file_load"]) and payload["origin"] == "local":                    
                    fileLocation = payload.get("origin")
                    selectedFilename = payload.get("path")
                    selectedFile = self._file_manager.path_on_disk(fileLocation, selectedFilename)
                    self._logger.info(f"Start pre-heat on file loaded: {selectedFile}")

                    nozzle, bed, chamber = self.preprocess_loaded_file(selectedFile)
                    self.do_preheat(nozzle, bed, chamber)
                    
            elif event == Events.CONNECTED:
                if self._settings.get(["preheat_on_printer_connected"]):
                    self._logger.info("Starting pre-heat on printer connected")

                    tool_setpoint = self._settings.get(["nozzle_setpoint_default"])
                    if(self._settings.get(["use_last_used_tool_temperature"]) and self._last_tool_temp_setpoint > 0):
                        tool_setpoint = self._last_tool_temp_setpoint

                    bed_setpoint = self._settings.get(["bed_setpoint_default"])
                    if(self._settings.get(["use_last_used_bed_temperature"]) and self._last_bed_temp_setpoint > 0):
                        bed_setpoint = self._last_bed_temp_setpoint

                    self.do_preheat(tool_setpoint,
                                    bed_setpoint,
                                    self._settings.get(["chamber_setpoint_default"]) )
        except Exception as e:
            self._logger.error("TraceBack: {}".format(''.join(x for x in traceback.format_exception(*sys.exc_info()))))

    def on_temperatures_received(self, comm_instance, parsed_temperatures, *args, **kwargs):
        # {'B': (45.2, 50.0), 'T0': (178.9, 210.0), 'T1': (21.3, 0.0)}
        try:
            last_bed_setpoint = self._last_bed_temp_setpoint
            last_tool_setpoint = self._last_tool_temp_setpoint
            if parsed_temperatures.get("B"):
                bed_target = parsed_temperatures.get("B")[-1]
                if bed_target and bed_target >= MINIMAL_SETPOINT_TEMPERATURE:
                    self._last_bed_temp_setpoint = bed_target

            if parsed_temperatures.get("T0"):
                tool_target = parsed_temperatures.get("T0")[-1]
                if tool_target and tool_target >= MINIMAL_SETPOINT_TEMPERATURE:
                    self._last_tool_temp_setpoint = tool_target

            if last_bed_setpoint != self._last_bed_temp_setpoint or last_tool_setpoint != self._last_tool_temp_setpoint:
                self._settings.set(["last_bed_temp_setpoint"], int(self._last_bed_temp_setpoint))
                self._settings.set(["last_tool_temp_setpoint"], int(self._last_tool_temp_setpoint))
                self._logger.debug(f"Stored last Received setpoints ({parsed_temperatures}). Last setpoints Bed: {self._last_bed_temp_setpoint}, Tool: {self._last_tool_temp_setpoint}")
        except Exception as e:
            self._logger.error("TraceBack: {}".format(''.join(x for x in traceback.format_exception(*sys.exc_info()))))

        return parsed_temperatures

    ##~~ SettingsPlugin mixin

    def get_settings_defaults(self):
        return dict(
            # Setpoint settings
            nozzle_setpoint_default=215,
            bed_setpoint_default=60,
            chamber_setpoint_default=None,

            use_last_used_tool_temperature=False,
            use_last_used_bed_temperature=False,

            # File parse settings
            search_nozzle=True,
            search_bed=True,
            search_chamber=False,
            max_search_lines=2500,

            # Trigger settings
            preheat_on_file_load=True,
            preheat_on_printer_connected=True,

            check_bedready_before_preheat=False,

            # Not a setting, just to store last known setpoints...
            last_bed_temp_setpoint=None,
            last_tool_temp_setpoint=None,
        )

    def update_missing_settings(self):
        default_settings = self.get_settings_defaults()
        for key in default_settings:
            if None == self._settings.get([key]):
                self._settings.set([key], default_settings[key])
                self._logger.debug(f"Added default value ({default_settings[key]}) for missing setting '{key}'")

    def on_settings_initialized(self):
        self.update_missing_settings()
        self._last_bed_temp_setpoint = self._settings.get(["last_bed_temp_setpoint"])
        self._last_tool_temp_setpoint = self._settings.get(["last_tool_temp_setpoint"])

        
    def on_settings_save(self, data):
        # Get updated settings
        octoprint.plugin.SettingsPlugin.on_settings_save(self, data)

        self._logger.debug(f"PreHeatHelper settings saved: {data}")
        self.print_settings()

    def print_settings(self):
        settings_keys = list(self.get_settings_defaults().keys())
        all_settings = {k: self._settings.get([k]) for k in self.get_settings_defaults().keys()}
        self._logger.debug(f"All Settings: {all_settings}")

    ##~~ StartupPlugin mixin

    def on_after_startup(self):
        self._logger.debug("on_after_startup()")
        self.print_settings()

    ##~~ ShutdownPlugin mixin

    def on_shutdown(self):
        self._logger.debug("PreHeatHelper shutdown!")
        self._logger.debug(f"Last used setpoints at shutdown: tool={self._settings.get(['last_tool_temp_setpoint'])}, bed={self._settings.get(['last_bed_temp_setpoint'])}")

    ##~~ TemplatePlugin mixin

    def get_template_configs(self):
        return [ dict(type="settings", custom_bindings=False)]


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

                "stable_branch": {
                    "name": "Stable",
                    "branch": "master",
                    "comittish": ["master"],
                },
                "prerelease_branches": [
                    {
                        "name": "Release Candidate",
                        "branch": "RC",
                        "comittish": ["RC", "master"],
                    },
                    {
                        "name": "Development",
                        "branch": "dev",
                        "comittish": ["dev", "RC", "master"],
                    }
                ],


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
        "octoprint.plugin.softwareupdate.check_config": __plugin_implementation__.get_update_information,
        "octoprint.comm.protocol.temperatures.received": __plugin_implementation__.on_temperatures_received
    }
