#!/usr/bin/env python

import sys
import os
import re
import GnuPGInterface
import getpass

# sudo apt-get install python-gnupginterface

__version__ = "0.1"

gnupg = GnuPGInterface.GnuPG()
gnupg.options.armor = 1
gnupg.options.meta_interactive = 0
gnupg.options.extra_args.append('--no-secmem-warning')

pwd = re.compile("[Pp]assword")
color = False

def read_db(pwddb):
    try:
        f = open(pwddb)
    except IOError:
        print >>sys.stderr, "Cannot open", pwddb
        sys.exit(1)

    proc = gnupg.run(['--decrypt'], create_fhs=['stdout', 'passphrase'], attach_fhs={'stdin': f})

    pwd = getpass.getpass("GPG Password:")
    proc.handles['passphrase'].write(pwd)
    proc.handles['passphrase'].close()

    cleartext = proc.handles['stdout'].read()
    proc.handles['stdout'].close()
    proc.wait()
    f.close()

    #return cleartext.strip()
    return cleartext

def write_db(pwddb, keyid, cleartext):
    try:
        f = open(pwddb, 'w')
    except IOError:
        print >>sys.stderr, "Cannot open", pwddb
        sys.exit(1)

    gnupg.options.recipients = [keyid]

    proc = gnupg.run(['--encrypt'], create_fhs=['stdin'], attach_fhs={'stdout': f})

    proc.handles['stdin'].write(cleartext)
    proc.handles['stdin'].close()

    proc.wait()
    f.close()
    print "Successfully wrote encrypted database"

def find(text, regex):

    p = re.compile(regex)

    first = True
    for line in text:
        if first: 
            captions = line.strip().split('\t')
            first = False
        else:
            if p.search(line):
                print
                entry = line.strip().split('\t')
                for i, cap in enumerate(captions):
                    if color:
                        if pwd.match(cap): 
                            print cap.ljust(23), ":", "\033[0;31;41m%s\033[m" % entry[i]
                        else:
                            print cap.ljust(23), ":", "\033[1m%s\033[m" % entry[i]
                    else:
                        print cap.ljust(23), ":", entry[i]


def main():
    global color
    from optparse import OptionParser
    
    parser = OptionParser(usage="%prog "+"[options] "+"[regex]...", version="%prog "+__version__)
    parser.add_option("-c", "--color",
                      action="store_true", dest="use_colors",
                      help="use colors for output")
    parser.add_option("-d", "--dump",
                      action="store_true", dest="dump_db",
                      help="dump database to plain text")
    parser.add_option("-i", "--init",
                      action="store_true", dest="init_db",
                      help="initialize/create new database")
    parser.add_option("-f", "--file", dest="pwddb",
                      metavar="FILE", help="use FILE as password database")
    parser.add_option("-t", "--text", dest="cleartextdb",
                      metavar="FILE", help="generate password database from cleartext file")
    parser.add_option("-k", "--key", dest="keyid", help="specify gpg key")
    parser.add_option("-a", "--add", action="store_true", dest="add", help="add entry")

    (options, args) = parser.parse_args()

    pwddb = options.pwddb if options.pwddb else False
    keyid = options.keyid if options.keyid else False
    color = True if options.use_colors else False
    dump = True if options.dump_db else False
    init = True if options.init_db else False
    add = True if options.add else False
    importfile = options.cleartextdb if options.cleartextdb else False


    # simple config parser
    default_config = os.getenv("HOME")+"/.pwm.conf"
    if not os.path.exists(default_config): # writing defaults
        try:
            fh = open(default_config, 'w')
        except IOError:
            print >>sys.stderr, "Cannot open", default_config
            sys.exit(1)

        print "Creating default config in:", default_config
        print "Please edit values in", default_config
        print "Additional help/hints can be found in the config file"
        fh.write("KEYID=123456\n")
        fh.write("PWDFILE=%s/.pwmdb.gpg\n" % os.getenv("HOME"))
        fh.write("COLOR=False\n")
        help = "# Hint: vim can edit .gpg files with the plugin from:\n"
        help += "# http://www.vim.org/scripts/script.php?script_id=661"
        fh.write(help)
        fh.close
        sys.exit(1)
    else: # parsing values, commandline options overwrite them
        for line in open(default_config):
            if line.startswith("KEYID") and not keyid:
                keyid = line.strip().split('=')[-1]
            if line.startswith("PWDFILE") and not pwddb:
                pwddb = line.strip().split('=')[-1]
            if line.startswith("COLOR") and not color:
                color = line.strip().split('=')[-1]
                color = True if color == "True" else False

    cmndlineoptions = add or dump or init or importfile
    if len(args) == 0 and not cmndlineoptions:
        print >>sys.stderr, "Specify at least one regex"
        sys.exit(1)

    if dump:
        cleartext = read_db(pwddb)
        print cleartext,
        sys.exit(0)

    if importfile:
        try:
            fh = open(importfile)
            cleartext = fh.read()
            fh.close()
        except IOError:
            print >>sys.stderr, "Cannot open", importfile
            sys.exit(1)
        write_db(pwddb, keyid, cleartext)
        sys.exit(0)

    if add and init: add = False # init wins
    if add or init:
        if add:
            cleartext = read_db(pwddb)
            text = "data"
        if init:
            cleartext = ""
            text = "columns"

        print "\nInput your %s (separated by <Tab>):" % text

        if add: print cleartext.split('\n')[0]

        input = raw_input()
        cleartext += input + '\n'

        write_db(pwddb, keyid, cleartext)
        sys.exit(0)


    #find regex in DB
    cleartext = read_db(pwddb)
    text_splitted = cleartext.split('\n')

    for regex in args:
        find(text_splitted, regex)

if __name__ == "__main__":
    main()

