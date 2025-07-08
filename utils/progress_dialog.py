# -*- coding: utf-8 -*-
"""
/***************************************************************************
 AcATaMa
                                 A QGIS plugin
 AcATaMa is a Qgis plugin for Accuracy Assessment of Thematic Maps
                              -------------------
        copyright            : (C) 2017-2025 by Xavier C. Llano, SMByC
        email                : xavier.corredor.llano@gmail.com
 ***************************************************************************/

/***************************************************************************
 *                                                                         *
 *   This program is free software; you can redistribute it and/or modify  *
 *   it under the terms of the GNU General Public License as published by  *
 *   the Free Software Foundation; either version 2 of the License, or     *
 *   (at your option) any later version.                                   *
 *                                                                         *
 ***************************************************************************/
"""
# based on https://github.com/dask/dask/blob/main/dask/diagnostics/progress.py

import threading
import time
from timeit import default_timer

from dask.callbacks import Callback
from qgis.PyQt.QtWidgets import QProgressDialog


class DaskQTProgressDialog(Callback):
    """A QT progress dialog for dask.

    Parameters
    ----------
    minimum : int, optional
        Minimum time threshold in seconds before displaying a progress bar.
        Default is 0 (always display)
    dt : float, optional
        Update resolution in seconds, default is 0.1 seconds
    """

    def __init__(self, progress_dialog: QProgressDialog, minimum=0, dt=0.2):
        self._progress_dialog = progress_dialog
        self._minimum = minimum
        self._dt = dt
        self.last_duration = 0

    def _start(self, dsk):
        self._state = None
        self._start_time = default_timer()
        # Start background thread
        self._running = True
        self._timer = threading.Thread(target=self._timer_func)
        self._timer.daemon = True
        self._timer.start()

    def _pretask(self, key, dsk, state):
        self._state = state

    def _finish(self, dsk, state, errored):
        self._running = False
        elapsed = default_timer() - self._start_time
        self.last_duration = elapsed
        if elapsed < self._minimum:
            return
        if not errored:
            self._draw_bar(1)
        else:
            self._update_bar()

    def _timer_func(self):
        """Background thread for updating the progress bar"""
        while self._running:
            elapsed = default_timer() - self._start_time
            if elapsed > self._minimum:
                self._update_bar()
            time.sleep(self._dt)

    def _update_bar(self):
        s = self._state
        if not s:
            self._draw_bar(0)
            return
        ndone = len(s["finished"])
        ntasks = sum(len(s[k]) for k in ["ready", "waiting", "running"]) + ndone
        if ndone < ntasks:
            self._draw_bar(ndone / ntasks if ntasks else 0)

    def _draw_bar(self, frac):
        percent = int(100 * frac)
        self._progress_dialog.setValue(percent)
        self._progress_dialog.update()
