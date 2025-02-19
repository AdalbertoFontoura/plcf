#!/usr/bin/env python2
# vim: set fileencoding=utf-8 :

from __future__ import print_function
from __future__ import absolute_import

""" PLC Factory: Entry point """

__author__     = "Gregor Ulm"
__copyright__  = "Copyright 2016, European Spallation Source, Lund"
__credits__    = [ "Gregor Ulm",
                   "David Brodrick",
                   "Nick Levchenko",
                   "Francois Bellorini",
                   "Ricardo Fernandes"
                 ]
__license__    = "GPLv3"
__maintainer__ = "Krisztián Löki"
__email__      = "krisztian.loki@ess.eu"
__status__     = "Production"
__env__        = "Python version 2.7"
__product__    = "ics_plc_factory"

# Python libraries
import sys
import argparse
from collections import OrderedDict
import datetime
import filecmp
import os
import time
import hashlib
import zlib
from shutil import copy2
from ast import literal_eval as ast_literal_eval

import plcf_git as git

tainted = False
master_branch = True


def taint_message():
    ret = False
    if not master_branch:
        ret = True
        print("""
+*+*+*+*+*+*+*+*+*+*+*+*+*+*+*+*+*+*+*+*+*+*+*+*+*+*+
* You are not on branch 'master'; warranty is void. *
+*+*+*+*+*+*+*+*+*+*+*+*+*+*+*+*+*+*+*+*+*+*+*+*+*+*+
""", file = sys.stderr)

    if tainted:
        ret = True
        print("""
+++++++++++++++++++++++++++++++++++++++++++++++++++++
+ Your working copy is not clean; warranty is void. +
+++++++++++++++++++++++++++++++++++++++++++++++++++++
""", file = sys.stderr)

    return ret


if git.get_status() is False:
    tainted = True

if git.get_current_branch() != "master":
    master_branch = False


taint_message()

# Template Factory
parent_dir = os.path.abspath(os.path.dirname(__file__))
tf_dir     = os.path.join(parent_dir, 'template_factory')
sys.path.append(tf_dir)
del tf_dir

from tf_ifdef import IF_DEF, FOOTER_IF_DEF

try:
    import tf
except AttributeError as e:
    if e.args[0] == "'module' object has no attribute 'iglob'":
        # glob.py has been renamed to plcf_glob.py but the .pyc can still be
        # there. Remove the .pyc and reload glob and try to import tf again
        os.unlink(os.path.join(parent_dir, "glob.pyc"))
        import glob
        from imp import reload as imp_reload
        imp_reload(glob)
        del glob
        del imp_reload

        import tf
    else:
        raise

del parent_dir


# PLC Factory modules
import plcf_glob as glob
import plcf
from plcf_ext import PLCFExtException
from cc import CC
import helpers


# global variables
OUTPUT_DIR      = "output"
MODULES_DIR     = os.path.join(os.path.dirname(__file__), "module_templates")
TEMPLATE_TAG    = "TEMPLATE"
HEADER_TAG      = "HEADER"
FOOTER_TAG      = "FOOTER"
IFDEF_EXTENSION = ".def"
hashobj         = None
ifdefs          = dict()
printers        = dict()
ifdef_params    = dict(PLC_TYPE = "SIEMENS", PLCF_STATUS = not tainted)
plcfs           = dict()
output_files    = dict()
previous_files  = None
device_tag      = None
epi_version     = None
hashes          = dict()
prev_hashes     = None
IOC_ARGS        = None
ioc             = None
e3              = None
PLCF_BRANCH     = git.get_current_branch()
PLCF_URL        = helpers.url_strip_user(git.get_origin())
COMMIT_ID       = git.get_local_ref(PLCF_BRANCH)
VERIFY          = False
RAW_TIMESTAMP   = None
if COMMIT_ID is not None:
    ifdef_params["COMMIT_ID"] = COMMIT_ID


class PLCFactoryException(Exception):
    status = 1
    def __init__(self, *args):
        super(PLCFactoryException, self).__init__(*args)

        try:
            if isinstance(args[0], Exception):
                self.message = args[0].args[0]
            else:
                self.message = args[0]
        except IndexError:
            self.message = ""


    def __str__(self):
        if self.message is not None:
            return """
{banner}
{msg}
{banner}
""".format(banner = "*" * max(map(lambda x: len(x), self.message.splitlines())), msg = self.message)
        else:
            return super(PLCFactoryException, self).__str__()



class ProcessTemplateException(PLCFactoryException):
    def __init__(self, device, template, exception, *args):
        super(ProcessTemplateException, self).__init__(*args)
        self.device    = device
        self.template  = template
        self.exception = exception
        self.message = """The following exception occured during the processing of template '{template}' of device '{device}':
{exc}: {msg}""".format(template = self.template,
                       device   = self.device,
                       exc      = type(self.exception).__name__,
                       msg      = self.exception)



class Hasher(object):
    def __init__(self, hash_base = None):
        self._hashobj = hashlib.sha256(hash_base.encode())


    def update(self, string):
        try:
            self._hashobj.update(string.encode())
        except UnicodeDecodeError:
            # Happens on Py2 with strings containing unicode characters
            self._hashobj.update(string)


    def _crc32(self):
        return zlib.crc32(self._hashobj.hexdigest().encode())


    def getHash(self):
        return self._hashobj.hexdigest()


    def getCRC32(self):
        crc32 = self._crc32()
        # Python3 returns an UNSIGNED integer. But we need a signed integer
        if crc32 > 0x7FFFFFFF:
            return str(crc32 - 0x100000000)

        return str(crc32)



