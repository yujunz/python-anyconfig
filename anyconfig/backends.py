#
# Copyright (C) 2011 - 2018 Satoru SATOH <ssato @ redhat.com>
# License: MIT
#
# Suppress:
# - false-positive warn at '... pkg_resources ...' line
# - import positions after some globals are defined
# pylint: disable=no-member,wrong-import-position
"""A module to aggregate config parser (loader/dumper) backends.
"""
from __future__ import absolute_import

import itertools
import logging
import operator

import anyconfig.compat
import anyconfig.ioinfo
import anyconfig.plugins
import anyconfig.utils

import anyconfig.backend.base
import anyconfig.backend.ini
import anyconfig.backend.json
import anyconfig.backend.pickle
import anyconfig.backend.properties
import anyconfig.backend.shellvars
import anyconfig.backend.xml


LOGGER = logging.getLogger(__name__)
PARSERS = [anyconfig.backend.ini.Parser, anyconfig.backend.json.Parser,
           anyconfig.backend.pickle.Parser,
           anyconfig.backend.properties.Parser,
           anyconfig.backend.shellvars.Parser, anyconfig.backend.xml.Parser]

_NA_MSG = "%s is not available. Disabled %s support."

try:
    import anyconfig.backend.yaml
    PARSERS.append(anyconfig.backend.yaml.Parser)
except ImportError:
    LOGGER.info(_NA_MSG, "yaml module", "YAML")

try:
    import anyconfig.backend.configobj
    PARSERS.append(anyconfig.backend.configobj.Parser)
except ImportError:
    LOGGER.info(_NA_MSG, "ConfigObj module", "its")

try:
    import anyconfig.backend.toml
    PARSERS.append(anyconfig.backend.toml.Parser)
except ImportError:
    LOGGER.info(_NA_MSG, "toml module", "TOML")

PARSERS.extend(anyconfig.plugins.load_plugins("anyconfig_backends"))


def fst(tpl):
    """
    >>> fst((0, 1))
    0
    """
    return tpl[0]


def snd(tpl):
    """
    >>> snd((0, 1))
    1
    """
    return tpl[1]


def groupby_key(itr, keyfunc):
    """
    An wrapper function around itertools.groupby

    :param itr: Iterable object, a list/tuple/genrator, etc.
    :param keyfunc: Key function to sort `itr`.

    >>> itr = [("a", 1), ("b", -1), ("c", 1)]
    >>> res = groupby_key(itr, operator.itemgetter(1))
    >>> [(key, tuple(grp)) for key, grp in res]
    [(-1, (('b', -1),)), (1, (('a', 1), ('c', 1)))]
    """
    return itertools.groupby(sorted(itr, key=keyfunc), key=keyfunc)


def is_parser(obj):
    """
    :return: True if given `obj` is an instance of parser.

    >>> is_parser("ini")
    False
    >>> is_parser(anyconfig.backend.base.Parser)
    False
    >>> is_parser(anyconfig.backend.base.Parser())
    True
    """
    return isinstance(obj, anyconfig.backend.base.Parser)


def _list_parsers_by_type(cps):
    """
    :param cps: A list of parser classes
    :return: List (generator) of (config_type, [config_parser])
    """
    return ((t, sorted(p, key=operator.methodcaller("priority"))) for t, p
            in groupby_key(cps, operator.methodcaller("type")))


def _list_xppairs(xps):
    """List config parsers by priority.
    """
    return sorted((snd(xp) for xp in xps),
                  key=operator.methodcaller("priority"))


def _list_parsers_by_extension(cps):
    """
    :param cps: A list of parser classes
    :return: List (generator) of (config_ext, [config_parser])
    """
    cps_by_ext = anyconfig.utils.concat(([(x, p) for x in p.extensions()] for p
                                         in cps))

    return ((x, _list_xppairs(xps)) for x, xps in groupby_key(cps_by_ext, fst))


_PARSERS_BY_TYPE = tuple(_list_parsers_by_type(PARSERS))
_PARSERS_BY_EXT = tuple(_list_parsers_by_extension(PARSERS))


def inspect_io_obj(obj, cps_by_ext=_PARSERS_BY_EXT,
                   cps_by_type=_PARSERS_BY_TYPE, forced_type=None):
    """
    Inspect a given object `obj` which may be a path string, file / file-like
    object, pathlib.Path object or `~anyconfig.globals.IOInfo` namedtuple
    object, and find out appropriate parser object to load or dump from/to it
    along with other I/O information.

    :param obj:
        a file path string, file / file-like object, pathlib.Path object or
        `~anyconfig.globals.IOInfo` object
    :param forced_type: Forced type of parser to load or dump

    :return: anyconfig.globals.IOInfo object :: namedtuple
    :raises: ValueError, UnknownParserTypeError, UnknownFileTypeError
    """
    return anyconfig.ioinfo.make(obj, cps_by_ext, cps_by_type,
                                 forced_type=forced_type)


def find_parser_by_type(forced_type, cps_by_ext=_PARSERS_BY_EXT,
                        cps_by_type=_PARSERS_BY_TYPE):
    """
    Find out appropriate parser object to load inputs of given type.

    :param forced_type: Forced parser type
    :param cps_by_type: A list of pairs (parser_type, [parser_class])

    :return:
        An instance of :class:`~anyconfig.backend.base.Parser` or None means no
        appropriate parser was found
    :raises: UnknownParserTypeError
    """
    if forced_type is None or not forced_type:
        raise ValueError("forced_type must be a some string")

    return anyconfig.ioinfo.find_parser(None, cps_by_ext=cps_by_ext,
                                        cps_by_type=cps_by_type,
                                        forced_type=forced_type)


def find_parser(obj, forced_type=None):
    """
    Find out appropriate parser object to load from a file of given path or
    file/file-like object.

    :param obj:
        a file path string, file / file-like object, pathlib.Path object or
        `~anyconfig.globals.IOInfo` object
    :param forced_type: Forced configuration parser type

    :return: A tuple of (Parser class or None, "" or error message)
    :raises: ValueError, UnknownParserTypeError, UnknownFileTypeError
    """
    if anyconfig.utils.is_ioinfo(obj):
        return obj.parser  # It must have this.

    ioi = inspect_io_obj(obj, _PARSERS_BY_EXT, _PARSERS_BY_TYPE, forced_type)
    psr = ioi.parser
    LOGGER.debug("Using parser %r [%s] for input type %s",
                 psr, psr.type(), ioi.type)
    return psr


def list_types(cps=_PARSERS_BY_TYPE):
    """List available config types.
    """
    if cps is None:
        cps = _list_parsers_by_type(PARSERS)

    return sorted(set(next(anyconfig.compat.izip(*cps))))

# vim:sw=4:ts=4:et:
