#!/usr/bin/env python
import sys
import json
import getpass
import requests
import ConfigParser
import argparse
import copy

defaults = {
    # "org": "bu-ist",
    "name": "irc",
    "events": [
        "push"
    ],
    "config": {     # hook defaults
        "branch_regexes": "",
        "nick": "GitHubBot",
        "password": "",
        "long_url": "0",
        "no_colors": "1",
        "room": "#cms",
        "server": "malahide.bu.edu",
        "port": "7000",
        "active": "1",
    }
}

# command line args
parser = argparse.ArgumentParser(description='Sets IRC settings to repositories using supplied config.ini')
parser.add_argument('--username', default=getpass.getuser(), help='github.com username')
# parser.add_argument('--org', default=defaults['org'], help='github.com organization account name')
parser.add_argument('--config', default='config.ini', help='config that overrides the settings in defaults["config"]')
parser.add_argument('--force', default=False, help='force update all the repos')
args = parser.parse_args()

password = getpass.getpass("Enter github.com password for '%s': " % (args.username,))

# config overrides the settings in defaults['config'] for each repo
config = ConfigParser.SafeConfigParser()
config.read(args.config)

auth = requests.auth.HTTPBasicAuth(args.username, password)

for repo_name in config.sections():

    repo_api = 'https://api.github.com/repos/%s' % (repo_name,)
    r = requests.get(repo_api, auth=auth)

    print "\nRepo: " + repo_name

    repo = json.loads(r.text or r.content)
    if 'message' in repo:
        # Bad credentials, Not Found, etc
        print '- %s' % (repo['message'],)
        if repo['message'] == 'Bad credentials':
            sys.exit()
        else:
            continue

    name = repo['name']
    hurl = repo['hooks_url']

    hook_config = copy.deepcopy(defaults)
    hook_config['config'].update(dict(config.items(repo_name)))

    ## Prompt
    inp = raw_input("Add hooks? [Y / n / [a]ll / [q]uit ] ")
    if inp == "q" or inp == "quit":
        sys.exit(0)
    if inp == "a" or inp == "all":
        doall = True
    else:
        if not (inp == "" or inp == "y" or inp == "Y"):
            continue

    ## Get all existing hooks
    hs = requests.get(hurl, auth=auth)
    if not r.ok:
        print "- Failed to get hooks: ", name
        continue
    hooks = json.loads(hs.text or hs.content)

    ## Look for existing hooks that matches this one
    found = False
    for remote_hook in hooks:
        if remote_hook['name'] != defaults['name']:
            continue

        if remote_hook['config']['room'] == hook_config['config']['room'] \
            and remote_hook['config']['server'] == hook_config['config']['server'] \
            and remote_hook['active'] == bool(int(hook_config['config']['active'])):
            found = True
            break

    ## Setup hook, if matching one not found
    if not found or args.force:

        if not found:
            print '- Remote %s hook does not match our configuration.' % (hook_config['name'],)
        elif args.force:
            print '- %s force update' % (hook_config['name'],)

        # active flag is one level above for saving purposes
        hook_config['active'] = bool(int(hook_config['config']['active']))
        hook_config['config'].pop('active')

        headers = {'Content-type': 'application/json'}
        k = requests.post(hurl, auth=auth, data=json.dumps(hook_config), headers=headers)
        print "- Response:"
        print k.text or p.content

        if k.ok:
            print "- Hook set"
        else:
            print "- Failed to set hook"
    else:
        print '- %s already exists' % (hook_config['name'],)
