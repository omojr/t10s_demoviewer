import os
import yaml

if os.environ.get('ENV') == 'local':
    CONFIG_PATH = './config.yml'
else:
    CONFIG_PATH = '/etc/t10s_demoviewer/config.yml'

with open(CONFIG_PATH, 'r') as f:
    config = yaml.safe_load(f)
