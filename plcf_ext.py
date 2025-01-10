from __future__ import absolute_import
""" PLC Factory: PLCF# Extensions """

__author__     = "Gregor Ulm"
__copyright__  = "Copyright 2016, European Spallation Source, Lund"
__license__    = "GPLv3"


# user-defined extensions for PLCF#
import helpers
import plcf_glob


class PLCFExtException(Exception):
    pass



def plcfactory_cmdline():
    """
    Returns the command line that was used to run PLCFactory
    """
    return plcf_glob.cmdline


def plcfactory_branch():
    """
    Returns the git branch of PLCFactory
    """
    return plcf_glob.branch


def plcfactory_commit_id():
    """
    Returns the git commit id of PLCFactory
    """
    return plcf_glob.commit_id


def plcfactory_origin():
    """
    Returns the git url of PLCFactory
    """
    return plcf_glob.origin


def plcfactory_timestamp_as(formatting):
    """
    Returns the raw timestamp when PLCFactory was started
    """
    return formatting.format(plcf_glob.raw_timestamp)


def plcfactory_timestamp():
    """
    Returns the timestamp when PLCFactory was started
    """
    return plcf_glob.timestamp


def modversion():
    """
    Returns the modversion (can be None)
    """
    return plcf_glob.modversion


def default_modversion():
    """
    Returns the default modversion
    """
    return plcf_glob.default_modversion


def to_filename(x):
    assert isinstance(x, str)

    return helpers.sanitizeFilename(x)


def e3_modulename():
    return plcf_glob.e3_modulename


def e3_snippet():
    return plcf_glob.e3_snippet



def extra_colon(slot):
    return slot if ':' in slot or slot[0] == '$' else "{}:".format(slot)


class PVLengthException(PLCFExtException):
    pass



def check_pv_length(pv_name):
    assert isinstance(pv_name, str)

    if ('$' in pv_name or len(pv_name) <= 60):
        return pv_name

    raise PVLengthException("The PV name '{pv_name}' is longer than permitted ({act_len} / 60)".format(pv_name = pv_name, act_len = len(pv_name)))


def strip(what):
    """
        Strip whitspace
    """
    return what.strip()


def dash_means_empty(what):
    """
        Return an empty string if `what` is a dash (`-`) otherwise return `what`
    """
    return "" if what.strip() == "-" else what
