"""
Formulary Command Line Interface

"""
import argparse
import logging
from os import path
import sys

from formulary import __version__
from formulary import cloudformation
from formulary import network

DESCRIPTION = 'AWS Cloud Formation Stack Management'


def _add_commands(parser):
    commands = parser.add_subparsers(title='Commands', dest='command')
    create = commands.add_parser('create',
                                 help='Create a Cloud Formation stack')
    create.add_argument('type', choices=['network', 'service'],
                        help='The type of stack to create')

    update = commands.add_parser('update',
                                 help='Update a Cloud Formation stack')
    update.add_argument('type', choices=['network', 'service'],
                        help='The type of stack to update')


def _create_network_stack(region, environment, config_path):
    template = network.NetworkStackTemplate(environment, config_path)
    try:
        cloudformation.create_stack(region, template)
    except cloudformation.RequestException as error:
        sys.stdout.write(str(error) + "\n")
        sys.exit(1)


def _update_network_stack(region, environment, config_path):
    template = network.NetworkStackTemplate(environment, config_path)
    try:
        cloudformation.update_stack(region, template)
    except cloudformation.RequestException as error:
        sys.stdout.write(str(error) + "\n")
        sys.exit(1)


def run():

    parser = argparse.ArgumentParser(description=DESCRIPTION)
    _add_commands(parser)
    parser.add_argument('-c', '--config-dir',
                        default=path.normpath('.'),
                        help='Specify the path to the configuration directory. ' \
                             'Default: .')
    parser.add_argument('-e', '--environment', required=True,
                        help='The formulary environment name (Required)')

    parser.add_argument('-r', '--region', dest='region', default='us-east-1',
                        help='Specify the region for the stack. '
                             'Default: us-east-1')
    parser.add_argument('-v', '--verbose', action='store_true')

    args = parser.parse_args()

    if args.verbose:
        logging.basicConfig(level=logging.INFO)

    if args.command == 'create':
        if args.type == 'network':
            _create_network_stack(args.region,
                                  args.environment,
                                  args.config_dir)
    elif args.command == 'update':
        if args.type == 'network':
            _update_network_stack(args.region,
                                  args.environment,
                                  args.config_dir)
