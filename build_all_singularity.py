#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# Standard lib imports
import os
import sys
from glob import glob
import subprocess
import hashlib
from collections import OrderedDict
import time

# Generic third party imports
import yaml

#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~MAIN FUNCTION~~~~~~~~~~~~~~~~~~~~~~~~~~~~~#

def main ():

    recipe_md5_fn="recipe_sha.yml"
    recipe_md5_d = ordered_load_yaml(recipe_md5_fn)

    for recipe_fn in sorted(glob("*/*.srf")):
        stdout_print (f"Evaluating recipe: {recipe_fn}")

        image_fn = recipe_fn.rstrip(".srf")+".sif"

        with open(recipe_fn,"rb") as f:
            recipe_hash = hashlib.md5(f.read()).hexdigest()

        if not os.path.isfile(image_fn):
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
            stdout_print("\tBuilding image")
            log_fn = recipe_fn.rstrip(".srf")+".log"
            bash(cmd=f"singularity build --fakeroot -F {image_fn} {recipe_fn}", log_fn=log_fn)
            recipe_md5_d[recipe_fn] = recipe_hash

    ordered_dump_yaml(recipe_md5_d, recipe_md5_fn)

#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~HELPER FUNCTIONS~~~~~~~~~~~~~~~~~~~~~~~~~~~~~#

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

def bash (cmd, log_fn):
    with open(log_fn, "w") as log_fp:
        with subprocess.Popen (cmd, shell=True, stdout=log_fp, stderr=log_fp, executable="bash") as p:
            returncode = p.wait()
            if returncode >= 1:
                stderr_print(f"\tERROR {returncode}. See log file for mor details")

def stdout_print (*args):
    s =  " ".join([str(i) for i in args])+"\n"
    sys.stdout.write(s)
    sys.stdout.flush()

def stderr_print (*args):
    s =  " ".join([str(i) for i in args])+"\n"
    sys.stderr.write(s)
    sys.stderr.flush()

#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~SCRIPT ENTRY POINT~~~~~~~~~~~~~~~~~~~~~~~~~~~~~#

if __name__ == "__main__":
    main ()
