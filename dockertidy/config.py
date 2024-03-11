#!/usr/bin/env python3
"""Global settings definition."""

import os

import anyconfig
import environs
import jsonschema.exceptions
import ruamel.yaml
from appdirs import AppDirs
from jsonschema._utils import format_as_index

import dockertidy.exception
import dockertidy.parser
from dockertidy.parser import env
from dockertidy.utils import Singleton, dict_intersect

config_dir = AppDirs("docker-tidy").user_config_dir
default_config_file = os.path.join(config_dir, "config.yml")


class Config:
    """
    Create an object with all necessary settings.

    Settings are loade from multiple locations in defined order (last wins):
        - default settings defined by `self._get_defaults()`
        - yaml config file, defaults to OS specific user config directory
        - provided cli parameters
    """

    SETTINGS = {
        "command": {
            "default": "",
        },
        "config_file": {
            "default": "",
            "env": "CONFIG_FILE",
            "type": environs.Env().str,
        },
        "dry_run": {
            "default": False,
            "env": "DRY_RUN",
            "file": True,
            "type": environs.Env().bool,
        },
        "http_timeout": {
            "default": 60,
            "env": "HTTP_TIMEOUT",
            "file": True,
            "type": environs.Env().int,
        },
        "logging.level": {
            "default": "WARNING",
            "env": "LOG_LEVEL",
            "file": True,
            "type": environs.Env().str,
        },
        "logging.json": {
            "default": False,
            "env": "LOG_JSON",
            "file": True,
            "type": environs.Env().bool,
        },
        "gc.max_container_age": {
            "default": "",
            "env": "GC_MAX_CONTAINER_AGE",
            "file": True,
            "type": env.timedelta_validator,
        },
        "gc.max_image_age": {
            "default": "",
            "env": "GC_MAX_IMAGE_AGE",
            "file": True,
            "type": env.timedelta_validator,
        },
        "gc.dangling_volumes": {
            "default": False,
            "env": "GC_DANGLING_VOLUMES",
            "file": True,
            "type": environs.Env().bool,
        },
        "gc.exclude_images": {
            "default": [],
            "env": "GC_EXCLUDE_IMAGES",
            "file": True,
            "type": environs.Env().list,
        },
        "gc.exclude_container_labels": {
            "default": [],
            "env": "GC_EXCLUDE_CONTAINER_LABELS",
            "file": True,
            "type": environs.Env().list,
        },
        "stop.max_run_time": {
            "default": "",
            "env": "STOP_MAX_RUN_TIME",
            "file": True,
            "type": env.timedelta_validator,
        },
        "stop.prefix": {
            "default": [],
            "env": "STOP_PREFIX",
            "file": True,
            "type": environs.Env().list,
        },
    }

    def __init__(self, args=None):
        """
        Initialize a new settings class.

        :param args: An optional dict of options, arguments and commands from the CLI.
        :param config_file: An optional path to a yaml config file.
        :returns: None

        """
        if args is None:
            self._args = {}
        else:
            self._args = args
        self._schema = None
        self.config_file = default_config_file
        self.config = None
        self._set_config()

    def _get_args(self, args):
        cleaned = dict(filter(lambda item: item[1] is not None, args.items()))

        normalized = {}
        for key, value in cleaned.items():
            normalized = self._add_dict_branch(normalized, key.split("."), value)

        # Override correct log level from argparse
        levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        log_level = levels.index(self.SETTINGS["logging.level"]["default"])
        if normalized.get("logging"):
            for adjustment in normalized["logging"]["level"]:
                log_level = min(len(levels) - 1, max(log_level + adjustment, 0))
            normalized["logging"]["level"] = levels[log_level]

        return normalized

    def _get_defaults(self, files=False):
        normalized = {}

        for key, item in self.SETTINGS.items():
            if files and not item.get("file"):
                continue
            normalized = self._add_dict_branch(normalized, key.split("."), item["default"])

        self.schema = anyconfig.gen_schema(normalized)
        return normalized

    def _get_envs(self):
        normalized = {}
        for key, item in self.SETTINGS.items():
            if item.get("env"):
                prefix = "TIDY_"
                envname = prefix + item["env"]
                try:
                    value = item["type"](envname)
                    normalized = self._add_dict_branch(normalized, key.split("."), value)
                except environs.EnvError as e:
                    if f'"{envname}" not set' in str(e):
                        pass
                    else:
                        raise dockertidy.exception.ConfigError(
                            "Unable to read environment variable", str(e)
                        ) from e

        return normalized

    def _set_config(self):
        args = self._get_args(self._args)
        envs = self._get_envs()
        defaults = self._get_defaults()
        files_raw = self._get_defaults(files=True)

        # preset config file path
        if envs.get("config_file"):
            self.config_file = self._normalize_path(envs.get("config_file"))

        if args.get("config_file"):
            self.config_file = self._normalize_path(args.get("config_file"))

        source_files = []
        source_files.append(self.config_file)
        source_files.append(os.path.join(os.getcwd(), ".dockertidy"))
        source_files.append(os.path.join(os.getcwd(), ".dockertidy.yml"))
        source_files.append(os.path.join(os.getcwd(), ".dockertidy.yaml"))

        for config in [i for i in source_files if os.path.exists(i)]:
            with open(config, encoding="utf8") as stream:
                s = stream.read()
                try:
                    normalized = ruamel.yaml.YAML(typ="safe", pure=True).load(s)
                except (ruamel.yaml.composer.ComposerError, ruamel.yaml.scanner.ScannerError) as e:
                    message = f"{e.context} {e.problem}"
                    raise dockertidy.exception.ConfigError(
                        f"Unable to read config file {config}", message
                    ) from e

                if self._validate(normalized):
                    anyconfig.merge(files_raw, normalized, ac_merge=anyconfig.MS_DICTS)
                    files_raw["logging"]["level"] = files_raw["logging"]["level"].upper()

        files = dict_intersect(files_raw, self._get_defaults(files=True))

        if self._validate(files):
            anyconfig.merge(defaults, files, ac_merge=anyconfig.MS_DICTS)

        if self._validate(envs):
            anyconfig.merge(defaults, envs, ac_merge=anyconfig.MS_DICTS)

        if self._validate(args):
            anyconfig.merge(defaults, args, ac_merge=anyconfig.MS_DICTS)

        if "config_file" in defaults:
            defaults.pop("config_file")

        defaults["logging"]["level"] = defaults["logging"]["level"].upper()

        self.config = defaults

    def _normalize_path(self, path):
        if not os.path.isabs(path):
            base = os.path.join(os.getcwd(), path)
            return os.path.abspath(os.path.expanduser(os.path.expandvars(base)))

        return path

    def _validate(self, config):
        try:
            anyconfig.validate(config, self.schema, ac_schema_safe=False)
        except jsonschema.exceptions.ValidationError as e:
            schema = format_as_index(list(e.relative_schema_path)[:-1])
            schema_error = f"Failed validating '{e.validator}' in schema {schema}\n{e.message}"
            raise dockertidy.exception.ConfigError("Configuration error", schema_error) from e

        return True

    def _add_dict_branch(self, tree, vector, value):
        key = vector[0]
        tree[key] = (
            value
            if len(vector) == 1
            else self._add_dict_branch(tree.get(key, {}), vector[1:], value)
        )
        return tree


class SingleConfig(Config, metaclass=Singleton):
    """Singleton config object."""

    pass
