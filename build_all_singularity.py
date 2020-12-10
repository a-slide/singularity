#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# Standard lib imports
import os
import sys
from glob import glob
import subprocess
import hashlib
from collections import OrderedDict
import argparse
import sys

# Generic third party imports
import yaml

__version__ = "0.0.1"
__name__ = "build_all_singularity"
__description__ = "Build, sign verify and push singurality images to Sylab cloud"


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~MAIN FUNCTION~~~~~~~~~~~~~~~~~~~~~~~~~~~~~#

def main(args=None):
    parser = argparse.ArgumentParser(description=__description__)
    parser.add_argument("--version", action="version", version="{} v{}".format(__name__, __version__))
    parser.add_argument("--user_id", "-u", default="aleg", help="Singularity library user_id (default: %(default)s)")
    parser.add_argument("--collection", "-c", default="default", help="Collection name to push to (default: %(default)s)")
    parser.add_argument("--sign", "-s", action="store_true", default=False, help="Sign and verify singularity image (default: %(default)s)")
    parser.add_argument("--push", "-p", action="store_true", default=False, help="Push to Sylab cloud (default: %(default)s)")
    parser.add_argument("--force", "-f", action="store_true", default=False, help="Force regenerated all the package (default: %(default)s)")
    args = parser.parse_args()

    recipe_md5_fn = "recipe_sha.yml"
    recipe_md5_d = ordered_load_yaml(recipe_md5_fn)

    for recipe_fn in sorted(glob("*/*.srf")):
        stdout_print(f"Evaluating recipe: {recipe_fn}")

        image_fn = recipe_fn.rstrip(".srf") + ".sif"

        with open(recipe_fn, "rb") as f:
            recipe_hash = hashlib.md5(f.read()).hexdigest()

        if args.force:
            build = True
            stdout_print("\tForced build")
        elif not os.path.isfile(image_fn):
            build = True
            stdout_print("\tNo image for current recipe")
        elif recipe_fn not in recipe_md5_d:
            build = True
            stdout_print("\tNo hash for current recipe")
        elif recipe_md5_d[recipe_fn] != recipe_hash:
            build = True
            stdout_print("\tRecipe Updated")
        else:
            build = False
            stdout_print("\tNothing to be done")

        if build:
            log_fn = recipe_fn.rstrip(".srf") + ".log"
            if os.path.isfile(log_fn):
                os.remove(log_fn)
            try:
                stdout_print("\tBuilding image")
                bash(cmd=f"singularity build --fakeroot -F {image_fn} {recipe_fn}", log_fn=log_fn)

                if args.sign:
                    stdout_print("\tSigning image")
                    bash(cmd=f"singularity sign {image_fn}", log_fn=log_fn)
                    stdout_print("\tVerifying image")
                    bash(cmd=f"singularity verify {image_fn}", log_fn=log_fn)

                if args.push:
                    stdout_print("\tUploading image to sylab Cloud")
                    c = os.path.split(recipe_fn)[-1].rstrip(".srf")
                    container_name = c.split(":")[0].lower()
                    container_tag = c.split(":")[1].lower()
                    bash(cmd=f"singularity push {image_fn} library://{args.user_id}/{args.collection}/{container_name}:{container_tag}", log_fn=log_fn)

                # Update the yaml hash file
                recipe_md5_d[recipe_fn] = recipe_hash

            except BashCommandError as E:
                stdout_print(f"Evaluating recipe: {recipe_fn}")
                stdout_print(E)

    ordered_dump_yaml(recipe_md5_d, recipe_md5_fn)


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~HELPER FUNCTIONS~~~~~~~~~~~~~~~~~~~~~~~~~~~~~#


def ordered_load_yaml(yaml_fn, Loader=yaml.Loader, **kwargs):
    """
    Ensure YAML entries are loaded in an ordered dict following the original file order
    """
    # Define custom loader
    class OrderedLoader(Loader):
        pass

    def construct_mapping(loader, node):
        loader.flatten_mapping(node)
        return OrderedDict(loader.construct_pairs(node))

    OrderedLoader.add_constructor(yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, construct_mapping)
    # Try to load file
    try:
        with open(yaml_fn, "r") as yaml_fp:
            d = yaml.load(stream=yaml_fp, Loader=OrderedLoader, **kwargs)
            return d
    except:
        return OrderedDict()


def ordered_dump_yaml(d, yaml_fn, Dumper=yaml.Dumper, **kwargs):
    """
    Ensure ordered dict items are dumped in YAML file following the dictionary order
    """
    # Define custom dumper
    class OrderedDumper(Dumper):
        pass

    def _dict_representer(dumper, data):
        return dumper.represent_mapping(yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, data.items())

    OrderedDumper.add_representer(OrderedDict, _dict_representer)

    # Try to dump dict to file
    try:
        with open(yaml_fn, "w") as yaml_fp:
            yaml.dump(data=d, stream=yaml_fp, Dumper=OrderedDumper, **kwargs)
    except:
        raise IOError("Error while trying to dump data in file: {}".format(yaml_fn))


def bash(cmd, log_fn):
    returncode = 1
    stdout_print(cmd)
    with open(log_fn, "a") as log_fp:
        with subprocess.Popen(cmd, shell=True, stdout=log_fp, stderr=log_fp, executable="bash") as p:
            returncode = p.wait()
    if returncode >= 1:
        raise BashCommandError(f"\tERROR {returncode}. See log file for more details")


def stdout_print(*args):
    s = " ".join([str(i) for i in args]) + "\n"
    sys.stdout.write(s)
    sys.stdout.flush()


def stderr_print(*args):
    s = " ".join([str(i) for i in args]) + "\n"
    sys.stderr.write(s)
    sys.stderr.flush()


class BashCommandError(Exception):
    pass


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~SCRIPT ENTRY POINT~~~~~~~~~~~~~~~~~~~~~~~~~~~~~#
main()
