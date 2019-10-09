"""
This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this
file, You can obtain one at https://mozilla.org/MPL/2.0/.
"""

import atexit
from contextlib import suppress
import json
import os
from pathlib import Path
import platform
import sys
import tempfile


from PySide2.QtWidgets import QApplication, QWidget
from PySide2.QtGui import QCloseEvent, QIcon, QImage, QWindow
from PySide2.QtCore import QByteArray, QEvent, QObject

import bpy
from bpy.app.handlers import persistent

if platform.system().lower() == 'linux':
	# TODO: Need to point this to 'window_geometry_prefs.json' in the use's blender data folder (the folder with /config and /scripts)
	PREFS_FILEPATH = ''
elif platform.system().lower() == 'darwin':
	# TODO: Need to point this to 'window_geometry_prefs.json' in the use's blender data folder (the folder with /config and /scripts)
	PREFS_FILEPATH = ''
elif platform.system().lower() == 'windows':
	import pywintypes
	import win32con
	import win32api
	import win32gui
	import win32process
	import win32ui

	PREFS_FILEPATH = Path(os.getenv('APPDATA')) / 'Blender Foundation' / 'Blender' / 'window_geometry_prefs.json'
else:
	PREFS_FILEPATH = ''

PREFS_KEY_ON_SCREEN = 'window_on_screen'
PREFS_KEY_WINDOW_GEOMETRY = 'window_geometry'
TEMP_ICON_FILEPATH = Path(tempfile.gettempdir()) / 'blender_icon.png'
TICK = 1.0 / float(os.getenv('BQT_TICK_RATE', '30'))


class BlenderApplication(QApplication):
	"""
	[description]

	**Arguments:**

		None

	**Keyword Arguments:**

		:``argv``: `[type]` [description]
	"""

	def __init__(self, argv = None):
		argv = [] if argv is None else argv
		super().__init__(argv)
		#self.setStyleSheet(<str>)
		self.should_close = False
		self._hwnd = win32gui.FindWindow(None, 'blender')
		self._blender_window = QWindow.fromWinId(self._hwnd)
		self.blender_widget = QWidget.createWindowContainer(self._blender_window)

		if platform.system().lower() == 'windows':
			self._get_application_icon_windows()
		elif platform.system().lower() == 'darwin':
			self._get_application_icon_macintosh()
		elif platform.system().lower() == 'linux':
			self._get_application_icon_linux()

		QApplication.setWindowIcon(QIcon(str(TEMP_ICON_FILEPATH)))
		self._set_window_geometry()

		self.focusObjectChanged.connect(self._on_focus_object_changed)


	def notify(self, receiver: QObject, event: QEvent):
		"""
		[description]

		**Arguments:**

			:``receiver``: `qobject` [description]
			:``event``: `qevent` [description]

		**Keword Arguments:**

			None

		**Returns:**

			:``[type]``: [description]
		"""

		if isinstance(event, QCloseEvent) and receiver in (self.blender_widget, self._blender_window):
			event.ignore()
			self._store_window_geometry()
			self.should_close = True
			return False

		return super().notify(receiver, event)


	def _on_focus_object_changed(self, focus_object: QObject):
		"""
		[description]

		**Arguments:**

			:``focus_object``: `qobject` [description]

		**Keword Arguments:**

			None
		"""

		if focus_object is self.blender_widget:
			win32gui.SetFocus(self._hwnd)


	def _set_window_geometry(self):
		"""
		Loads storeed widnow geometry preferences and applies them to the QWindow.
		.setGeometry() sets the size of the window minus the window frame.
		For this reason it should be set on self.blender_widget.

		**Arguments:**

			None

		**Keword Arguments:**

			None
		"""

		# with suppress(FileNotFoundError, json.decoder.JSONDecodeError):
		# 	settings = json.loads(PREFS_FILEPATH.read_text())

		# if settings:
		# 	window_geometry = settings.get(PREFS_KEY_WINDOW_GEOMETRY)
			# if window_geometry:
			# 	self.blender_widget.setGeometry(*window_geometry)
			# 	return

		self.blender_widget.showMaximized() # This doesn't work if it is called on self._blender_window


	@staticmethod
	def _get_application_icon_linux():
		"""
		Linux
		This finds the running blender process, extracts the blender icon from the blender.exe file on disk and saves it to the user's temp folder.
		It then creates a QIcon with that data and returns it.

		**Arguments:**

			None

		**Keword Arguments:**

			None
		"""

		raise NotImplementedError


	@staticmethod
	def _get_application_icon_macintosh():
		"""
		Macintosh
		This finds the running blender process, extracts the blender icon from the blender.exe file on disk and saves it to the user's temp folder.
		It then creates a QIcon with that data and returns it.

		**Arguments:**

			None

		**Keword Arguments:**

			None
		"""

		raise NotImplementedError


	@staticmethod
	def _get_application_icon_windows():
		"""
		Windows
		This finds the running blender process, extracts the blender icon from the blender.exe file on disk and saves it to the user's temp folder.
		It then creates a QIcon with that data and returns it.

		**Arguments:**

			None

		**Keword Arguments:**

			None
		"""

		for pid in win32process.EnumProcesses():
			with suppress(pywintypes.error):
				handle = win32api.OpenProcess(win32con.PROCESS_ALL_ACCESS, False, pid)
				exe = win32process.GetModuleFileNameEx(handle, 0)
				if 'blender' in exe.lower():
					hdc = win32ui.CreateDCFromHandle(win32gui.GetDC(0))
					hbmp = win32ui.CreateBitmap()
					ico_x = win32api.GetSystemMetrics(win32con.SM_CXICON)
					ico_y = win32api.GetSystemMetrics(win32con.SM_CYICON)
					hbmp.CreateCompatibleBitmap(hdc, ico_x, ico_y)
					hdc = hdc.CreateCompatibleDC()
					hdc.SelectObject(hbmp)
					large, _small = win32gui.ExtractIconEx(exe, 0)
					hdc.DrawIcon((0, 0), large[0])
					bmpstr = hbmp.GetBitmapBits(True)

					img = QImage()
					img.loadFromData(QByteArray(bmpstr))
					img.save(str(TEMP_ICON_FILEPATH), 'png')


	def _store_window_geometry(self):
		"""
		Stores the current window geometry for the QWindow
		The .geometry() method on QWindow includes the size of the application minus the window frame.
		For that reason the _blender_widget should be used.

		**Arguments:**

			None

		**Keword Arguments:**

			None
		"""

		#screen = self._blender_widget.screen() # This fails and halts this function from completing.
		geometry = self.blender_widget.geometry()

		settings = {#PREFS_KEY_ON_SCREEN : screen,
						 PREFS_KEY_WINDOW_GEOMETRY : (geometry.x(), geometry.y(), geometry.width(), geometry.height())}

		PREFS_FILEPATH.write_text(json.dumps(settings))



