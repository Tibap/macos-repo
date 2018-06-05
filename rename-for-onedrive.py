#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @author: Tibap

import sys
import os
import unicodedata
import argparse


def print_help():
    print("""Usage: python {prog_name} [onedrive_folder]
Script to check user's OneDrive folders for any\
illegal characters and to correct them to help allow smooth syncing in OneDrive.
If no argument is given, the script search for a directory named with "onedrive" \
in its name in the user directory.
Logs are saved in /tmp, with the name of the directory that has been sanitized.
""".format(prog_name=sys.argv[0]))

def getUserLoggedIn():
    """ Returns the user logged in.
    When multiple users are logged in, SCDynamicStoreCopyConsoleUser returns the
    one using the console.
    """
    from SystemConfiguration import SCDynamicStoreCopyConsoleUser

    username = (SCDynamicStoreCopyConsoleUser(None, None, None) or [None])[0]
    username = [username, ""][username in [u"loginwindow", None, u""]]
    return username

def searchOneDriveFolder(home_folder):
    """
    Search for OneDrive folder in the user directory. The search is looking for
    folder containing onedrive (combination of lower and upper cases) in their name.
    Returns a list of folders that match.
    """
    import fnmatch
    matches = []
    exclude = set(['Library', '.Trash'])
    for root, dirnames, filenames in os.walk('/Users/' + home_folder):
        dirnames[:] = [d for d in dirnames if d not in exclude]
        for dirname in fnmatch.filter(dirnames, '*[Oo][Nn][Ee][Dd][Rr][Ii][Vv][Ee]*'):
            matches.append(os.path.join(root, dirname))
            dirnames.remove(dirname) # We do not continue to walk into a onedrive folder

    return matches


def removeAccentsAndAll(name):
    try:
        name = unicode(name, 'utf-8')
    except (TypeError, NameError): # unicode is a default on python 3
        #print("TypeError or NameError for name")
        pass

    name = unicodedata.normalize('NFD', name)
    try:
        name = name.encode('ascii', 'ignore')
    except:
        name = name.decode('ascii').encode('ascii', 'ignore')

    name = name.decode("utf-8")

    return name


