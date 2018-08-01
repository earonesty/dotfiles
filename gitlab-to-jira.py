import gitlab
from jira import JIRA

from pathlib import Path
import json
import logging
import re
import os
import sys

import codecs
sys.stdout = codecs.getwriter("utf-8")(sys.stdout.detach())

logging.basicConfig()
log = logging.getLogger()

def get_cfg(api):
    path = "~/." + api + "-api.cfg"
    config = Path(path).expanduser()
    config = json.load(open(config))
    return config

def get_gl():
    config = get_cfg("gitlab")

    privtok = config["token"]
    url = config["url"]
    debug = config.get("debug", False)

    if (debug):
        gl_enable_debug()

    gl = gitlab.Gitlab(url, private_token=privtok, api_version=4)
    gl.auth()

    return gl

jira_email_to_user = {}
jira_sprint_list = []
def get_jira():
    config = get_cfg("jira")

    url = config["url"]
    user = config["username"]
    pwd = config["password"]

    jira = JIRA(url, auth=(user, pwd))

    for board in jira.boards():
        for sprint in jira.sprints(board.id):
            jira_sprint_list.append(sprint)

    for group in jira.groups():        
        for ent in jira.group_members(group):
            jira_email_to_user[jira.user(ent).emailAddress]=ent

    return jira

project_cache={}
def gl_get_project(gl, id):
    if id not in project_cache:
        project_cache[id] = gl.projects.get(id)
    return project_cache[id]

user_map = {
    "earthman" : "michael@codenamevida.com",
    "earthman1" : "michael@codenamevida.com",
    "earonesty" : "erik@getvida.io",
    "vida-jenkins" : "erik@getvida.io",
    "gallancy" : "daniel@codenamevida.com",
    "rgaiken" : "ross@codenamevida.com",
    "lithiumflower" : "oren@codenamevida.com",
    "oren_" : "oren@codenamevida.com",
    "colatkinson" : "colin@codenamevida.com",
    "higleyc" : "chris@codenamevida.com",
    "alexanderpinkerton" : "alexander@codenamevida.com",
    "stefanlenoach" : "stefan@codenamevida.com",
    "ianianian" : "ian@codenamevida.com",
    "ianjs" : "ian@codenamevida.com",
    "dniceci" : "dimitri@codenamevida.com",
    "mfwic212" : "dimitri@codenamevida.com",
    "girishchandrasekar" : "",
    "mcelrath" : "",
    "thetylerwolf" : "",
    "jfiscella" : "",
}

component_map = [
        ('Accessibility', []),
        ('Active Directory', ['sharing']),
        ('Bluetooth', []),
        ('Build Process', ['jenkins', 'gitlab ci', 'gitlab runner', 'package', 'install']),
        ('Cloud Storage', ['dropbox', 'google drive']),
        ('Encrypted Search', ['indexer']),
        ('External Files', [' .vida ']),
        ('File Migration', ['migration']),
        ('FUSE',['file system']),
        ('GUI',['dialog', 'qml', 'desktop']),
        ('Mofnop',[]),
        ('Onboarding',[]),
        ('Password Manager',[]),
        ('Redistribution',['redist']),
        ('Relay Server',['cryptvfs-server']),
        ('VSSS',['vss', 'ecies']),
        ('WAR Files',['vida file', 'vidafile', 'varfile']),   
        ('Mobile App',['android', 'ios', 'mobile']),
]

def gl_to_jira_user(a):
    a = a.lower()
    if a not in user_map:
#        print("NO MAP FOR", a)
        return ""

    email = user_map[a]
    if not email:
        return ""

    user = jira_email_to_user[email] 
    return user

