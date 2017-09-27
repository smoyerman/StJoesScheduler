import os
import sys

os.environ['DJANGO_SETTINGS_MODULE'] = 'myproject.settings'

from django.core.wsgi import get_wsgi_application

"""def application(environ, start_response):
    if environ['mod_wsgi.process_group'] != '': 
        import signal
        os.kill(os.getpid(), signal.SIGINT)
    return ["killed"]"""

application = get_wsgi_application()