class E3(object):
    @staticmethod
    def add_parser_args(parser):
        parser.add_argument(
                            '--e3',
                            help    = "create a minimal E3 module with EPICS-DB and startup snippet",
                            metavar = "modulename",
                            nargs   = "?",
                            type    = str,
                            const   = ""
                           )

        return parser


    @staticmethod
    def parse_args(args):
        if args.e3 is None:
            return None

        if args.e3 != "":
            return E3(args.e3)
        else:
            # processDevice() will create the correct E3
            return True


    def __init__(self, modname, snippet = None):
        super(E3, self).__init__()

        if snippet is None:
            modname = helpers.sanitizeFilename(modname.lower())

        if modname.startswith('e3-'):
            modname = modname[len('e3-'):]

        self._modulename = modname.replace('-', '_')
        self._snippet    = snippet.replace('-', '_') if snippet is not None else self._modulename

        self._files = []
        self._test_cmd = False
        self._iocsh = None

        glob.e3_modulename = self._modulename
        glob.e3_snippet    = self._snippet


    def modulename(self):
        """
        Returns the name of the module without the 'e3-' prefix
        """
        return self._modulename


    def snippet(self):
        """
        Returns the snippet; the base name that is used for .iocsh files
        """
        return self._snippet


    def iocsh(self):
        """
        Returns the name of the main iocsh file
        """
        return os.path.basename(self._iocsh)


    def files(self):
        """
        Returns the list of files that are in the module
        """
        return self._files


    def iocsh_printer(self):
        """
        Returns the printer that generated the iocsh snippet
        """
        return  printers["IOCSH"]


    @staticmethod
    def from_device(device):
        """
        Create an E3 object from the EPICSModule and EPICSSnippet properties of 'device'
        """

        dev_props = device.properties()
        modulename = dev_props.get("EPICSModule", [])
        if len(modulename) == 1:
            modulename = modulename[0]
            if modulename != helpers.sanitizeFilename(modulename):
                print("Overriding modulename because it is not a valid filename", file = sys.stderr)
        else:
            if modulename:
                print("Ignoring EPICSModule property; it is an array: {}".format(modulename), file = sys.stderr)
            modulename = device.name().lower()

        modulename = helpers.sanitizeFilename(modulename)

        snippet = dev_props.get("EPICSSnippet", [])
        if len(snippet) == 1:
            snippet = snippet[0]
            validSnippet = helpers.sanitizeFilename(snippet)
            if snippet != validSnippet:
                print("Overriding snippet because it is not a valid filename", file = sys.stderr)
                snippet = validSnippet
        else:
            if snippet:
                print("Ignoring EPICSSnippet property; it is an array: {}".format(snippet), file = sys.stderr)
            snippet = modulename

        return E3(modulename, snippet)


    def copy_files(self, basedir):
        """
        Create the directory structure and copy the generated files
        """
        ch = copy_helper(basedir)

        #
        # Copy files
        #
        ch.m_cp(output_files.get('EPICS-DB', output_files.get('EPICS-OPC-DB')), "db", self.modulename() + ".db")

        try:
            ch.m_cp(output_files['EPICS-TEST-DB'],           "db",      self.modulename() + "-test.db")
        except KeyError:
            pass

        try:
            self._iocsh = ch.m_cp(output_files['IOCSH'],     "iocsh",   self.snippet() + ".iocsh")
        except KeyError:
            pass

        try:
            ch.m_cp(output_files['TEST-IOCSH'],              "iocsh",   self.snippet() + "-test.iocsh")
            self._test_cmd = True
        except KeyError:
            self._test_cmd = False

        ch.m_cp(output_files["CREATOR"],                     "misc",    "creator")
        ch.m_cp(output_files["DEVICE-LIST"],                 "misc",    "device-list.txt")

        try:
            ch.m_cp(output_files["BECKHOFF"],                "misc",    os.path.basename(output_files["BECKHOFF"]))
        except KeyError:
            pass

        try:
            ch.m_cp(output_files["STANDARD_SCL"],            "misc",    os.path.basename(output_files["STANDARD_SCL"]))
        except KeyError:
            pass

        try:
            ch.m_cp(output_files["PROJECT_SCL"],             "misc",    os.path.basename(output_files["PROJECT_SCL"]))
        except KeyError:
            pass

        try:
            ch.m_cp(output_files["ARCHIVE"],                 "misc",    self.modulename() + ".archive")
        except KeyError:
            pass

        #
        # Copy CCDB dump
        #
        if output_files['CCDB-DUMP'] is not None:
            miscdir = os.path.join(basedir, "misc")
            try:
                import zipfile
                with zipfile.ZipFile(output_files['CCDB-DUMP'], "r") as z:
                    z.extractall(miscdir)
                    self._files.extend(map(lambda x: os.path.join(miscdir, x), z.namelist()))
                    z.close()
            except:
                helpers.rmdirs(os.path.join(miscdir, "ccdb"))
                print("Cannot copy CCDB dump to E3 module", file = sys.stderr)

        #
        # Copy the README file to the modname directory
        #
        readme = os.path.join(basedir, "README.md")
        copy2(output_files["PLC-README"], readme)
        self._files.append(readme)

        self._files.extend(ch.copied())

        return self._files


    def create(self):
        """
        Create the E3 module and some helper scripts to run it
        """
        out_mdir = os.path.join(OUTPUT_DIR, "modules", "-".join([ "e3", self.modulename() ]))
        helpers.makedirs(out_mdir)

        self._files.extend(m_copytree(module_dir("e3"), out_mdir))

        out_sdir = os.path.join(out_mdir, self.modulename())
        helpers.makedirs(out_sdir)
        self.copy_files(out_sdir)

        output_files['E3'] = self._files

        # It returns the autosave-iocsh if it was generated otherwise the 'normal' iocsh
        iocsh_printer   = self.iocsh_printer()
        macro_list      = iocsh_printer.macros()
        if macro_list:
            macros      = ", ".join(["{m}={m}".format(m = iocsh_printer.macro_name(macro)) for macro in macro_list])
            live_macros = ", {}".format(macros)
        else:
            macros      = ""
            live_macros = ""

        #
        # Create script to run module with 'safe' defaults
        #
        run_module_bash = os.path.join(OUTPUT_DIR, "run_module.bash")
        with open(run_module_bash, "w") as run:
            if 'OPC' in ifdef_params['PLC_TYPE']:
                rmb_macros = """PORT = 4840, PUBLISHING_INTERVAL = 200{macros}""".format(macros = live_macros)
            else:
                rmb_macros = """RECVTIMEOUT = 3000{macros}""".format(macros = live_macros)

            print("""#!/bin/bash

export IOCNAME='{modulename}'
export IOCDIR='autosave-{modulename}'

iocsh.bash -l {moduledir}/cellMods \\
    -r autosave \\
    -r {modulename},plcfactory \\
    -c 'iocshLoad("$({modulename}_DIR)/{iocsh}", "IPADDR = 127.0.0.1, {macros}")' \\
    -c 'iocshLoad("$(autosave_DIR)/autosave.iocsh", "AS_TOP = ., NUM_SEQ = 1")'
""".format(modulename = self.modulename(),
           moduledir  = os.path.abspath(out_mdir),
           iocsh      = self.iocsh(),
           macros     = rmb_macros), file = run)

            os.chmod(run_module_bash, 0o775)

        if self._test_cmd:
            #
            # Create script to run test version of module
            #
            run_test_module_bash = os.path.join(OUTPUT_DIR, "run_test_module.bash")
            with open(run_test_module_bash, "w") as run:
                if macros:
                    test_macros = ', "{}"'.format(macros)
                else:
                    test_macros = ""

                print("""#!/bin/bash

export IOCNAME='{modulename}'
export IOCDIR='autosave-{modulename}-test'

iocsh.bash -l {moduledir}/cellMods \\
    -r autosave \\
    -r {modulename},plcfactory \\
    -c 'iocshLoad($({modulename}_DIR)/{snippet}-test.iocsh, "_={macros}")' \\
    -c 'iocshLoad("$(autosave_DIR)/autosave.iocsh", "AS_TOP = ., NUM_SEQ = 1")'
""".format(modulename = self.modulename(),
           moduledir  = os.path.abspath(out_mdir),
           snippet    = self.snippet(),
           macros     = test_macros), file = run)

            os.chmod(run_test_module_bash, 0o775)

        print("E3 Module created:", out_mdir)
        return out_mdir



