# coding=utf-8
from __future__ import absolute_import

import octoprint.plugin
import octoprint.settings
import octoprint.util
import flask
import hashlib
import os

from octoprint.server.util.flask import restricted_access
from octoprint.server import admin_permission, VERSION

class TouchUIPlugin(octoprint.plugin.SettingsPlugin,
					octoprint.plugin.AssetPlugin,
					octoprint.plugin.TemplatePlugin,
					octoprint.plugin.StartupPlugin,
					octoprint.plugin.BlueprintPlugin):

	def __init__(self):
		self._whatsNewPath = os.path.dirname(__file__) + "/WHATSNEW.md"
		self._customCssPath = os.path.dirname(__file__) + "/static/css/touchui.custom.css"
		self._customLessPath = os.path.dirname(__file__) + "/static/less/touchui.bundled.less"
		self._customHashPath = os.path.dirname(__file__) + "/static/css/hash.touchui"
		self._requireNewCSS = False

	def on_settings_load(self):
		data = dict(octoprint.plugin.SettingsPlugin.on_settings_load(self))
		data["hasCustom"] = os.path.isfile(self._customCssPath)
		data["requireNewCSS"] = self._requireNewCSS
		data["whatsNew"] = False

		if self._settings.get(["useCustomization"]):
			if os.path.isfile(self._customHashPath) is not True:
				data["requireNewCSS"] = True

		if admin_permission.can():
			if os.path.isfile(self._whatsNewPath):
				with open(self._whatsNewPath, 'r') as contentFile:
					data["whatsNew"] = contentFile.read()
				os.unlink(self._whatsNewPath)

		return data

	def on_after_startup(self):
		# Check if old LESS file equals the new LESS file, if not push/grab new generated
		if self._settings.get(["useCustomization"]):
			hashedNew = "1"
			hashedOld = "2"

			if os.path.isfile(self._customLessPath):
				with open(self._customLessPath, 'r') as contentFile:
					hashedNew = hashlib.md5(contentFile.read()).hexdigest()

			if os.path.isfile(self._customHashPath):
				with open(self._customHashPath, 'r') as contentFile:
					hashedOld = contentFile.read()

			if hashedNew != hashedOld:
				self._requireNewCSS = True

		else:
			self._remove_custom_css()

	def on_settings_save(self, data):
		del data["whatsNew"]
		del data["requireNewCSS"]
		del data["hasCustom"]
		octoprint.plugin.SettingsPlugin.on_settings_save(self, data)

		if self._settings.get(["useCustomization"]) is False:
			self._remove_custom_css()

	def increase_upload_bodysize(self, current_max_body_sizes, *args, **kwargs):
		return [("POST", r"/saveCSS", 1 * 1024 * 1024)] # set a maximum body size of 1 MB for plugin archive uploads

	@octoprint.plugin.BlueprintPlugin.route("/saveCSS", methods=["POST"])
	@restricted_access
	@admin_permission.require(403)
	def saveCSS(self):
		if not "css" in flask.request.values:
			return flask.make_response("Expected a CSS value.", 400)

		try:
			self._save_custom_css(flask.request.values["css"])

		except Exception as e:
			self._logger.warn("Exception while generating LESS file: {message}".format(message=str(e)))
			return flask.make_response(str(e), 400)

		return flask.make_response("Ok.", 200)

	@octoprint.plugin.BlueprintPlugin.route("/getCSS", methods=["POST"])
	@restricted_access
	@admin_permission.require(403)
	def getCSS(self):
		data = ""

		if not "path" in flask.request.values:
			return flask.make_response("Expected a path value.", 400)

		try:
			with open(flask.request.values["path"], 'r') as contentFile:
				data = contentFile.read()

		except Exception as e:
			self._logger.warn("Exception while generating LESS file: {message}".format(message=str(e)))
			return flask.make_response(str(e), 400)

		return flask.make_response(data, 200)

	def _save_custom_css(self, data):
		self._requireNewCSS = False
		hashed = ""

		with open(self._customCssPath, "w+") as customCSS:
			customCSS.write('{css}'.format(css=data))

		if os.path.isfile(self._customLessPath):
			with open(self._customLessPath, 'r') as contentFile:
				hashed = hashlib.md5(contentFile.read()).hexdigest()

		with open(self._customHashPath, "w+") as customHash:
			customHash.write('{hash}'.format(hash=hashed))

	def _remove_custom_css(self):
		self._requireNewCSS = False

		if os.path.isfile(self._customCssPath):
			os.unlink(self._customCssPath)

		if os.path.isfile(self._customHashPath):
			os.unlink(self._customHashPath)

	def get_template_vars(self):
		if os.path.isfile(self._customCssPath) and self._settings.get(["useCustomization"]):
			return dict(
				cssPath="/plugin/touchui/static/css/touchui.custom.css"
			)
		else:
			return dict(
				cssPath="/plugin/touchui/static/css/touchui.css"
			)

	def get_assets(self):
		return dict(
			js=[
				"js/touchui.libraries.js",
				"js/touchui.bundled.js",
				"js/touchui.knockout.js"
			]
		)

	def get_template_configs(self):

		files = [
			dict(type="generic", template="touchui_modal.jinja2", custom_bindings=True),
			dict(type="settings", template="touchui_settings.jinja2", custom_bindings=True),
			dict(type="navbar", template="touchui_menu_item.jinja2", custom_bindings=True),
			dict(type="generic", template="touchui_load_css.jinja2", custom_bindings=False)
		]

		if self._settings.get(["automaticallyLoad"]):
			files.append(
				dict(type="generic", template="touchui_auto_load.jinja2", custom_bindings=False)
			)

		return files

	def get_settings_defaults(self):
		return dict(
			hasVisibleSettings=True,
			automaticallyLoad=True,
			useCustomization=False,
			colors=dict(
				mainColor="#00B0FF",
				termColor="#0F0",
				bgColor="#000",
				textColor="#FFF",
				customPath="",
				useLocalFile=False
			)
		)

	def get_version(self):
		return self._plugin_version

	def get_update_information(self):
		return dict(
			touchui=dict(
				displayName="TouchUI",
				displayVersion=self._plugin_version,
				type="github_release",
				user="BillyBlaze",
				repo="OctoPrint-TouchUI",
				current=self._plugin_version,
				pip="https://github.com/BillyBlaze/OctoPrint-TouchUI/archive/{target_version}.zip"
			)
		)

__plugin_name__ = "TouchUI"
def __plugin_load__():
	global __plugin_implementation__
	__plugin_implementation__ = TouchUIPlugin()

	global __plugin_hooks__
	__plugin_hooks__ = {
		"octoprint.plugin.softwareupdate.check_config": __plugin_implementation__.get_update_information,
		"octoprint.server.http.bodysize": __plugin_implementation__.increase_upload_bodysize
	}
