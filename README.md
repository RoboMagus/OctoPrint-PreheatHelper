# OctoPrint-PreheatHelper

A little helper to automate your printer pre-heating!

You can have it automatically pre-heat your printer as soon as it connects to Octoprint.
Or when you (pre-)load a file this plugin can scan for the temperature setpoints in the GCode and use those to pre-heat the printer before you hit play.

## Setup

Install via the bundled [Plugin Manager](https://docs.octoprint.org/en/master/bundledplugins/pluginmanager.html)
or manually using this URL:

    https://github.com/RoboMagus/OctoPrint-PreheatHelper/archive/master.zip


## Configuration

- Set default setpoints for Nozzle, Bed, and even Chamber temperatures.
- Select if you want the plugin to start pre-heating when the printer connects using default setpoints, or when you load a print file (or both).
- For auto pre-heat when a file loads you can select for which setpoints to search (Nozzle, Bed, and Chamber) and the max number of GCode lines to parse.