json_projects = {}
def gl_to_jira(proj, issue, jira):
    summary = issue.title
    description = issue.description or ""
    if not description and not summary:
        print(issue)
        raise

    # make sure utf8 works
    description = description.encode("utf8").decode("utf8")

    m = re.search(r"Created by: ([^*]+)\*",description)

    author = None
    if m:
        author = m[1]
        description = re.sub(r".*?Created by: ([^*]+)\*[^\n]*\n", "", description)

    author = author or issue.author["username"]
    reporter = gl_to_jira_user(author)

    if reporter == "":
        # delibarately ignored
        return

    assignee = None
    watchers = []

    for a in issue.assignees:
        a = gl_to_jira_user(a["username"])
        if not assignee:
            assignee = a
        else:
            watchers.append(a)

    status = None
    version = None

    if issue.state.lower() == "closed":
        status = "Done"

    project_key = "VFM"
    issuetype = "Story"

    if proj.name == "UI-UX":
        project_key = "UU"

    #print(status, proj.name, project_key)

    sprint = None
    if issue.milestone:
        milestone = issue.milestone["title"].lower()
        m = re.search(r"sprint (\d+)", milestone, re.I)
        if m:
            sprintnum = m[1]

            for s in jira_sprint_list:
                if (" " + sprintnum) in s.name:
                    sprint = s.id

            if int(sprintnum) < 29:
                sprint = None
            elif not sprint:
                raise Exception("Can't find sprint " + sprintnum)
   
    labels = []
    for l in issue.labels:
        label = l.lower()

        if label == 'opsec':
            project_key = "OP"
            continue

        if label == 'epic':
            return

        if label == 'assigned':
            status = "Assigned"
            continue

        if label == 'big b beta':
            version = "Big B Beta"
            continue

        if label == 'in progress':
            status = "In Progress"
            continue

        if label == 'qa' or label == "review":
            status = "QA"
            continue

        if label == 'bug':
            issuetype = "Bug"
            continue

        final = l.replace(" ","-")
        labels.append(final)

    components = set()
    for ent in component_map:
        component = ent[0]
        aliases = ent[1]
        aliases.append(component.lower())

        for alias in aliases:
            if alias in summary.lower():
                components.add(component)
                break
            elif alias in description.lower():
                components.add(component)
                break

    components = [{"name":c} for c in components]

    if project_key != 'VFM':
        components = []

    if status is None:
        if assignee:
            status = "Assigned"
        else:
            status = "New Issues"

    if project_key == "VFM":
        if status == "Done":
            status = "Closed"



################ DELETE ISSUE FROM GITLAB

    find_issue = jira.search_issues('project=' + project_key + " and summary ~ '" + tmp + "'")
    if len(find_issue) == 0:
        print("ERROR, NOT FOUND", tmp)
        return

    if len(find_issue) != 1:
        print("ERROR, NOT UNIQUE", tmp)
        return

    issue.delete()

################ FIX VERSION & SPRINT ASSIGNMENT
    if version or sprint:
        tmp = summary
        tmp = tmp.replace("'","\\'")
        tmp = tmp.replace('"'," ")
        tmp = tmp.replace(":"," ")
        tmp = tmp.replace("+"," ")
        tmp = tmp.replace("("," ")
        tmp = tmp.replace(")"," ")

        find_issue = jira.search_issues('project=' + project_key + " and summary ~ '" + tmp + "'")

        if len(find_issue) == 0:
            print("ERROR, NOT FOUND", tmp)
            return

        if len(find_issue) != 1:
            print("ERROR, NOT UNIQUE", tmp)
            return
        found = find_issue[0]


        if version:
            found.update(fields={'fixVersions': [{"name":version}]}) 

        if sprint:
            try:
                found.update(fields={'customfield_10018': sprint}) 
            except:
                pass
    return

############# USES JSON IMPORTER INSTEAD
    issue_dict = {
        'summary': summary,
        'status' : status,
        'created' : issue.created_at,
        'labels': labels,
        'reporter': reporter,
        'description': description,
        'components': components,
        'issuetype': issuetype,
        'watchers': watchers,
        'assignee': assignee,
    }
    if status == "Done" or status == "Closed":
        issue_dict['resolution'] = 'Resolved'

    if assignee:
        issue_dict['assignee'] = assignee

    if version:
        issue_dict['fixVersions'] = [version]

    if sprint:
        issue_dict['sprint']= sprint

    if project_key not in json_projects:
        json_projects[project_key] = []

    json_projects[project_key].append(issue_dict)


    return

############# USES JIRA API BELOW
    issue_dict = {
        'project': {'key': project_key},
        'summary': summary,
        'labels': labels,
        'reporter': {'name' : reporter},
        'description': description,
        'components': components,
        'issuetype': {'name': issuetype},
        'customfield_10025': str(issue.created_at),
    }

    if assignee:
        issue_dict['assignee'] = {'name' : assignee}

    if version:
        issue_dict['fixVersions'] = [{'name': version}]

    if sprint:
        issue_dict['customfield_10018']= sprint

    try:
        new_issue = jira.create_issue(fields=issue_dict)
        try:
            for watcher in watchers:
                jira.add_watcher(new_issue.id,watcher)
        except Exception:
            new_issue.delete()
    except Exception as e:
        print(issue_dict, e)

def main():
    gl = get_gl()
    jira = get_jira()

    groups = gl.groups.list()

    for group in groups:
        next_page = 0
        issues = True
        while issues:
            next_page += 1
            issues = group.issues.list(scope="all", page=next_page)
            for issue in issues:
                project = gl_get_project(gl, issue.project_id)
                #print(project)
                #print(issue)
                gl_to_jira(project, issue, jira)

    final = {
            "projects": [ {"key":pk,"issues":issues} for pk, issues in json_projects.items() ]
            }

    print(json.dumps(final))

def gl_enable_debug():
    requests_log = logging.getLogger("requests.packages.urllib3")
    requests_log.setLevel(logging.DEBUG)
    requests_log.propagate = True
    log.setLevel(logging.DEBUG)

if __name__ == main():
    main()
