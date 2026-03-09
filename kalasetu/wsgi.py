"""
WSGI config for kalasetu project.

It exposes the WSGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/6.0/howto/deployment/wsgi/
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# PythonAnywhere: load .env from project directory
project_home = Path(__file__).resolve().parent.parent
load_dotenv(project_home / '.env')

# PythonAnywhere: add project to sys.path
if str(project_home) not in sys.path:
    sys.path.insert(0, str(project_home))

from django.core.wsgi import get_wsgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'kalasetu.settings')

application = get_wsgi_application()
