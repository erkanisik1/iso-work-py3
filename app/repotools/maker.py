#!/usr/bin/python3
# -*- coding: utf-8 -*-

from app.repotools.repo_ops import make_repos, check_repo_files
from app.repotools.image_ops import make_image, squash_image
from app.repotools.iso_ops import make_iso

# Backward compatibility or central entry points
def maker(command, project_name):
    from app.repotools.project import Project
    project = Project()
    err = project.open(project_name)
    if err:
        print("ERROR: %s" % err)
        return
    
    if command == "make-repo":
        make_repos(project)
    elif command == "check-repo":
        check_repo_files(project)
    elif command == "make-live":
        make_image(project)
    elif command == "pack-live":
        squash_image(project)
    elif command == "make-iso":
        make_iso(project)
    else:
        print("Unknown command: %s" % command)