class QOperator(bpy.types.Operator):
	"""
	QOperator is a subclass of the Blender `bpy.types.Operator`
	It instantiates the application if one does not exist already
	"""

	bl_idname = "qoperator.global_app"
	bl_label = "Global QApplication"


	def __init__(self):
		super().__init__()
		self.__qapp = None


	def execute(self, _context):
		"""
		[description]

		**Arguments:**

			:``_context``: `[type]` [description]

		**Keword Arguments:**

			None

		**Returns:**

			:``[type]``: [description]
		"""

		self.__qapp = instantiate_application()
		return {'PASS_THROUGH'}



def instantiate_application():
	"""
	[description]

	**Arguments:**

		None

	**Keword Arguments:**

		None

	**Returns:**

		:``[type]``: [description]
	"""

	app = QApplication.instance()
	if not app:
		app = BlenderApplication(sys.argv)
		bpy.app.timers.register(on_update, persistent = True)

	return app


def on_update():
	"""
	[description]

	**Arguments:**

		None

	**Keword Arguments:**

		None

	**Returns:**

		:``[type]``: [description]
	"""

	app = QApplication.instance()
	if app.should_close:
		bpy.ops.wm.quit_blender({'window': bpy.context.window_manager.windows[0]}, 'INVOKE_DEFAULT')

	return TICK


@persistent
def create_global_app(*args):
	"""
	[description]

	**Arguments:**

		None

	**Keword Arguments:**

		None
	"""

	if 'startup' in __file__ and not os.getenv('BQT_DISABLE_STARTUP'):
		bpy.ops.qoperator.global_app()


def register():
	"""
	[description]

	**Arguments:**

		None

	**Keword Arguments:**

		None
	"""

	bpy.utils.register_class(QOperator)
	if not create_global_app in bpy.app.handlers.load_post:
		bpy.app.handlers.load_post.append(create_global_app)


def unregister():
	"""
	[description]

	**Arguments:**

		None

	**Keword Arguments:**

		None
	"""

	bpy.utils.unregister_class(QOperator)
	if create_global_app in bpy.app.handlers.load_post:
		bpy.app.handlers.load_post.remove(create_global_app)


def onexit():
	"""
	[description]

	**Arguments:**

		None

	**Keword Arguments:**

		None
	"""

	app = QApplication.instance()
	if app:
		app.quit()


atexit.register(onexit)

if __name__ == '__main__':
	try:
		unregister()
	except (ValueError, TypeError) as e:
		print('Failed to unregister QOperator: {}'.format(e))

	register()