class IOC(object):
    REQUIRED_MODULES = [ "essioc", "s7plc", "modbus", "calc" ]
    AUTO_COMMIT_MSG = "auto"

    @staticmethod
    def check_requirements():
        try:
            import yaml
        except ImportError:
            raise NotImplementedError("""
++++++++++++++++++++++++++++++
Could not find package `yaml`!
Please install it by running:

pip2 install --user pyyaml==5.4.1

""")


    @staticmethod
    def add_parser_args(parser):
        group = parser.add_argument_group("IOC related options")

        group.add_argument(
                            "--ioc",
                            help     = "Generate IOC and if git repository is defined tag it with the given version as `plcfactory_<version>`",
                            metavar  = "version",
                            type     = str,
                            const    = "",
                            nargs    = "?")

        group.add_argument(
                            "--no-ioc-git",
                            dest     = "ioc_git",
                            help     = "Ignore any git repository when generating IOC",
                            default  = True,
                            action   = "store_false")

        group.add_argument(
                            "--no-ioc-git-tag",
                            dest     = "ioc_git_tag",
                            help     = "Do not tag the generated IOC when a version is specified",
                            default  = True,
                            action   = "store_false")

        group.add_argument(
                            "--no-ioc-st-cmd",
                            dest     = "ioc_st_cmd",
                            help     = "Do not generate an `st.cmd` file when generating IOC",
                            default  = True,
                            action   = "store_false")

        group.add_argument(
                            "--ioc-git-commit-message",
                            dest     = "ioc_commit_msg",
                            help     = "Specify commit message to use. If left empty then the default commit message will be used",
                            metavar  = "commit_message",
                            const    = IOC.AUTO_COMMIT_MSG, # if there is no argument to the option this will be the argument
                            type     = str,
                            nargs    = "?")
        
        group.add_argument( "--ioc-conda",
                            help     = "Create a conda-based IOC",
                            action   = "store_true")
        
        group.add_argument(
                            "--ioc-epics-version",
                            dest     = "ioc_epics_version",
                            help     = "Specifiy EPICS base version to use. Default is 7.0.8.1.",
                            default  = "7.0.8.1"
        )

        group.add_argument(
                            "--ioc-require-version",
                            dest     = "ioc_require_version",
                            help     = "Specifiy require version to use. Default is 5.1.1.",
                            default  = "5.1.1"
        )

        return parser


    @staticmethod
    def parse_args(args):
        if args.ioc is None:
            return None

        IOC.check_requirements()

        class ioc_args(object):
            def __init__(self, args):
                self.ioc = args.ioc
                self.ioc_git = args.ioc_git
                self.ioc_git_tag = args.ioc_git_tag
                self.ioc_st_cmd = args.ioc_st_cmd
                self.ioc_commit_msg = args.ioc_commit_msg
                self.conda = args.ioc_conda
                self.epics_version = args.ioc_epics_version
                self.require_version = args.ioc_require_version
                

        return ioc_args(args)


    def __init__(self, device_s, args):
        super(IOC, self).__init__()

        if isinstance(device_s, list):
            device = device_s[0]
            self._controlled_devices = list(device_s)
        else:
            device = device_s
            self._controlled_devices = None

        self._ioc = self.__get_ioc(device)
        if self._ioc != device:
            # Create our own E3 module
            self._e3 = E3(device.name())
        else:
            self._e3 = None

        self._conda = args.conda
        self._epics_version = args.epics_version
        self._require_version = args.require_version

        self._dir = helpers.sanitizeFilename(self.name().lower()).replace('-', '_')
        self._generate_st_cmd = args.ioc_st_cmd
        self._repo = get_repository(self._ioc, "IOC_REPOSITORY") if args.ioc_git else None
        self._tag_repo = args.ioc_git_tag
        self._commit_msg = args.ioc_commit_msg
        if self._repo:
            git.GIT.check_minimal_config()

            if not self._repo.endswith(".git"):
                self._repo += ".git"

            self._dir = helpers.url_to_path(self._repo).split('/')[-1]
            if self._dir.endswith(".git"):
                self._dir = self._dir[:-4]


    def __get_ioc(self, device):
        """
        Get the IOC that _directly_ controls 'device'
        """
        if device.deviceType() == "IOC":
            return device

        for c in device.controlledBy(convert = False):
            if c.deviceType() == "IOC":
                return c

        raise PLCFactoryException("Could not find IOC for {}".format(device.name()))


    def __get_contents(self, fname):
        try:
            stat = os.stat(fname)
            if stat.st_size > 1024 * 1024:
                raise PLCFactoryException("'{}' is suspiciously large. Refusing to continue".format(os.path.basename(fname)))
        except OSError:
            return None

        with open(fname, "rt") as f:
            return f.read()


    def __create_st_cmd(self, out_idir):
        st_cmd = os.path.join(out_idir, "st.cmd")

        existing_st_cmd_contents = self.__get_contents(st_cmd)

        # Check if we have to keep an existing st.cmd intact
        if existing_st_cmd_contents is not None and not self._generate_st_cmd:
            return st_cmd

        proposed_st_cmd_contents = """# Startup for {iocname}

# Load required modules
{modules}

# Load standard IOC startup scripts
iocshLoad("$(essioc_DIR)/common_config.iocsh")

# Load PLC specific startup script
iocshLoad("$(IOCSH_TOP)/iocsh/{iocsh}", "DBDIR=$(IOCSH_TOP)/db/, MODVERSION=$(IOCVERSION=)")
""".format(iocname = self.name(),
           modules = "\n".join(["require {}".format(module) for module in self.REQUIRED_MODULES]),
           iocsh = self._e3.iocsh())

        # Check if we have to backup existing st.cmd
        if existing_st_cmd_contents is not None and existing_st_cmd_contents != proposed_st_cmd_contents:
            if os.name == "nt":
                os.replace(st_cmd, os.path.join(out_idir, "st.cmd.orig"))
            else:
                os.rename(st_cmd, os.path.join(out_idir, "st.cmd.orig"))

        with open(st_cmd, "wt") as f:
            print(proposed_st_cmd_contents, file = f)

        return st_cmd


    def __create_ioc_metadata_file(self, out_idir):
        import json

        ioc_metadata = os.path.join(out_idir, "ioc.json")
        try:
            with open(ioc_metadata, "rt") as f:
                metadata = json.load(f)
        except IOError:
            metadata = dict()

        if self._conda:
            metadata["ioc_type"] = "conda"
        else:
            metadata["ioc_type"] = "nfs"
            metadata["epics_version"] = self._epics_version
            metadata["require_version"] = self._require_version

        with open(ioc_metadata, "wt") as f:
            json.dump(metadata,f)

        return ioc_metadata


    def __create_ioc_env_file(self, out_idir):
        import yaml
        
        ioc_env = os.path.join(out_idir, "environment.yaml")
        try:
            with open(ioc_env, "rt") as f:
                env = yaml.safe_load(f)
        except IOError:
            env = dict()
        
        env["dependencies"] = [
            "epics-base={}".format(self._epics_version),
            "require={}".format(self._require_version),
            "essioc",
            "s7plc",
            "calc",
            "modbus"
        ]
        
        with open(ioc_env, "wt") as f:
            yaml.dump(env,f)

        return ioc_env


    def __create_custom_iocsh(self, out_idir):
        custom_iocsh = os.path.join(out_idir, "iocsh")
        helpers.makedirs(custom_iocsh)
        custom_iocsh = os.path.join(custom_iocsh, "custom.iocsh")

        # basically a 'touch custom.iocsh'
        with open(custom_iocsh, "at"):
            pass

        return custom_iocsh


    def __create_run_ioc(self, out_dir, iocdir):
        run_ioc_sh = os.path.join(out_dir, "run_ioc.sh")
        major, minor, patch = map(int, self._require_version.split("."))
        with open(run_ioc_sh, "w") as run:
            print("""#!/bin/bash

# Script to start {iocname}

# This variable sets the base autosave directory; the actual autosave files will be in $(AS_TOP)/{iocslug}/save
(
export AS_TOP=/tmp
export IOCNAME="{iocname}"
export IOCDIR="{iocslug}"

source /epics/base-{epics_version}/require/{require_version}/bin/{activate_script}

{iocsh} {iocdir}/st.cmd
)
""".format(iocname = self.name(),
           iocslug = self.name().replace(':', '_'),
           iocdir = iocdir,
           epics_version = self._epics_version,
           require_version = self._require_version,
           iocsh = "iocsh.bash" if major < 4 else "iocsh",
           activate_script = "setE3Env.bash" if major < 3 else "activate"),
                file = run)
        

            os.chmod(run_ioc_sh, 0o775)


    def name(self):
        """
        Returns the IOC name
        """
        return self._ioc.name()


    def directory(self):
        """
        Returns the directory name (as derived from repo URL or name) where the IOC is generated
        """
        return self._dir


    def repo(self):
        """
        Returns the IOC repository URL
        """
        return self._repo


    @staticmethod
    def _create_plcfactory_ignore(ioc):
        plcfactory_ignore = os.path.join(ioc._path, ".plcfactory_ignore")
        with open(plcfactory_ignore, "wt") as pf:
            print("# List of files that are not managed by PLCFactory", file = pf)
        ioc.add(plcfactory_ignore)


    def get_ignored_files(self, out_idir, repo):
        """
        Returns the list of files (with absolute path) that should not be removed by PLCFactory
        """
        plcfactory_ignore = os.path.join(out_idir, ".plcfactory_ignore")
        try:
            with open(plcfactory_ignore, "rt") as pf:
                # Remove newlines, empty lines, and comments
                return list(map(lambda p: os.path.join(out_idir, p), filter(lambda y: True if y and y[0] != '#' else False, map(lambda x: x.strip(), pf.readlines()))))
        except IOError as e:
            if e.errno == 2:
                self._create_plcfactory_ignore(repo)
                return []
            raise


    def create(self, version):
        """
        Generate IOC
        """

        branch = "{}{}".format("{}_by_".format(version) if version else "", "PLCFactory_on_{}".format(glob.timestamp))
        out_idir = os.path.join(OUTPUT_DIR, "ioc", self.directory())
        helpers.makedirs(out_idir)
        if self.repo():
            # Cannot specify 'branch = "master"'; git segfaults when trying to clone an empty repository and checking out its "master" branch
            # Update the master branch if available, and initialize an empty repository
            repo = git.GIT.clone(self.repo(), out_idir, update = "Lazy", initialize_if_empty = True, gitignore_contents = "/cell/", initializer = self._create_plcfactory_ignore)
            # Create branch 'branch' based on the default branch
            repo.create_branch(branch, repo.get_default_branch())
        else:
            repo = None

        created_files = []
        if self._e3:
            # Copy the generated e3 files
            self._e3.copy_files(out_idir)
            # Create st.cmd
            st_cmd = self.__create_st_cmd(out_idir)
            created_files.append(st_cmd)

        # Create ioc.json
        ioc_metadata_file = self.__create_ioc_metadata_file(out_idir)
        created_files.append(ioc_metadata_file)

        if self._conda:
            ioc_env_file = self.__create_ioc_env_file(out_idir)
            created_files.append(ioc_env_file)

        # Create custom.iocsh
        custom_iocsh = self.__create_custom_iocsh(out_idir)
        created_files.append(custom_iocsh)

        # Create run_ioc.sh
        self.__create_run_ioc(OUTPUT_DIR, out_idir)

        # Update the repository
        if repo:
            auto_commit = self._commit_msg is not None
            if self._commit_msg and self._commit_msg != IOC.AUTO_COMMIT_MSG:
                self._commit_msg = """{}

""".format(self._commit_msg)
                exit_helper = ""
            else:
                self._commit_msg = ""
                exit_helper = """
###################################################################
#
# To exit press Esc and then type :wq and then press Enter
#
###################################################################
"""

            commit_msg = """{user_commit_msg}Generated by PLCFactory on {tstamp}

{exit_helper}
Date:
=====
{tstamp}

PLCFactory URL:
===============
{url}

PLCFactory branch:
==================
{branch}

PLCFactory commit:
==================
{commit}

Command line:
=============
{cmdline}
""".format(user_commit_msg = self._commit_msg,
           exit_helper = exit_helper,
           tstamp  = '{:%Y-%m-%d %H:%M:%S}'.format(RAW_TIMESTAMP),
           url     = PLCF_URL,
           branch  = PLCF_BRANCH,
           commit  = COMMIT_ID,
           cmdline = " ".join(sys.argv))

            repo.add(created_files)
            if os.path.isfile(os.path.join(out_idir, "env.sh")):
                repo.remove("env.sh")

            # Create list of generated/ignored files inside subdirectories
            generated_files = self.get_ignored_files(out_idir, repo)
            generated_files.extend(created_files)
            if self._e3:
                repo.add(self._e3.files())
                generated_files.extend(list(self._e3.files()))

            # Remove files that are not created by PLCFactory inside subdirectories
            repo.remove_stale_items(generated_files)

            repo.commit(msg = commit_msg, edit = not auto_commit)

            # Tag if requested
            tag_repo = self._tag_repo and version
            if tag_repo:
                repo.tag("plcfactory_{}".format(version), override_local = True)

            # Push the branch
            link = repo.push()

            # Open a create merge request page if we created a tag (and the URL)
            if link and tag_repo:
                try:
                    print("Launching browser to create merge request...")
                    helpers.xdg_open(link)
                except helpers.FileNotFoundError:
                    print("""
Could not launch browser to create merge request, please visit:

{}

""".format(link))



