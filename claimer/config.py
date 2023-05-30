import os
import configparser

HOME = os.path.expanduser('~')

CONFIG_DIR = os.path.join(HOME, '.config', 'jira-claimer')
CONFIG_FILE = os.path.join(CONFIG_DIR, 'config.ini')

if not os.path.isdir(CONFIG_DIR):
    os.mkdir(CONFIG_DIR)


def load_config():
    config = configparser.ConfigParser()
    config.read([CONFIG_FILE])

    try:
        jira_user = config.get('JIRA', 'jira_user')
        jira_pass = config.get('JIRA', 'jira_pass')
        jira_server = config.get('JIRA', 'jira_server')
    except configparser.NoSectionError:
        config.add_section('JIRA')
        jira_user = None
        jira_pass = None
        jira_server = None

    if not jira_user:
        jira_user = input("Enter jira user:")
        config.set('JIRA', 'jira_user', jira_user)

    if not jira_pass:
        jira_pass = input("Enter jira pass:")
        config.set('JIRA', 'jira_pass', jira_pass)

    if not jira_server:
        jira_server = input("Enter jira server:")
        config.set('JIRA', 'jira_server', jira_server)

    with open(CONFIG_FILE, 'w') as config_file:
        config.write(config_file)

    return jira_user, jira_pass, jira_server


jira_user, jira_pass, jira_server = load_config()
