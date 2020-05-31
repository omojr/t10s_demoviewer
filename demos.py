import concurrent.futures
import ftplib
import logging
import os
import re
import urllib.request
import uuid
from datetime import datetime

from config import config
from db import get_conn


PATTERN = r'^pug\_(?P<map>\w+)\_(?P<datetime>[\d\_\-]+)\.dem$'
DOWNLOAD_LINK = 'ftp://{user}:{passwd}@{host}:{port}{remote_filepath}'
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

logging.basicConfig(filename=os.path.join(BASE_DIR, config['general']['demos_logfile']),
                    format="%(asctime)s [%(name)s %(levelname)s] - %(message)s",
                    level=logging.INFO)
logger = logging.getLogger(__file__)


def get_ftp_client(creds):
    client = ftplib.FTP(host=creds['host'])
    client.login(user=creds['user'], passwd=creds['passwd'])
    return client


def parse_demolist(demodir, server_name, filelist):
    regex = re.compile(PATTERN)
    result = []
    for file in filelist:
        if (m := regex.search(file)):
            info = {
                'server': server_name,
                'filename': file,
                'filepath': os.path.join(BASE_DIR, demodir, server_name, file),
                'datetime': datetime.strptime(m.group('datetime'), '%Y-%m-%d_%H-%M').strftime('%Y-%m-%d %H:%M'),
                'map': m.group('map'),
            }
            result.append(info)
    return result


def retrieve_demo_list(creds):
    """Return list of all .dem files on the server (default dir)"""
    ftp = get_ftp_client(creds)
    if ftp.pwd() != creds['remote_dir']:
        ftp.cwd(creds['remote_dir'])
    return [file for file in ftp.nlst() if file.endswith('.dem')]


def filter_demos(demodir, server_name, demos):
    """Filter out existing demos and return new ones"""
    demos_path = os.path.join(BASE_DIR, demodir, server_name)
    new_demos = [demo for demo in demos if not os.path.exists(os.path.join(demos_path, demo))]
    return new_demos


def download_demo(link, filepath):
    logger.info(f'Downloading demo to {filepath} ...')
    urllib.request.urlretrieve(link, filename=filepath)
    logger.info(f'Saved demo to {filepath}')


def download_new_demos(new_demos, server_config):
    download_args = []
    for demo in new_demos:
        format_args = {
            'remote_filepath': os.path.join(server_config[demo['server']]['remote_dir'], demo['filename']),
            **server_config[demo['server']]
        }
        link = DOWNLOAD_LINK.format(**format_args)
        download_args.append((link, demo['filepath']))

    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
        futures = [executor.submit(download_demo, *args) for args in download_args]
        for future in concurrent.futures.as_completed(futures):
            future.result()


def save_demos_db(new_demos):
    logger.info('Saving new demo entries to DB')
    conn = get_conn()
    cursor = conn.cursor()
    for demo in new_demos:
        demo_id = str(uuid.uuid4())
        cursor.execute('''insert into demos(demo_id, server, filepath, map, datetime)
                          values (?, ?, ?, ?, ?)''',
                       (demo_id,
                        demo['server'],
                        demo['filepath'],
                        demo['map'],
                        demo['datetime'],))
    conn.commit()
    conn.close()
    logger.info('Saved demos')


def update_demos():
    """
    Entrypoint for this module.
    Retrieve .dem files from servers via FTP, compare with existing,
    download new ones and add entries to DB.
    """
    demodir = config['general']['demodir']
    try:
        os.mkdir(os.path.join(BASE_DIR, demodir))
    except Exception:
        pass

    new_demos = []
    for server_name, creds in config['servers'].items():
        logger.info(f'Updating demos from {server_name} server...')
        demos = retrieve_demo_list(creds)
        count = len(demos)
        logger.info(f'Retrieved {count} demo{"s" if count != 1 else ""} on the {server_name} server')
        new = filter_demos(demodir, server_name, demos)
        count = len(new)
        logger.info(f'Got {count} new demo{"s" if count != 1 else ""} from {server_name} server')
        new_demos.extend(parse_demolist(demodir, server_name, new))
        try:
            os.mkdir(os.path.join(BASE_DIR, demodir, server_name))
        except Exception:
            pass

    if new_demos:
        download_new_demos(new_demos, config['servers'])
        save_demos_db(new_demos)
    else:
        logger.info('No new demos on the servers')


if __name__ == '__main__':
    update_demos()