class PLC(object):
    @staticmethod
    def add_parser_args(parser):
        plc_group = parser.add_argument_group("PLC related options")

        plc_args = plc_group.add_mutually_exclusive_group()

        default_tia = "TIAv15.1"

        plc_args.add_argument(
                              "--plc-siemens",
                              "--plc-interface",
                              dest    = "siemens",
                              help    = "use the default templates for Siemens PLCs and generate interface PLC comms. The default TIA version is {}".format(default_tia),
                              metavar = "TIA-Portal-version",
                              nargs   = "?",
                              const   = default_tia,
                              type    = str
                             )

        plc_args.add_argument(
                              "--plc-beckhoff",
                              dest    = "beckhoff",
                              help    = "use the default templates for Beckhoff PLCs and generate interface Beckhoff PLC comms. 'Beckhoff-version' is not used right now",
                              metavar = "Beckhoff-version",
                              nargs   = "?",
                              const   = "not-used",
                              type    = str
                             )

        plc_args.add_argument(
                              "--plc-opc",
                              dest    = "opc",
                              help    = "use the default templates for OPC-UA. No PLC code is generated!",
                              action  = "store_true",
                             )

        diag_args = plc_group.add_mutually_exclusive_group()
        diag_args.add_argument(
                               "--plc-diag",
                               dest     = "plc_no_diag",
                               help     = "generate PLC diagnostics code (if used with --plc-x)",
                               action   = "store_false",
                               default  = True,
                               required = False)

        diag_args.add_argument(
                               "--plc-only-diag",
                               help     = "generate PLC diagnostics code only (if used with --plc-x)",
                               action   = "store_true",
                               required = False)

        test_args = plc_group.add_mutually_exclusive_group()
        test_args.add_argument(
                               "--plc-no-test",
                               dest     = "plc_test",
                               help     = "do not generate PLC comms testing code (if used with --plc-x). This is the default",
                               action   = "store_false",
                               default  = False,
                               required = False)

        test_args.add_argument(
                               "--plc-test",
                               help     = "generate PLC comms testing code (if used with --plc-x)",
                               action   = "store_true",
                               required = False)

        plc_group.add_argument(
                               "--plc-readonly",
                               help     = "do not generate EPICS --> PLC communication code",
                               action   = "store_true",
                               default  = False)

        # This should only be used for testing purposes
        plc_group.add_argument(
                               "--plc-hostname",
                               help = "Override the `Hostname` CCDB property of the PLC. Only use it for testing purposes")

        return parser


    @staticmethod
    def parse_args(args):
        if args.siemens is not None:
            return SIEMENS_PLC(args)

        if args.beckhoff:
            return BECKHOFF_PLC(args)

        if args.opc:
            return OPC_PLC(args)

        return None


    @staticmethod
    def type():
        raise NotImplementedError


    def __init__(self, args):
        super(PLC, self).__init__()

        # FIXME: these arguments should not even be exposed without --plc-siemens
        if (args.plc_only_diag or args.plc_no_diag is False) and not args.siemens:
            raise PLCFArgumentError('--plc-only-diag requires --plc-siemens')

        self._readonly = args.plc_readonly
        self._only_diag = args.plc_only_diag
        self._no_diag = args.plc_no_diag
        self._test = args.plc_test
        self._hostname = args.plc_hostname
        self._version = None
        self._plc = None
        self._plc_plcf = None
        self._hashobj = None
        self._ifdefs = []


    def is_readonly(self):
        return self._readonly


    def hostname(self):
        """
        Returns the hostname set in the arguments. If not set it will return None
        WILL NOT RETURN THE VALUE OF THE 'Hostname' CCDB property
        """
        return self._hostname


    def _validate_plc_device(self):
        pass


    def set_plc(self, plc):
        self._plc = plc
        self._plc_plcf = getPLCF(self._plc)
        self._validate_plc_device()

        hash_base = """EPICSToPLCDataBlockStartOffset: [PLCF#EPICSToPLCDataBlockStartOffset]
PLCToEPICSDataBlockStartOffset: [PLCF#PLCToEPICSDataBlockStartOffset]
PLC-EPICS-COMMS:Endianness: [PLCF#PLC-EPICS-COMMS:Endianness]"""
        # GatewayDatablock is a relatively new feature; do not break the hash for PLCs not using it
        try:
            gw_db = self._plc_plcf.getProperty("PLC-EPICS-COMMS: GatewayDatablock")
            if gw_db:
                hash_base = """{}
PLC-EPICS-COMMS: GatewayDatablock: {}""".format(hash_base, gw_db)
        except plcf.PLCFNoPropertyException:
            pass
        hash_base = "\n".join(self._plc_plcf.process(hash_base.splitlines()))

        self._hashobj = initializeHash(hash_base)

        return hash_base


    def get_ifdefs(self, devices):
        print("Downloading Interface Definition files...")
        print("-----------------------------------------")
        for device in devices:
            cplcf = getPLCF(device)
            print(cplcf)
            print(device.name())
#            print("Device type: " + device.deviceType())

            self._hashobj.update(device.name())
            print("depois do update")
            ifdef = getIfDef(device, cplcf)
            print(ifdef)
            print("depois do ifdef")
            if ifdef is not None:
                ifdef.calculate_hash(self._hashobj)
                self._ifdefs.append(ifdef)
            
            print("=" * 40)

        cur_hash = (self._hashobj.getHash(), self._hashobj.getCRC32())

        global hashes
        hashes[self._plc.name()] = cur_hash

        self._footer_ifdef = FOOTER_IF_DEF(self._plc, self._ifdefs, PLCF = self._plc_plcf, **ifdef_params)

        try:
            prev_hash = prev_hashes[self._plc.name()]
            # Check if CRC32 is the same but the actual hash is different
            if prev_hash[0] is not None and prev_hash[0] != cur_hash[0] and prev_hash[1] == cur_hash[1]:
                raise PLCFactoryException("CRC32 collision detected. Please file a bug report")
        except (KeyError, TypeError):
            pass


    def generate_files(self, devices, templates):
        remaining_templates = []
        for template in templates:
            if not self._generate_file(devices, template):
                remaining_templates.append(template)

        return remaining_templates


    def _get_printer(self, template):
        try:
            return printers[template]
        except KeyError:
            templatePrinter = tf.get_printer(template)

        if templatePrinter is not None:
            printers[template] = templatePrinter

        return templatePrinter


    def _generate_file(self, devices, template):
        printer = self._get_printer(template)
        if printer is None:
            return False

        start_time = time.time()

        self._plc_plcf.register_template(template)

        if device_tag:
            tagged_templateID = "_".join([ device_tag, template ])
        else:
            tagged_templateID = template

        print("#" * 60)
        print("Template ID " + tagged_templateID)
        print("Device at root: " + str(self._plc) + "\n")

        header = []
        print("ifdef_params:\n")
        print(ifdef_params)
        printer.header(None, header, ROOT_DEVICE = self._plc, PLCF = self._plc_plcf, OUTPUT_DIR = OUTPUT_DIR, HELPERS = helpers, **ifdef_params)
        # has to acquire filename _before_ processing the header
        # there are some special tags that are only valid in the header
        outputFile = os.path.join(OUTPUT_DIR, createFilename(self._plc_plcf, header))

        if header:
            header = self._plc_plcf.process(header)
            header = processHash(header, self._hashobj)

        print("Processing entire tree of controls-relationships:\n")

        template_from_def_file = "Generating '{}' template from Definition File...".format(template)

        # for each device, find corresponding template and process it
        output     = []
        for device in devices:
            deviceType = device.deviceType()
            cplcf      = getPLCF(device)
            cplcf.register_template(template)

            print(device.name())
            print("Device type: " + deviceType)

            ifdef = getIfDef(device, cplcf)
            if ifdef is not None:
                print(template_from_def_file)

                try:
                    printer.body(ifdef, output, DEVICE = device, PLCF = cplcf) #printer_iff.py line139
                except (tf.TemplatePrinterException, plcf.PLCFException, PLCFExtException) as e:
                    raise ProcessTemplateException(device.name(), template, e)

            print("=" * 40)

        print("\n")

        footer = []
        printer.footer(self._footer_ifdef, footer, PLCF = self._plc_plcf)
        if footer:
            footer = self._plc_plcf.process(footer)
            footer = processHash(footer, self._hashobj)

        output = header + output + footer

        if not output:
            print("There were no templates for ID = {}.\n".format(tagged_templateID))
            return

        # Process counters
        (output, _) = plcf.PLCF.evalCounters(output)

        eol = getEOL(header)
        # write file
        with open(outputFile, 'w') as f:
            for line in output:
                line = line.rstrip()
                if not line.startswith("#COUNTER") \
                   and not line.startswith("#FILENAME") \
                   and not line.startswith("#EOL"):
                    print(line, end = eol, file = f)

        output_files[template] = outputFile

        print("Output file written:", outputFile)
        print("Hash sum:", self._hashobj.getCRC32())
        print("--- %s %.1f seconds ---\n" % (tagged_templateID, time.time() - start_time))

        return True


    def generate_plc(self, out_dir, commit_id, verify):
        from interface_factory import IFA

        output_files.update(IFA.produce(out_dir, output_files["IFA"], TIAVersion = self._version, nodiag = self._no_diag, onlydiag = self._only_diag, commstest = self._test, verify = verify, readonly = self._readonly, commit_id = commit_id))



class S7PLC_MODBUS_PLC(PLC):
    def __init__(self, args):
        super(S7PLC_MODBUS_PLC, self).__init__(args)


    def _validate_plc_device(self):
        toplc_offset = None
        fromplc_offset = None
        try:
            toplc_offset = int(self._plc_plcf.getProperty("EPICSToPLCDataBlockStartOffset"))
            if int(toplc_offset) < 0:
                raise ValueError
        except (TypeError, ValueError):
            raise PLCFactoryException("Invalid EPICSToPLCDataBlockStartOffset property: {}".format(toplc_offset))

        try:
            fromplc_offset = int(self._plc_plcf.getProperty("PLCToEPICSDataBlockStartOffset"))
            if int(fromplc_offset) < 0:
                raise ValueError
        except (TypeError, ValueError):
            raise PLCFactoryException("Invalid PLCToEPICSDataBlockStartOffset property: {}".format(fromplc_offset))



