# PythonAnywhere WSGI configuration file.
# Paste the contents of this file into your PythonAnywhere WSGI config
# (Web tab → click the WSGI configuration file link).
#
# Replace <username> with your actual PythonAnywhere username.

import sys
import os

project_home = "/home/<username>/spx-dashboard"
if project_home not in sys.path:
    sys.path.insert(0, project_home)

# Activate virtualenv if you created one:
# activate_this = f"/home/<username>/.virtualenvs/spx-dashboard/bin/activate_this.py"
# with open(activate_this) as f:
#     exec(f.read(), {"__file__": activate_this})

from app import app as application  # noqa: E402
