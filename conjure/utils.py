import shutil
import os
import yaml
from termcolor import colored
from subprocess import run, check_call, CalledProcessError, DEVNULL, PIPE
from conjure.async import submit
from conjure.app_config import app
from configobj import ConfigObj


def run_script(path):
    return run(path, shell=True, stderr=PIPE, stdout=PIPE, env=app.env)


def check_bridge_exists():
    """ Checks that an LXD network bridge exists
    """
    if os.path.isfile('/etc/default/lxd-bridge'):
        cfg = ConfigObj('/etc/default/lxd-bridge')
    else:
        cfg = ConfigObj()

    ready = cfg.get('LXD_IPV4_ADDR', None)
    if not ready:
        return False
    return True


def check_deb_installed(pkg):
    """ Checks if a debian package is installed
    """
    try:
        run('dpkg-query -W {}'.format(pkg),
            shell=True, check=True, stdout=DEVNULL, stderr=DEVNULL)
    except CalledProcessError:
        return False
    return True


def info(msg):
    prefix = colored('[info]', 'green', attrs=['bold'])
    print("{} {}".format(prefix, msg))


def error(msg):
    prefix = colored('[error]', 'red', attrs=['bold'])
    print("{} {}".format(prefix, msg))


def warning(msg):
    prefix = colored('[warning]', 'yellow', attrs=['bold'])
    print("{} {}".format(prefix, msg))


def install_home():
    """ returns installer user home
    """
    return os.path.expanduser("~" + install_user())


def juju_path():
    """ returns juju path for $user
    """
    return os.getenv('JUJU_DATA',
                     os.path.expanduser('~/.local/share/juju'))


def mkdir(path):
    if not os.path.isdir(path):
        os.makedirs(path)
        chown(path, install_user(), recursive=True)


def chown(path, user, group=None, recursive=False):
    """ Change user/group ownership of file

    Arguments:
    path: path of file or directory
    user: new owner username
    group: new owner group name
    recursive: set files/dirs recursively
    """
    if group is None:
        group = user

    try:
        if not recursive or os.path.isfile(path):
            shutil.chown(path, user, group)
        else:
            for root, dirs, files in os.walk(path):
                shutil.chown(root, user, group)
                for item in dirs:
                    shutil.chown(os.path.join(root, item), user, group)
                for item in files:
                    shutil.chown(os.path.join(root, item), user, group)
    except OSError as e:
        raise e


def spew(path, data, owner=None):
    """ Writes data to path
    Arguments:
    path: path of file to write to
    data: contents to write
    owner: optional owner of file
    """
    with open(path, 'w') as f:
        f.write(data)
    if owner:
        try:
            chown(path, owner)
        except:
            raise Exception(
                "Unable to set ownership of {}".format(path))


def slurp(path):
    """ Reads data from path

    Arguments:
    path: path of file
    """
    try:
        with open(path) as f:
            return f.read().strip()
    except IOError:
        raise IOError


def install_user():
    """ returns sudo user
    """
    user = os.getenv('USER', None)
    if user is None:
        raise Exception("Unable to determine current user.")
    return user


def pollinate(session, tag):
    """ fetches random seed

    Tag definitions:
        W001 - welcome shown
        B001 - bundle selected
        CS - cloud selected
        CC - cloud creation started
        CA - cloud credentials added
        L001 - LXD Setup started
        L002 - LXD Setup completed
        J001 - juju post-bootstrap started
        J002 - juju post-bootstrap completed
        J003 - juju bootstrap started
        J004 - juju bootstrap completed
        CS - controller selected
        PM - placement/bundle editor shown (maas)
        PS - placement/bundle editor shown (other)
        PC - placements committed
        SS - deploy summary shown
        DS - deploy started
        DC - deploy complete
        XA - pre processing started
        XB - post processing started

        UC - user cancelled
        EC - error getting credentials
        EP - error in placement/bundle editor
        EB - error juju bootstrap
        ED - error deploying
        E001 - error in post bootstrap phase
        E002 - error in post processor
        E003 - error in pre processor
        E004 - error creating model in existing controller

    Arguments:
    session: randomly generated session id
    tag: custom tag
    """
    agent_str = 'conjure/{}/{}'.format(session, tag)

    def do_pollinate():
        try:
            cmd = ("curl -A {} --connect-timeout 3 --max-time 3 "
                   "--data /dev/null https://entropy.ubuntu.com "
                   "> /dev/null 2>&1".format(
                       agent_str))
            app.log.debug("pollinate: {}".format(cmd))
            check_call(cmd, shell=True)
        except CalledProcessError as e:
            app.log.warning("Generating random seed failed: {}".format(e))
    if not app.argv.debug:
        submit(do_pollinate, lambda _: None)


def load_global_conf():
    """ loads global configuration

    Returns:
    dictionary of config items
    """
    global_conf_file = '/etc/conjure-up.conf'
    if not os.path.exists(global_conf_file):
        global_conf_file = os.path.join(
            os.path.dirname(__file__), '..', 'etc', 'conjure-up.conf')
    try:
        with open(global_conf_file) as fp:
            return yaml.safe_load(fp.read())
    except:
        return {}