class SIEMENS_PLC(S7PLC_MODBUS_PLC):
    @staticmethod
    def PLC_is_siemens():
        return False

    PLC.is_siemens = PLC_is_siemens


    @staticmethod
    def update_default_printers(default_printers):
        default_printers.update( [ "EPICS-DB", "EPICS-TEST-DB", "IFA", "ARCHIVE", "BEAST", "BEAST-TEMPLATE", "PLC-README" ] )


    @staticmethod
    def is_siemens():
        return True


    @staticmethod
    def type():
        return "SIEMENS"


    def __init__(self, args):
        super(SIEMENS_PLC, self).__init__(args)

        from interface_factory import IFA
        tia_version  = args.siemens.lower()
        try:
            tia_version  = IFA.consolidate_tia_version(tia_version)
        except IFA.FatalException as e:
            raise PLCFArgumentError(e.message)

        self._version = tia_version


    def _validate_plc_device(self):
        super(SIEMENS_PLC, self)._validate_plc_device()

        try:
            interface_id = int(self._plc_plcf.getProperty("PLC-EPICS-COMMS: InterfaceID"))
        except (TypeError, ValueError) as e:
            raise PLCFactoryException("Missing/invalid 'PLC-EPICS-COMMS: InterfaceID'")



class BECKHOFF_PLC(S7PLC_MODBUS_PLC):
    @staticmethod
    def PLC_is_beckhoff():
        return False

    PLC.is_beckhoff = PLC_is_beckhoff


    @staticmethod
    def update_default_printers(default_printers):
        default_printers.update( [ "EPICS-DB", "EPICS-TEST-DB", "IFA", "ARCHIVE", "BEAST", "BEAST-TEMPLATE", "PLC-README" ] )


    @staticmethod
    def is_beckhoff():
        return True


    @staticmethod
    def type():
        return "BECKHOFF"


    def __init__(self, args):
        super(BECKHOFF_PLC, self).__init__(args)

        if self._only_diag or self._no_diag is False:
            raise PLCFArgumentError('PLCFactory cannot (yet?) generate diagnostics code for Beckhoff PLCs')


    def _validate_plc_device(self):
        super(BECKHOFF_PLC, self)._validate_plc_device()

        if int(self._plc_plcf.getProperty("EPICSToPLCDataBlockStartOffset")) < 12288:
            raise PLCFactoryException("PLCF#EPICSToPLCDataBlockStartOffset property must be at least 12288! Are you using PLC_BECKHOFF?")



class OPC_PLC(PLC):
    @staticmethod
    def PLC_is_opc():
        return False

    PLC.is_opc = PLC_is_opc


    @staticmethod
    def update_default_printers(default_printers):
        # EPICS-DB will be deleted later, but we add it here so that it is enough to check for EPICS-DB
        default_printers.update( [ "EPICS-DB", "EPICS-OPC-DB", "BEAST", "BEAST-TEMPLATE" ] )


    @staticmethod
    def is_opc():
        return True


    @staticmethod
    def type():
        return "OPC"


    def __init__(self, args):
        super(OPC_PLC, self).__init__(args)


    def generate_plc(self, *args, **kwargs):
        return



def initializeHash(hash_base = None):
    return Hasher(hash_base)


def openHeaderFooter(device, tag, templateID):
    assert isinstance(tag,        str)
    assert isinstance(templateID, str)

    artifact = device.downloadArtifact(extension = ".txt",
                                       filetype = "{} for {}".format("_".join([ tag, TEMPLATE_TAG, templateID ]), templateID),
                                       custom_filter = matchingArtifact,
                                       filter_args = ((tag, TEMPLATE_TAG), templateID))

    if not artifact:
        return []

    with open(artifact.saved_as()) as f:
        lines = f.readlines()

    return lines


def downloadTemplate(device, templateID):
    assert isinstance(templateID, str)

    artifact = device.downloadArtifact(extension = ".txt",
                                       filetype = "{} for {}".format("_".join([ TEMPLATE_TAG, templateID ]), templateID),
                                       custom_filter = matchingArtifact,
                                       filter_args = (TEMPLATE_TAG, templateID))

    if artifact is not None:
        return artifact.saved_as()

    return None


def matchingArtifact(artifact, tag, templateID):
    filename = artifact.filename()

    # exactly one '.' in filename
    if filename.count('.') != 1:
        return False

    assert isinstance(templateID, str)
    if isinstance(tag, tuple):
        assert len(tag) == 2
        assert isinstance(tag[0], str)
        assert isinstance(tag[1], str)

        match  = "{}.txt".format("_".join([ tag[0], tag[1], templateID ]))
    else:
        assert isinstance(tag, str)

        # do not match HEADERs and FOOTERs if not in HEADER/FOOTER mode
        if HEADER_TAG in filename or FOOTER_TAG in filename:
            return False
        match  = "{}.txt".format("_".join([ tag, templateID ]))

    return filename.endswith(match)


def createFilename(cplcf, header):
    assert isinstance(header, list)

    tag    = "#FILENAME"
    tagPos = findTag(header, tag)

    # default filename is chosen when no custom filename is specified
    if tagPos == -1:
        header = [ '{} [PLCF#RAW_INSTALLATION_SLOT]_[PLCF#DEVICE_TYPE]-[PLCF#TEMPLATE]_[PLCF#TIMESTAMP].scl'.format(tag) ]
        tagPos = 0

    filename = header[tagPos]

    # remove tag and strip surrounding whitespace
    filename = filename[len(tag):].strip()
    filename = cplcf.process(filename)

    return helpers.sanitizeFilename(filename)


def findTag(lines, tag):
    tagPos = -1

    if not lines:
        return tagPos

    assert isinstance(lines, list)
    assert isinstance(tag,   str)

    for i in range(len(lines)):
        if lines[i].startswith(tag):
            tagPos = i
            break

    return tagPos


def processHash(header, hashobj):
    assert isinstance(header, list)

    tag     = "#HASH"
    pos     = -1

    for i in range(len(header)):
        if tag in header[i]:
            pos = i
            hashSum     = hashobj.getCRC32()
            line        = header[pos]
            tagPos      = line.find(tag)
            line        = line[:tagPos] + hashSum + line[tagPos + len(tag):]
            header[pos] = line

    return header


def getEOL(header):
    assert isinstance(header, list)

    tag    = "#EOL"
    tagPos = findTag(header, tag)

    if tagPos == -1:
        return "\n"

    # this really is a quick and dirty hack
    # should be replaced by something like
    # #EOL CR LF
    return header[tagPos][len(tag):].strip().replace('\\n', '\n').replace('\\r', '\r').strip('"').strip("'")


#
# Returns an interface definition object
#
def getIfDef(device, cplcf):
    # If a definition file is already downloaded (and parsed) for this device then we must use that one
    try:
        return ifdefs[device.name()]
    except KeyError:
        pass

    artifact = device.downloadArtifact(IFDEF_EXTENSION, device_tag, filetype = "Interface Definition")
    if artifact is None:
        # No 'file' artifact found, let's see if there is a URL
        artifact = device.downloadExternalLink("EPI", IFDEF_EXTENSION, device_tag, "Interface Definition", git_tag = epi_version)
        if artifact is None:
            # No def file is present, do not check again
            ifdefs[device.name()] = None
            return None

    # We can no longer cache parsed per-device-type definition files; there might be PLCF expressions in them
    ifdef = IF_DEF.parse(artifact, PLCF = cplcf, **ifdef_params)

    if ifdef is not None:
        ifdefs[device.name()] = ifdef

    return ifdef


def getHeader(device, templateID, plcf):
    assert isinstance(templateID, str)

    try:
        templatePrinter = printers[templateID]
    except KeyError:
        templatePrinter = tf.get_printer(templateID)

    if templatePrinter is not None:
        print("Using built-in '{}' template header".format(templateID))
        printers[templateID] = templatePrinter
        header = []
        templatePrinter.header(None, header, ROOT_DEVICE = device, PLCF = plcf, OUTPUT_DIR = OUTPUT_DIR, HELPERS = helpers, **ifdef_params)
    else:
        header = openHeaderFooter(device, HEADER_TAG, templateID)

    if not header:
        print("No header found.\n")
    else:
        print("Header read.\n")

    return (header, templatePrinter)


def getFooter(device, templateID, plcf):
    try:
        templatePrinter = printers[templateID]
    except KeyError:
        return openHeaderFooter(device, FOOTER_TAG, templateID)

    print("Using built-in '{}' template footer".format(templateID))
    footer = []
    templatePrinter.footer(None, footer, PLCF = plcf)

    return footer


def getPLCF(device):
    global plcfs

    device_name = device.name()
    try:
        return plcfs[device_name]
    except KeyError:
        cplcf = plcf.PLCF(device)
        plcfs[device_name] = cplcf
        return cplcf


