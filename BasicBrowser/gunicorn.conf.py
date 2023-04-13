
# Django WSGI application path in pattern MODULE_NAME:VARIABLE_NAME
wsgi_app = "BasicBrowser.wsgi:application"
pythonpath = "/var/www/nacsos1/tmv/BasicBrowser/"
# The granularity of Error log outputs
loglevel = "debug"
# The number of worker processes for handling requests
workers = 1
# The socket to bind
bind = "0.0.0.0:8053"
# Restart workers when code changes (development only!)
reload = False
# Write access and error info to /var/log
errorlog = "/var/www/nacsos1/error.log"
accesslog = "/var/www/nacsos1/access.log"
# Redirect stdout/stderr to log file
capture_output = True
# PID file so you can easily fetch process ID
pidfile = "/var/www/nacsos1/server.pid"
# Daemonize the Gunicorn process (detach & enter background)
daemon = False
