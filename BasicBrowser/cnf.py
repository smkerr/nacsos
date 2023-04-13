
# Django WSGI application path in pattern MODULE_NAME:VARIABLE_NAME
#pythonpath = "/var/www/nacsos1/tmv/BasicBrowser"
#chdir = "/var/www/nacsos1/tmv/BasicBrowser"
#application_path = "/nacsos-legacy"
#root_path= "/var/www/nacsos1/tmv/BasicBrowser"

asgi_app = "BasicBrowser.asgi:application"


# The number of worker processes for handling requests
workers = 4
# The socket to bind
bind = "0.0.0.0:8053"

# The granularity of Error log outputs
loglevel = "info"
# Redirect stdout/stderr to log file
capture_output = True
# Write access and error info to /var/log
errorlog = "/var/www/nacsos1/logs/error.log"
accesslog = "/var/www/nacsos1/logs/access.log"

# PID file so you can easily fetch process ID
pid_path = "/var/www/nacsos1/server.pid"

# Daemonize the Gunicorn process (detach & enter background)
daemon = False
# Restart workers when code changes (development only!)
reload = False

debug = False
