#!/usr/bin/env python
# SPDX-License-Identifier: GPL-3.0-or-later
#
# turing-smart-screen-python - a Python system monitor and library for USB-C displays like Turing Smart Screen or XuanFang
# https://github.com/mathoudebine/turing-smart-screen-python/
#
# Copyright (C) 2021 Matthieu Houdebine (mathoudebine)
# Copyright (C) 2022 Rollbacke
# Copyright (C) 2022 Ebag333
# Copyright (C) 2022 w1ld3r
# Copyright (C) 2022 Charles Ferguson (gerph)
# Copyright (C) 2022 Russ Nelson (RussNelson)
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

# This file is the system monitor main program to display HW sensors on your screen using themes (see README)

from library.pythoncheck import check_python_version
check_python_version()

import os
import sys

try:
    import atexit
    import locale
    import signal
    import subprocess
    import time
    from pathlib import Path
    from PIL import Image

    from library.log import logger
    import library.scheduler as scheduler
    from library.display import display

except Exception as e:
    print("""Import error: %s
Please follow start guide to install required packages: https://github.com/mathoudebine/turing-smart-screen-python/wiki/System-monitor-:-how-to-start
Or the troubleshooting page: https://github.com/mathoudebine/turing-smart-screen-python/wiki/Troubleshooting#all-os-tkinter-dependency-not-installed""" % str(
        e))
    try:
        sys.exit(0)
    except:
        os._exit(0)

try:
    import pystray
except:
    # If pystray cannot be loaded do not stop the program, just ignore it. The tray icon will not be displayed.
    pass

MAIN_DIRECTORY = Path(__file__).resolve().parent

if __name__ == "__main__":

    # Apply system locale to this program
    locale.setlocale(locale.LC_ALL, '')

    logger.debug("Using Python %s" % sys.version)


    def wait_for_empty_queue(timeout: int = 5):
        # Waiting for all pending request to be sent to display
        logger.info("Waiting for all pending request to be sent to display (%ds max)..." % timeout)

        wait_time = 0
        while not scheduler.is_queue_empty() and wait_time < timeout:
            time.sleep(0.1)
            wait_time = wait_time + 0.1

        logger.debug("(Waited %.1fs)" % wait_time)

    def clean_stop(tray_icon=None):
        # Turn screen and LEDs off before stopping
        display.turn_off()

        # Do not stop the program now in case data transmission was in progress
        # Instead, ask the scheduler to empty the action queue before stopping
        scheduler.STOPPING = True

        # Waiting for all pending request to be sent to display
        wait_for_empty_queue(5)

        # Remove tray icon just before exit
        if tray_icon:
            tray_icon.visible = False

        # We force the exit to avoid waiting for other scheduled tasks: they may have a long delay!
        try:
            sys.exit(0)
        except:
            os._exit(0)

    def on_signal_caught(signum, frame=None):
        logger.info("Caught signal %d, exiting" % signum)
        clean_stop()

    def on_configure_tray(tray_icon, item):
        logger.info("Configure from tray icon")

        try:
            # Load Python file with local python interpreter (useful for venvs)
            configure_file = next(MAIN_DIRECTORY.glob("configure.py"))
            subprocess.Popen([sys.executable, str(configure_file)])
        except:
            # Load binary (for releases) or Python file with system interpreter
            configure_file = next(MAIN_DIRECTORY.glob("configure*"))
            subprocess.Popen([str(configure_file)])

        clean_stop(tray_icon)

    def on_exit_tray(tray_icon, item):
        logger.info("Exit from tray icon")
        clean_stop(tray_icon)


    def on_clean_exit(*args):
        logger.info("Program will now exit")
        clean_stop()


    # Create a tray icon for the program, with an Exit entry in menu
    try:
        tray_icon = pystray.Icon(
            name='Turing System Monitor',
            title='Turing System Monitor',
            icon=Image.open(MAIN_DIRECTORY / "res/icons/monitor-icon-17865/64.png"),
            menu=pystray.Menu(
                pystray.MenuItem(
                    text='Configure',
                    action=on_configure_tray),
                pystray.Menu.SEPARATOR,
                pystray.MenuItem(
                    text='Exit',
                    action=on_exit_tray)
            )
        )

        tray_icon.run_detached()
        logger.info("Tray icon has been displayed")
    except:
        tray_icon = None
        logger.warning("Tray icon is not supported on your platform")

    # Set the different stopping event handlers, to send a complete frame to the LCD before exit
    atexit.register(on_clean_exit)
    signal.signal(signal.SIGINT, on_signal_caught)
    signal.signal(signal.SIGTERM, on_signal_caught)
    signal.signal(signal.SIGQUIT, on_signal_caught)

    # Initialize the display
    logger.info("Initialize display")
    display.initialize_display()

    # Start serial queue handler
    scheduler.QueueHandler()

    # Create all static images
    display.display_static_images()

    # Create all static texts
    display.display_static_text()

    # Wait for static images/text to be displayed before starting monitoring (to avoid filling the queue while waiting)
    wait_for_empty_queue(10)

    # Start sensor scheduled reading. Avoid starting them all at the same time to optimize load
    logger.info("Starting system monitoring")
    import library.stats as stats

    scheduler.CPUPercentage(); time.sleep(0.25)
    scheduler.CPUFrequency(); time.sleep(0.25)
    scheduler.CPULoad(); time.sleep(0.25)
    scheduler.CPUTemperature(); time.sleep(0.25)
    scheduler.CPUFanSpeed(); time.sleep(0.25)
    if stats.Gpu.is_available():
        scheduler.GpuStats(); time.sleep(0.25)
    scheduler.MemoryStats(); time.sleep(0.25)
    scheduler.DiskStats(); time.sleep(0.25)
    scheduler.NetStats(); time.sleep(0.25)
    scheduler.DateStats(); time.sleep(0.25)
    scheduler.SystemUptimeStats(); time.sleep(0.25)
    scheduler.CustomStats(); time.sleep(0.25)
    scheduler.WeatherStats(); time.sleep(0.25)
    scheduler.PingStats(); time.sleep(0.25)
