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

# modules
import helpers


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

def get_repository(device, link_name):
    repo = None

    for repo_link in filter(lambda x: x.name() == link_name, device.externalLinks(convert = False)):
        if repo is None or not repo_link.is_perdevtype():
            repo = repo_link.uri()

    return repo

def processDevice(deviceName, plc, templateIDs):
    device = device(deviceName)

    global e3
    if e3 is True:
        e3 = E3.from_device(device)
    
    # create a stable list of controlled devices
    devices = device.buildControlsList(include_self = True, verbose = True)

    if IOC_ARGS:
        hostname = device.properties().get("Hostname", None)

        if plc and not hostname:
            hostname = plc.hostname()

        if not hostname:
            raise PLCFactoryException("Hostname of '{}' is not specified, required for IOC generation".format(device.name()))

        global ioc
        ioc = IOC(devices, args = IOC_ARGS)

def main(argv):

    def add_ioc_arg(parser):
        IOC.add_parser_args(parser)

        return parser
    
    parser = argparse.ArgumentParser(add_help = False)
    add_ioc_arg(parser)
    args = parser.parse_known_args(argv)[0]
    IOC_ARGS = IOC.parse_args(args)

    global OUTPUT_DIR
    parser.add_argument(
                        '--output',
                        dest     = 'output_dir',
                        help     = 'the output directory. Default: {}/'.format(OUTPUT_DIR),
                        type     = str,
                        default  = OUTPUT_DIR)

    # retrieve parameters
    args = parser.parse_args(argv)

    if ioc is not None:
        ioc.create(args.ioc)



if __name__ == "__main__":
    try:
        main(sys.argv[1:])
    except PLCFactoryException as e:
        if e.status:
            print(e, file = sys.stderr)
        exit(e.status)