def processTemplateID(templateID, devices):
    assert isinstance(templateID, str)
    assert isinstance(devices,    list)

    start_time = time.time()
    print("processa o template!!!!")
    rootDevice = devices[0]
    print(rootDevice)
    rcplcf     = getPLCF(rootDevice)
    rcplcf.register_template(templateID)

    if device_tag:
        tagged_templateID = "_".join([ device_tag, templateID ])
    else:
        tagged_templateID = templateID

    print("#" * 60)
    print("Template ID " + tagged_templateID)
    print("Device at root: " + str(rootDevice) + "\n")

    # collect lines to be written at the end
    output = []

    # process header
    (header, templatePrinter) = getHeader(rootDevice, templateID, rcplcf)
    # has to acquire filename _before_ processing the header
    # there are some special tags that are only valid in the header
    outputFile = os.path.join(OUTPUT_DIR, createFilename(rcplcf, header))

    if header:
        header = rcplcf.process(header)

    print("Processing entire tree of controls-relationships:\n")

    can_combine   = tf.is_combinable(templateID)
    def_seen      = None
    template_seen = None

    template_from_def_file = "Generating '{}' template from Definition File...".format(templateID)
    template_built_in = "Using default built-in '{}' template...".format(templateID)

    # for each device, find corresponding template and process it
    output     = []
    for device in devices:
        deviceType = device.deviceType()
        cplcf      = getPLCF(device)
        cplcf.register_template(templateID)
        processed = False

        print(device.name())
        print("Device type: " + deviceType)

        hashobj.update(device.name())

        # get template
        template = None

        # Try to process Interface Definition first
        if templatePrinter is not None:
            ifdef = getIfDef(device, cplcf)
            if ifdef is not None:
                print(template_from_def_file)

                def_seen = True
                ifdef.calculate_hash(hashobj)
                # TemplatePrinters do their own PLCF processing, so
                # we can use 'output' instead of an empty list and do no PLCF processing on 'output' later
                template = output
                try:
                    templatePrinter.body(ifdef, template, DEVICE = device, PLCF = cplcf)
                    processed = True
                except (tf.TemplatePrinterException, plcf.PLCFException, PLCFExtException) as e:
                    raise ProcessTemplateException(device.name(), templateID, e)

        # Try to download template from artifact
        if template is None:
            template = downloadTemplate(device, "_" + tagged_templateID if device_tag else tagged_templateID)
            if template is not None:
                template_seen = True

        if def_seen and template_seen and not can_combine:
            raise PLCFactoryException("Cannot combine Interface Definitions and ordinary templates with {}".format(templateID))

        # Try to check if we have a default template printer implementation
        if template is None and templatePrinter is not None and not templatePrinter.needs_ifdef():
            print(template_built_in)
            template = []
            try:
                templatePrinter.body(None, template, DEVICE = device, PLCF = cplcf)
            except tf.TemplatePrinterException as e:
                raise ProcessTemplateException(device.name(), templateID, e)

        if template is not None:
            if not processed:
                # process template and add result to output
                try:
                    if isinstance(template, str):
                        with open(template, 'r') as f:
                            output += cplcf.process(f)
                    else:
                        output += cplcf.process(template)
                except (plcf.PLCFException, PLCFExtException) as e:
                    raise ProcessTemplateException(device.name(), templateID, e)

            print("Template processed.")

        else:
            print("No template found.")

        print("=" * 40)

    print("\n")

    if not def_seen:
        glob.ccdb.computeHash(hashobj)

    footer = getFooter(rootDevice, templateID, rcplcf)
    if footer:
        footer = rcplcf.process(footer)

    # process #HASH keyword in header and footer
    header      = processHash(header, hashobj)
    footer      = processHash(footer, hashobj)

    output      = header + output + footer

    if not output:
        print("There were no templates for ID = {}.\n".format(tagged_templateID))
        return

    # Process counters
    (output, _) = plcf.PLCF.evalCounters(output)

    eol = getEOL(header)
    # write file
    with open(outputFile, 'w') as f:
        for line in output:
            line = line.rstrip()
            if not line.startswith("#COUNTER") \
               and not line.startswith("#FILENAME") \
               and not line.startswith("#EOL"):
                print(line, end = eol, file = f)

    output_files[templateID] = outputFile

    print("Output file written:", outputFile)
    print("Hash sum:", hashobj.getCRC32())
    print("--- %s %.1f seconds ---\n" % (tagged_templateID, time.time() - start_time))


def get_repository(device, link_name):
    repo = None

    for repo_link in filter(lambda x: x.name() == link_name, device.externalLinks(convert = False)):
        if repo is None or not repo_link.is_perdevtype():
            repo = repo_link.uri()

    return repo


def processDevice(deviceName, plc, templateIDs):
    assert isinstance(deviceName,  str)
    assert plc is None or isinstance(plc, PLC)
    assert isinstance(templateIDs, list)

    try:
        print("Obtaining controls tree for {}...".format(deviceName), end = '', flush = True)
    except TypeError:
        print("Obtaining controls tree for {}...".format(deviceName), end = '')
        sys.stdout.flush()

    try:#should come from prject  .json file not ccdb anymore
        print("aqui!")
        device = glob.ccdb.device(deviceName)
        #device = {'id': '302596', 'nameId': 'af564417-4e68-41b3-8372-a0a36f487737', 'name': 'LabS-ICS:Cryo-PLC-163', 'slotType': 'SLOT', 'parents': [{'id': '30Id': None, 'name': 'CWU', 'label': None}], 'children': None, 'powers': None, 'poweredBy': None, 'controls': [{'id': '302636', 'nameId': 'd86a6cde-6a99-4f33-9ac8-6cd18727d090', 'name': 'LabV-090', 'label': None}, {'id': '312455', 'nameId': '978f8844-6b19-487f-a9b7-f54c4a761fa6', 'name': 'LabS-ICS:Cryo-PT-163', 'label': None}, {'id': '326015', 'nameId': 'fc2fec36-f666-4e5d-bfb3d', 'name': 'LabS-ICS:Cryo-LT-163', 'label': None}], 'controlledBy': [{'id': '302627', 'nameId': '5b40dbf3-43f1-4977-b642-11026e52eb2d', 'name': 'LabS-ICS:SC-IOC-163', 'label': None}], ': 'PLC to test some logic and functions to Cryogenic work group', 'artifacts': [{'id': None, 'name': 'EPI[CMS_GLOBAL]', 'description': 'PLC internal control PVs', 'uri': 'https://gitlab.eshwi/ics_library_definitions', 'kind': 'SLOT', 'type': 'URI'}], 'deviceType': 'PLC', 'properties': [{'name': 'PLCF#PLC-EPICS-COMMS: DiagConnectionID', 'value': '254', 'dataType': 'Integer',e, 'kind': 'SLOT'}, {'name': 'PLCF#PLC-EPICS-COMMS: DiagPort', 'value': '2001', 'dataType': 'Integer', 'unit': None, 'kind': 'SLOT'}, {'name': 'EPICSModule', 'value': 'null', 'dataType': '', 'unit': None, 'kind': 'SLOT'}, {'name': 'EPICSSnippet', 'value': 'null', 'dataType': 'Strings List', 'unit': None, 'kind': 'SLOT'}, {'name': 'PLCF#PLC-EPICS-COMMS:Endianness', 'value':  'dataType': 'Endianness', 'unit': None, 'kind': 'SLOT'}, {'name': 'PLCF#PLC-DIAG:Max-Modules-In-IO-Device', 'value': '60', 'dataType': 'Integer', 'unit': None, 'kind': 'SLOT'}, {'name': 'G:Max-IO-Devices', 'value': '20', 'dataType': 'Integer', 'unit': None, 'kind': 'SLOT'}, {'name': 'PLCF#EPICSToPLCDataBlockStartOffset', 'value': '0', 'dataType': 'Integer', 'unit': None, ''}, {'name': 'PLCF#PLCToEPICSDataBlockStartOffset', 'value': '0', 'dataType': 'Integer', 'unit': None, 'kind': 'SLOT'}, {'name': 'PLCF#PLC-EPICS-COMMS: MBConnectionID', 'value': '255', 'dateger', 'unit': None, 'kind': 'SLOT'}, {'name': 'PLCF#PLC-EPICS-COMMS: MBPort', 'value': '502', 'dataType': 'Integer', 'unit': None, 'kind': 'SLOT'}, {'name': 'PLCF#PLC-EPICS-COMMS: S7Connvalue': '256', 'dataType': 'Integer', 'unit': None, 'kind': 'SLOT'}, {'name': 'PLCF#PLC-EPICS-COMMS: S7Port', 'value': '2000', 'dataType': 'Integer', 'unit': None, 'kind': 'SLOT'}, {'name'EPICS-COMMS: PLCPulse', 'value': 'Pulse_200ms', 'dataType': 'PLCPulse', 'unit': None, 'kind': 'SLOT'}, {'name': 'PLCF#PLC-DIAG:Max-Local-Modules', 'value': '60', 'dataType': 'Integer', 'unkind': 'SLOT'}, {'name': 'PLC-EPICS-COMMS: GatewayDatablock', 'value': 'null', 'dataType': 'String', 'unit': None, 'kind': 'SLOT'}, {'name': 'Hostname', 'value': 'cryo-test-plc163.cslab.esdataType': 'CSEntryHost', 'unit': None, 'kind': 'SLOT'}, {'name': 'PLCF#PLC-EPICS-COMMS: InterfaceID', 'value': '72', 'dataType': 'String', 'unit': None, 'kind': 'SLOT'}]}>)
        print("device.name:{}".format(device.name))
    except CC.NoSuchDeviceException:
        print("""
ERROR:
Device '{}' not found.
Please check the list of devices in CCDB, and keep
in mind that device names are case-sensitive.
Maybe you meant one of the following devices:
(Accesing CCDB, may take a few seconds...)""".format(deviceName))
        (filtered, top10) = glob.ccdb.getSimilarDeviceNames(deviceName)
        if not top10:
            print("""
No devices found.""")
        else:
            print("""
Most similar device names in CCDB {}(max. 10):""".format("in chosen slot " if filtered else ""))
            for dev in top10:
                print(dev)

        print("""
Exiting.
""")
        exit(1)

    global e3
    if e3 is True:
        e3 = E3.from_device(device)

    hash_base = ""
    if plc:
        hash_base = plc.set_plc(device)

    # create a stable list of controlled devices
    devices = device.buildControlsList(include_self = True, verbose = True)
    print("devices:{}".format(devices))
    # create a factory of CCDB
    try:
        output_files["CCDB-FACTORY"] = device.toFactory(deviceName, OUTPUT_DIR, git_tag = epi_version, script = "-".join([ deviceName, glob.timestamp ])) #?
    except CC.Exception:
        pass

    if IOC_ARGS:
        hostname = device.properties().get("Hostname", None)

        if plc and not hostname:
            hostname = plc.hostname()

        if not hostname:
            raise PLCFactoryException("Hostname of '{}' is not specified, required for IOC generation".format(device.name()))

        global ioc
        ioc = IOC(devices, args = IOC_ARGS)

    if plc:
        plc.get_ifdefs(devices)
        print(plc)
        # Returns the template IDs that have nothing to do with the PLC
        templateIDs = plc.generate_files(devices, templateIDs)

    for templateID in templateIDs:
        global hashobj
        hashobj = initializeHash(hash_base)

        processTemplateID(templateID, devices)

    if plc is None:
        cur_hash = (hashobj.getHash(), hashobj.getCRC32())
        global hashes
        hashes[device.name()] = cur_hash

    if plc:
        plc.generate_plc(OUTPUT_DIR, COMMIT_ID, VERIFY)

    return device