if __name__ == "__main__":

    parser = argparse.ArgumentParser(description="""
    Script to check user's OneDrive folders for any\
    illegal characters and to correct them to help allow smooth syncing in OneDrive.
    If no argument is given, the script search for a directory named with "onedrive" \
    in its name in the user directory.
    Logs are saved in /tmp, with the name of the directory that has been sanitized.
    """)
    parser.add_argument('-d', '--dir',
                        action='store',
                        dest='directory',
                        help='Directory to sanitize for upload')
    parser.add_argument('-f', '--force',
                        action='store_true',
                        help='Force script to remove accents and unrecognized letters')
    args = parser.parse_args()

    force = args.force
    onedrive_folders = None

    if args.directory:
        onedrive_folders = [args.directory]
        for folder in onedrive_folders:
            if not os.path.isdir(folder):
                print("[-]Path {} does not exist".format(folder))
                sys.exit(-1)

    # If we don't have any argument, we have to search for the onedrive folder
    if not onedrive_folders:
        print("Looking for onedrive folders...")

        # Get logged in user
        logged_user = getUserLoggedIn()
        print("  User logged: {}".format(logged_user))
        onedrive_folders = searchOneDriveFolder(logged_user)

    if not onedrive_folders:
        print("[-]Cannot find OneDrive folder, quitting")
        sys.exit(-1)
    print("Found OneDrive folders: {}\nBeggining to sanitize it...".format(onedrive_folders))

    forbidden_char = ['~', '"', '#', '%', '&', '*', ':', '<', '>', '?', '/', '\\', '{', '|', '}', ',']
    unauthorized_names = ['AUX', 'PRN', 'NUL', 'CON', 'COM0', 'COM1', 'COM2', 'COM3',
                          'COM4', 'COM5', 'COM6', 'COM7', 'COM8', 'COM9', 'LPT0',
                          'LPT1', 'LPT2', 'LPT3', 'LPT4', 'LPT5', 'LPT6', 'LPT7', 'LPT8', 'LPT9']

    changed_names = []
    for folder in onedrive_folders:
        outside_user_partition = False
        # Folder may be encoded in non utf8...
        try:
            folder = folder.encode('utf-8')
        except:
            print("Error thrown when trying to encode OneDrive folders name, check it out manually.")
            continue

        # Check that folder is within /Users, ask user to confirm if not
        tmp = os.path.abspath(folder)
        if tmp[:7] != "/Users/":
            outside_user_partition = True
            response = raw_input("Onedrive folder {} is not on /Users/ partition, do you want to continue? [y/n] ".format(tmp))
            if response != 'y':
                print("Quitting.")
                continue

        print("Sanitizing {} folder...".format(folder))
        for root, dirnames, filenames in os.walk(folder):

            for name in filenames + dirnames:
                original_name = name
                #original_root = root

                if force:
                    name = removeAccentsAndAll(name)
                else:
                    force_rename = False
                    # Only take UTF8 names
                    try:
                        name.decode('utf-8')
                    except:
                        print("  Found non-UTF8 name, re-encoding everything...")
                        name = name.encode('utf-8')
                        #root = root.encode('utf-8')

                # Remove trailing and ending spaces
                if name[0] == ' ':
                    print("  Trailing spaces detected, removing")
                    name = name.lstrip(' ')
                if name[-1] == ' ':
                    print("  Ending spaces detected, removing")
                    name = name.rstrip(' ')
            

                # Remove all ending points
                if name[-1:] == '.':
                    print("  Ending points detected, removing")
                    name = name.rstrip('.')

                # Remove forbidden char only if we are in blacklist mode
                if not force:
                    for char in forbidden_char:
                        name = name.replace(char, '_')

                # Remove unauthorized_names
                for unauth_name in unauthorized_names:
                    if name == unauth_name:
                        print("  Found unauthorized name: {}".format(name))
                        name = '_{}'.format(name)

                # Maximum of 255 characters for name (documentation says 260 but tests
                # show that MacOS only supports 255, so...)
                # We test for 249 characters in order to not have conflict with
                # the next while loop
                if len(name) > 249:
                    print("  Found filename which is too long ({} chars), shortening to 249 chars".format(
                          len(name)))
                    name = name[:249]

                # Remove consecutive _ to have better looking filenames
                if not outside_user_partition:
                    while '__' in name:
                        name = name.replace('__', '_')


                if original_name != name:
                    try:
                        log = "Renaming: \"{}\" -> \"{}\"".format(original_name, name)
                        print("  [i]{}".format(log))
                    except Exception as e: # if original_name is not printable, it will throw an error
                        log = "Renamed: \"{}\"".format(name)
                        print("  [i]{}".format(log))
                    changed_names.append(log)

                    # We may have a file or dir that already has this name, so
                    # find a name which is free...
                    suffix = "-Copy"
                    increment = 0
                    while os.path.exists(os.path.join(root, name)):
                        print("  Path \"{}\" already exists, suffixing with \"{}\"".format(
                                os.path.join(root, name), suffix+str(increment)))
                        name = name + suffix + str(increment)
                        increment=increment+1
                    try:
                        os.rename(os.path.join(root, original_name), os.path.join(root, name))
                    except OSError:
                        log = "ERROR - Cannot rename file {} because of permission. Check out manually.".format(root, original_name)
                        print(log)
                        changed_names.append(log)


                    # If we change a directory name, replace it in the list to parse it files
                    if os.path.isdir(os.path.join(root, name)):
                        dirnames.append(name)

        # Save logs and quit
        print("A total of {} files has been changed".format(len(changed_names)))
        log_file = '/tmp/{}-rename.log'.format(os.path.basename(folder))
        print("Writing changes in log file: {}".format(log_file))
        with open(log_file, 'wt') as f:
            f.write("Folders: \"{}\" have been sanitized.\n".format(onedrive_folders))
            if len(changed_names):
                f.write("List of renamed files is:\n")
            for change in changed_names:
                f.write(change+"\n")

    print("Finished.")
