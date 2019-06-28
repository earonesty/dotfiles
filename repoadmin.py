#!/usr/bin/env python

import sys
import os
import json
import argparse
import logging


import github

log = logging.getLogger(__name__)

VALID_ACTIONS = ["delete", "list", "archive"]

CONNECT_ARGS = [ "login_or_token", "timeout", "per_page", "base_url", "password", "login", "token" ]

g = None
u = None
o = None

extra_argv = []

class RepoAdminError(Exception):
    pass

def parse_args():
    parser = argparse.ArgumentParser(description='Command line github repo admin tool')

    parser.add_argument('action', type=str,
                    help='Action to take', choices=VALID_ACTIONS)
    parser.add_argument('--debug', '-D', action="store_true", help='Debug logging')
    parser.add_argument('--organization', '-o', action="store", help='Organization name')
    parser.add_argument('--repos', '-r', action="store", help='Repository name')

    global extra_argv

    (args, extra_argv) = parser.parse_known_args()

    if args.organization:
        repo_types = ["public", "private", "forks"]
    else:
        repo_types = ["public", "private", "owner"]

    parser.add_argument('--type', action="store", help='Only repos of this type', choices=repo_types) 

    if args.action in ("delete", "archive"):
        parser.add_argument('--really', action="store_true", help='Really delete, don\'t just list what would be deleted') 

    args = parser.parse_args()

    if args.repos:
        args.repos = [e.strip() for e in args.repos.split(",") if e]

    return args

def connect(argv):
    try:
        conf = None
        conf = open(os.path.expanduser("~/.github")).read()
        data = json.loads(conf)
        argv.update(data)
    except FileNotFoundError:
        raise("Create a ~/.github file with an access_token in it")
    except ValueError:
        argv["token"] = conf

    kws={}

    lort = argv.pop("token", None)
    if not lort:
        lort = argv.pop("login", None)
    kws["login_or_token"] = lort

    for key in (CONNECT_ARGS):
        if argv.get(key):
            kws[key] = argv.pop(key)

    kws["login_or_token"] = kws["login_or_token"].strip()

    global g
    global u
    global o
    g = github.Github(**kws)

    org = argv.get("organization")
    if org:
        o = g.get_organization(org)

def get_repos(argv):
    v = argv.get("type")
    if not v:
        v = "all"

    names = set(argv.get("repos"))

    if len(names) == 1:
        name = names.pop()
        # just pull one repo
        if o:
            repo = o.get_repo(name)
        else:
            repo = u.get_repos(name)
        repos = [repo]
    else:
        if o:
            repos = o.get_repos(type=v)
        else:
            repos = u.get_repos(type=v)
        # filter by name
        repos = [r for r in repos if r.name in names]

        if len(repos) != len(names):
            for r in repos:
                names.discard(r.name)
            raise RepoAdminError("Cannot find repo %s" % (list(names),))

    return repos

def print_repos(argv):
    repos = get_repos(argv)
    for repo in repos:
        print(repo.name)

def delete_repos(argv):
    repos = get_repos(argv)

    for repo in repos:
        print("DELETE", repo.name)
        if argv.get("really"):
            repo.delete()

def archive_repos(argv):
    repos = get_repos(argv)
    for repo in repos:
        print("ARCHIVE", repo.name)
        if argv.get("really"):
            repo.edit(archived=True)

def main():
    try:
        args = parse_args()
        argv = vars(args)

        logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')

        if argv.pop("debug", False):
            log.setLevel(logging.DEBUG)

        connect(argv)

        if args.action == "list":
            print_repos(argv)

        if args.action == "delete":
            delete_repos(argv)

        if args.action == "archive":
            archive_repos(argv)
    except github.UnknownObjectException as e:
        print("Requested organization or repository was not found")
    except RepoAdminError as e:
        print(e)
        sys.exit(1)

if __name__ == "__main__":
    main()