def create_zipfile(zipit):
    import zipfile

    if not zipit.endswith(".zip"):
        zipit += ".zip"

    zipit = helpers.sanitize_path(zipit)

    z = zipfile.ZipFile(zipit, "w", zipfile.ZIP_DEFLATED)

    tostrip = OUTPUT_DIR + os.path.sep

    def removeoutdir(path):
        try:
            return path[path.index(tostrip) + len(tostrip):]
        except:
            return path

    for f in output_files.values():
        if f is None:
            continue

        if isinstance(f, str):
            z.write(f, removeoutdir(f))
        elif isinstance(f, list):
            for ff in f:
                z.write(ff, removeoutdir(ff))
    z.close()

    print("Zipfile created:", zipit)
    return zipit


def m_copytree(src, dst):
    copied = []
    for name in os.listdir(src):
        srcname = os.path.join(src, name)
        dstname = os.path.join(dst, name)

        if os.path.isdir(srcname):
            helpers.makedirs(dstname)
            copied.extend(m_copytree(srcname, dstname))
        else:
            copied.append(dstname)
            if name == "CONFIG_MODULE":
                with open(srcname, 'r') as src_f:
                    cplcf = plcf.PLCF(None)
                    with open(dstname, 'w') as dst_f:
                        for line in cplcf.process(src_f):
                            print(line, end = '', file = dst_f)
            else:
                copy2(srcname, dstname)

    return copied


def module_dir(module):
    if 'OPC' in ifdef_params["PLC_TYPE"]:
        return os.path.join(MODULES_DIR, "opc", module)

    return os.path.join(MODULES_DIR, "s7plc", module)


class copy_helper(object):
    def __init__(self, basedir):
        super(copy_helper, self).__init__()
        self._basedir = basedir
        self._copied = []


    def __makedir(self, d):
        od = os.path.join(self._basedir, d)
        helpers.makedirs(od)

        return od


    def copied(self):
        return self._copied


    def m_cp(self, src, dest, newname):
        of = os.path.join(self.__makedir(dest), newname)
        copy2(src, of)
        self._copied.append(of)

        return of


def read_data_files():
    global hashes
    global prev_hashes

    try:
        with open(os.path.join(helpers.create_data_dir(__product__), "hashes")) as h:
            raw_hashes = h.readline()
    except:
        return

    prev_hashes = ast_literal_eval(raw_hashes)
    import copy
    for (k, v) in prev_hashes.items():
        if isinstance(v, tuple):
            hashes[k] = copy.deepcopy(v)
        else:
            hashes[k] = (None, copy.deepcopy(v))


def write_data_files():
    try:
        with open(os.path.join(helpers.create_data_dir(__product__), "hashes"), 'w') as h:
            print(str(hashes), file = h)
    except:
        print("Was not able to save data files")
        return



def obtain_previous_files():
    global previous_files

    fname = os.path.join(OUTPUT_DIR, ".previous-files")
    try:
        with open(fname, "r") as lf:
            raw_hash       = lf.readline()
            previous_files = ast_literal_eval(raw_hash)
    except:
        return


def create_previous_files():
    fname = os.path.join(OUTPUT_DIR, ".previous-files")
    with open(fname, 'w') as lf:
        print(output_files, file = lf)
        output_files["PREVIOUS_FILES"] = fname


class PLCFactoryVerifyException(PLCFactoryException):
    def __init__(self, device, template_filename_tuple):
        self.device = device
        self.template_filename_tuple = template_filename_tuple

        message = """
THE FOLLOWING FILES WERE CHANGED:
"""
        for (template, output) in template_filename_tuple:
            message += """\t{template}:\t{filename}
""".format(template = template, filename = output)
        super(PLCFactoryVerifyException, self).__init__(message)


def verify_output(devicename, strictness, ignore):
    if strictness == 0 or (previous_files is None and strictness < 3):
        return

    # Ignore "E3" files for now; will deal with E3 later
    ignored_templates = [ "PREVIOUS_FILES", "CREATOR", "CCDB-DUMP", "E3" ]
    ignored_templates.extend(ignore.split(","))
    files_to_delete = []
    for template in ignored_templates:
        fname = previous_files.pop(template, None)
        if fname is not None and not isinstance(fname, list):
            if isinstance(fname, list):
# E3 produces lists BUT we don't want to delete those files yet until we can actually verify them
#                files_to_delete.extend(fname)
                pass
            else:
                files_to_delete.append(fname)

    def my_filecmp(f1, f2):
        if filecmp.cmp(f1, f2, shallow = 0):
            return True

        # The files are different, let's try again skipping comment lines
        comment = "#"
        if f1.endswith(".scl"):
            comment = "//"

        with open(f1, "r") as fp1, open(f2, "r") as fp2:
            while True:
                l1 = fp1.readline(1024)
                l2 = fp2.readline(1024)

                while l1 and l1.strip().startswith(comment):
                    l1 = fp1.readline()

                while l2 and l2.strip().startswith(comment):
                    l2 = fp2.readline()

                if l1 != l2:
                    return False

                if not l1:
                    return True

    # Compare files in output_files to those in previous_files
    # previous_files will contain files that are not the same
    # not_checked will contain files that are not found / not generated
    not_checked = dict()
    for (template, output) in output_files.items():
        if template in ignored_templates:
            continue

        try:
            prev = previous_files[template]
        except KeyError:
            not_checked[template] = output
            continue

        # compare prev and output
        try:
            if my_filecmp(prev, output):
                files_to_delete.append(previous_files.pop(template))
        except OSError as e:
            if e.errno == 2:
                not_checked[template] = output
                files_to_delete.append(previous_files.pop(template))
                continue
            raise

    if previous_files:
        # Save the list of files so that it is easy to delete them after checking
        fname = os.path.join(OUTPUT_DIR, ".current-files")
        # Do not delete E3 until we can verify them
        temp_output_files = dict(output_files)
        try:
            temp_output_files.pop("E3")
        except KeyError:
            pass
        with open(fname, "w") as lf:
            for n in temp_output_files.values():
                # Make sure not to include a CCDB-dump or anything from outside
                if n.startswith(OUTPUT_DIR):
                    print(n, file = lf)
        raise PLCFactoryVerifyException(devicename, previous_files.items())

    if not_checked:
        print("\n" + "=*" * 40)
        print("""
THE FOLLOWING FILES WERE NOT CHECKED:
""")
        for (template, output) in not_checked.items():
            print("\t{template}:\t{filename}".format(template = template, filename = output))
        print("\n" + "=*" * 40)

        if strictness > 1:
            # Record last update; even if strict checking was requested
            create_previous_files()

            exit(1)

    for fname in files_to_delete:
        os.remove(fname)


def record_args(root_device):
    creator = os.path.join(OUTPUT_DIR, createFilename(getPLCF(root_device), ["#FILENAME [PLCF#RAW_INSTALLATION_SLOT]-creator-[PLCF#TIMESTAMP]"]))
    with open(creator, 'w') as f:
        print("""#!/bin/sh

#Date:              {date}
#PLCFactory URL:    {url}
#PLCFactory branch: {branch}
#PLCFactory commit: {commit}
""".format(date   = '{:%Y-%m-%d %H:%M:%S}'.format(RAW_TIMESTAMP),
           url    = PLCF_URL,
           branch = PLCF_BRANCH,
           commit = COMMIT_ID), file = f)
        print(" ".join(sys.argv), file = f)
    output_files["CREATOR"] = creator


def banner():
    print(" _____  _      _____   ______         _                    ")
    print("|  __ \| |    / ____| |  ____|       | |                   ")
    print("| |__) | |   | |      | |__ __ _  ___| |_ ___  _ __ _   _  ")
    print("|  ___/| |   | |      |  __/ _` |/ __| __/ _ \| '__| | | | ")
    print("| |    | |___| |____  | | ( (_| | (__| |( (_) | |  | |_| | ")
    print("|_|    |______\_____| |_|  \__,_|\___|\__\___/|_|   \__, | ")
    print("                                                     __/ | ")
    print("European Spallation Source, Lund                    |___/ \n")

    taint_message()



class PLCFArgumentError(PLCFactoryException):
    def __init__(self, status, message = None):
        if message is None:
            if isinstance(status, str):
                message = status
                status = 1
        super(PLCFArgumentError, self).__init__(message)
        self.status = status



class PLCFArgumentParser(argparse.ArgumentParser):
    def __init__(self):
        argparse.ArgumentParser.__init__(self)


    def exit(self, status = 0, message = None):
        raise PLCFArgumentError(status, message)



