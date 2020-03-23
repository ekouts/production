#!/usr/bin/env python3

import logging
import os
import re
import subprocess

logging.basicConfig(
    format="%(levelname)s: %(message)s",
    level=logging.INFO,
)

METADATA_FILE = "cray_external_modules_metadata.cfg"


def natural_sort(l):
    convert = lambda text: int(text) if text.isdigit() else text.lower()
    alphanum_key = lambda key: [
        convert(c) for c in re.split("([0-9]+)", key[0] + " " + key[1])
    ]
    return sorted(l, key=alphanum_key)


def get_easybuild_path(path):
    return os.path.dirname(os.path.realpath(__file__)).split("scripts")[0] + path


def main():
    with open(get_easybuild_path(METADATA_FILE), "r") as infile:
        # Keep first three lines of comments
        comments = infile.readline() + infile.readline() + infile.readline()
        content = infile.read()

    # Example of entries:
    #
    # [cray-netcdf/4.3.2]
    # name = netCDF, netCDF-Fortran
    # version = 4.3.2, 4.3.2
    # prefix = NETCDF_DIR
    #
    # [cray-python/2.7.15.1]
    # name = Python
    # version = 2.7.15.1
    # prefix = /opt/python/2.7.15.1
    regex_entry = re.compile(
        r"\[(\S*)\/(\S*)\]\s*name\s*=\s*(.*)\s*version\s*=\s*(.*)\s*prefix\s*=\s*(\S*)"
    )
    entries = regex_entry.findall(content)
    entries = natural_sort(entries)
    logging.info("Entries in file:")
    for e in entries:
        logging.info(e)

    # It ignores slurm
    exceptions = ["slurm"]

    new_entries = []
    modules = set()

    for e in entries:
        if e[0] in modules:
            continue
        modules.add(e[0])
        cmd = subprocess.run("module avail " + e[0], stderr=subprocess.PIPE, shell=True)
        regex_available_module = re.compile(e[0] + r"\/(\S*?)(\(default\))?\s+")
        available_versions = regex_available_module.findall(cmd.stderr.decode("utf-8"))

        for v in available_versions:
            new_entry = (
                e[0],
                v[0],
                e[2],
                e[3].replace(e[1], v[0]),
                e[4].replace(e[1], v[0]),
            )
            if new_entry not in entries:
                new_entries.append(new_entry)

    actual_new_entries = [entry for entry in new_entries if entry[0] not in exceptions]

    logging.warning("Will not add:")
    for i in [temp for temp in new_entries if temp[0] in exceptions]:
        logging.warning(i)

    logging.info("New entries:")
    for entry in actual_new_entries:
        logging.info(entry)

    with open(get_easybuild_path(METADATA_FILE), "w+") as outfile:
        outfile.write(comments)
        all_entries = natural_sort(actual_new_entries + entries)
        for entry in all_entries:
            outfile.write(
                "[{}/{}]\nname = {}\nversion = {}\nprefix = {}\n\n".format(
                    entry[0], entry[1], entry[2], entry[3], entry[4]
                )
            )


if __name__ == "__main__":
    main()
