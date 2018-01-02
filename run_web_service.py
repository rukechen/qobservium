import logging

from qrmobservium import create_app
from qrmobservium.common import appconfig
from qrmobservium.common import logger
LOG = logger.Logger(__name__)

app = create_app(appconfig)

if __name__ == '__main__':
    app.run(host="0.0.0.0", port=appconfig.PORT, debug=appconfig.DEBUG, threaded=True, use_reloader=False)
