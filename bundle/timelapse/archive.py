#!/usr/bin/env python3
import sys
from service import Service
service=Service(sys.argv[1],recover=False)
try:
    projects=service.rows('SELECT * FROM projects WHERE id=?',(sys.argv[2],))
    if projects: service.archive(projects[0])
finally: service.close()