def main(argv):
    def not_empty_string(argument):
        if argument == "":
            raise argparse.ArgumentTypeError("empty string not allowed")
        return argument

    def add_common_parser_args(parser):
        #
        # -d/--device cannot be added to the common args, because it is not a required option in the first pass but a required one in the second pass
        #
        PLC.add_parser_args(parser)

        parser.add_argument(
                            '--list-templates',
                            help    = "give a list of the possible templates that can be generated on-the-fly from an Interface Definition",
                            action  = "store_true"
                           )

        parser.add_argument(
                            '--enable-experimental',
                            dest    = 'experimental',
                            help    = 'enable experimental features',
                            action  = "store_true"
                           )

        parser.add_argument(
                            '--enable-python3',
                            dest    = 'python3',
                            help    = 'enable experimental Python-3 support',
                            action  = "store_true"
                           )

        return parser


    def add_e3_ioc_arg(parser):
        IOC.add_parser_args(parser)
        E3.add_parser_args(parser)

        return parser


    if git.check_for_updates(helpers.create_data_dir(__product__), "PLC Factory"):
        return

    parser = argparse.ArgumentParser(add_help = False)

    add_common_parser_args(parser)

    parser.add_argument(
                        '-d',
                        '--device',
                        help     = 'device / installation slot',
                        const    = None
                       )

    # First pass
    #  get the device
    args   = parser.parse_known_args(argv)[0]
    device = args.device

    if not args.python3 and sys.version_info.major != 2:
        raise RuntimeError("""
PLCFactory supports Python-2.x only. Try running with the '--enable-python3' option.
Your Python version is {}
""".format(sys.version))

    if args.list_templates:
        print(tf.available_printers())
        return

    plc = PLC.parse_args(args)

    # Second pass
    #  get E3 and IOC
    add_e3_ioc_arg(parser)

    args = parser.parse_known_args(argv)[0]

    global IOC_ARGS
    IOC_ARGS = IOC.parse_args(args)

    global e3
    e3 = E3.parse_args(args)

    # Third pass
    #  get all options
    parser         = PLCFArgumentParser()

    add_common_parser_args(parser)
    add_e3_ioc_arg(parser)

    parser.add_argument(
                        '-d',
                        '--device',
                        help     = 'device / installation slot',
                        required = True
                       )

    parser.add_argument(
                        '--zip',
                        dest    = "zipit",
                        help    = 'create a zipfile containing the generated files',
                        metavar = "zipfile-name",
                        nargs   = "?",
                        type    = str,
                        const   = device
                       )

    parser.add_argument(
                        '--root',
                        help    = 'use this prefix instead of the device / installation slot',
                        metavar = "root-installation-slot",
                        type    = str
                       )

    CC.addArgs(parser)

    parser.add_argument(
                        '--verify',
                        help     = 'verify that the contents of the generated files did not change from the last run',
                        metavar  = "strictness",
                        type     = int,
                        const    = 1,
                        nargs    = '?')

    parser.add_argument(
                        '--verify-ignore',
                        help     = 'ignore the specified templates while verifying. Comma separated list',
                        type     = str,
                        default  = "")

    parser.add_argument(
                        '--tag',
                        help     = 'tag to use if more than one matching artifact is found',
                        type     = not_empty_string)

    parser.add_argument(
                        '--epi-version',
                        help     = "'EPI VERSION' to use. Overrides any 'EPI VERSION' property set in CCDB",
                        type     = not_empty_string)

    parser.add_argument(
                        '-t',
                        '--template',
                        help     = 'template name',
                        nargs    = '+',
                        type     = str,
                        default  = [],
                        required = not (plc or e3))
    

    global OUTPUT_DIR
    parser.add_argument(
                        '--output',
                        dest     = 'output_dir',
                        help     = 'the output directory. Default: {}/'.format(OUTPUT_DIR),
                        type     = str,
                        default  = OUTPUT_DIR)

    # retrieve parameters
    args = parser.parse_args(argv)

    start_time = time.time()

    global RAW_TIMESTAMP
    RAW_TIMESTAMP = datetime.datetime.now()
    if args.root is not None:
        glob.root_installation_slot = args.root
    else:
        glob.root_installation_slot = device

    ifdef_params["ROOT_INSTALLATION_SLOT"] = glob.root_installation_slot

    global VERIFY
    VERIFY = args.verify
    glob.raw_timestamp = RAW_TIMESTAMP if not VERIFY else datetime.datetime(2022, 1, 1)
    glob.timestamp = '{:%Y%m%d%H%M%S}'.format(RAW_TIMESTAMP)
    glob.commit_id = COMMIT_ID if not VERIFY else "N/A"
    glob.branch = PLCF_BRANCH if not VERIFY else "N/A"
    glob.cmdline = " ".join(sys.argv) if not VERIFY else "N/A"
    glob.origin = git.get_origin()
    glob.modversion = args.ioc
    glob.default_modversion = glob.timestamp if not VERIFY else "N/A"

    global device_tag
    device_tag = args.tag
    global epi_version
    epi_version = args.epi_version

    default_printers = set(["DEVICE-LIST"])

    ifdef_params["EXPERIMENTAL"] = args.experimental

    if plc:
        plc.update_default_printers(default_printers)
        ifdef_params["PLC_TYPE"] = plc.type()
        ifdef_params["PLC_READONLY"] = plc.is_readonly()
        ifdef_params["PLC_HOSTNAME"] = plc.hostname()

    elif e3:
        raise PLCFArgumentError("Generating an E3 module is only supported with PLC integration")

    if e3 or (IOC_ARGS and plc):
        default_printers.update( [ "EPICS-DB", "EPICS-TEST-DB", "IOCSH", "TEST-IOCSH", "BEAST", "BEAST-TEMPLATE", ] )

    if default_printers:
        if not default_printers <= set(tf.available_printers()):
            raise PLCFArgumentError("Your PLCFactory does not support generating the following necessary templates: {}".format(list(default_printers - set(tf.available_printers()))))

        templateIDs = default_printers | set(args.template)
    else:
        templateIDs = set(args.template)

    if plc and plc.is_opc() and "OPC-MAP.XLS" in tf.available_printers():
        templateIDs.update( [ "OPC-MAP.XLS" ] )

    if "EPICS-DB" in templateIDs and plc and plc.is_opc():
        templateIDs.add("EPICS-OPC-DB")
        templateIDs.remove("EPICS-DB")

    if args.output_dir[0] == '+':
        OUTPUT_DIR = os.path.join(OUTPUT_DIR, args.output_dir[1:])
    elif args.output_dir[-1] == '+':
        OUTPUT_DIR = os.path.join(args.output_dir[:-1], helpers.sanitizeFilename(device.lower()))
    elif args.output_dir == OUTPUT_DIR:
        OUTPUT_DIR = os.path.join(args.output_dir, helpers.sanitizeFilename(device.lower()))
    else:
        OUTPUT_DIR = args.output_dir

    if device_tag:
        OUTPUT_DIR = os.path.join(OUTPUT_DIR, helpers.sanitizeFilename(CC.TAG_SEPARATOR.join([ "", "tag", device_tag ])))

    OUTPUT_DIR = os.path.abspath(OUTPUT_DIR)

    os.system('cls' if os.name == 'nt' else 'clear')

    banner()

    glob.ccdb = CC.open_from_args(args)
    #print(glob.ccdb)
    helpers.makedirs(OUTPUT_DIR)

    read_data_files()
    if VERIFY:
        obtain_previous_files()
        # Remove commit-id when verifying
        ifdef_params.pop("COMMIT_ID", COMMIT_ID)
        # Remove plcfactory status when verifying
        ifdef_params.pop("PLCF_STATUS", 0)
    print(device)
    print(plc)
    print(templateIDs)
    root_device = processDevice(device, plc, list(templateIDs))
    
    # record the arguments used to run this instance
    record_args(root_device)

    # create a dump of CCDB
    output_files["CCDB-DUMP"] = glob.ccdb.save("-".join([ device, glob.timestamp ]), OUTPUT_DIR)

    if plc and e3:
        e3.create()
    if ioc is not None:
        ioc.create(args.ioc)

    # Verify created files: they should be the same as the ones from the last run
    if VERIFY:
        verify_output(root_device.name(), VERIFY, args.verify_ignore)

    create_previous_files()
    write_data_files()

    if args.zipit is not None:
        create_zipfile(args.zipit)

    has_warns = False
    for ifdef in ifdefs.values():
        if ifdef is None:
            continue

        for warn in ifdef.warnings():
            if not has_warns:
                has_warns = True
                print("\nThe following warnings were detected:\n", file = sys.stderr)
            print(warn, file = sys.stderr)

    if not args.clear_ccdb_cache:
        print("\nTemplates were reused\n")

    try:
        if prev_hashes is not None and prev_hashes[root_device.name()][1] != hashes[root_device.name()][1]:
            print("""
+++++++++++++++++++++++++++++++++++++++++++++++++++++
+ Be aware:                                         +
+	Our records show that the hash has changed. +
+++++++++++++++++++++++++++++++++++++++++++++++++++++
""")
    except KeyError:
        pass

    print("--- %.1f seconds ---" % (time.time() - start_time))

    if not taint_message():
        # As requested by Miklos :)
        print("---  ✨ 🍰 ✨ \n")
    else:
        print("--- No cake for you!\n")




if __name__ == "__main__":
    try:
        main(sys.argv[1:])
    except PLCFactoryException as e:
        if e.status:
            print(e, file = sys.stderr)
        exit(e.status)
