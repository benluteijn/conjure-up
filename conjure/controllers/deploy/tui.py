import sys
from functools import partial

from conjure import controllers
from conjure import utils

from conjure.app_config import app
from conjure import juju

from .common import get_bundleinfo, get_metadata_controller


this = sys.modules[__name__]
this.bundle_filename = None
this.bundle = None
this.services = []


def __handle_exception(tag, exc):
    utils.error("Error deploying services: {}".format(exc))
    sys.exit(1)


def finish():
    """ handles deployment

    """
    this.bundle_filename, this.bundle, this.services = get_bundleinfo()
    app.metadata_controller = get_metadata_controller(this.bundle,
                                                      this.bundle_filename)

    for service in this.services:
        juju.deploy_service(service, utils.info,
                            partial(__handle_exception, "ED"))

    f = juju.set_relations(this.services,
                           utils.info,
                           partial(__handle_exception, "ED"))

    utils.pollinate(app.session_id, 'PC')
    controllers.use('deploystatus').render(f)


def render():
    finish()
