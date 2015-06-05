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
from formulary import rds
from formulary import service

DESCRIPTION = 'AWS Cloud Formation Stack Management'


def _add_commands(parser):
    commands = parser.add_subparsers(title='Commands', dest='command')
    create = commands.add_parser('create',
                                 help='Create a Cloud Formation stack')
    create.add_argument('type', choices=['network', 'rds', 'service'],
                        help='The type of stack to create')
    create.add_argument('name', help='The name of the stack to create')

    update = commands.add_parser('update',
                                 help='Update a Cloud Formation stack')
    update.add_argument('type', choices=['network', 'rds', 'service'],
                        help='The type of stack to update')
    update.add_argument('name', help='The name of the stack to update')


def _create_network_stack(region, environment, config_path, debug=False):
    _create_stack(region,
                  network.NetworkTemplate(environment, config_path), debug)


def _create_rds_stack(region, environment, name, config_path, debug=False):
    template = rds.RDSTemplate(name, environment, config_path, region)
    _create_stack(region, template, debug)


def _create_service_stack(region, environment, name, config_path, debug=False):
    template = service.ServiceTemplate(name, environment, config_path, region)
    _create_stack(region, template, debug)


def _update_network_stack(region, environment, config_path, debug=False):
    _update_stack(region,
                  network.NetworkTemplate(environment, config_path), debug)


def _update_rds_stack(region, environment, name, config_path, debug=False):
    template = rds.RDSTemplate(name, environment, config_path, region)
    _update_stack(region, template, debug)


def _update_service_stack(region, environment, name, config_path, debug=False):
    template = service.ServiceTemplate(name, environment, config_path, region)
    _update_stack(region, template, debug)


def _create_stack(region, template, debug):
    if debug:
        print('Stack Template: ')
        print(template.as_json())
    try:
        cloudformation.create_stack(region, template)
    except cloudformation.RequestException as error:
        sys.stdout.write(str(error) + "\n")
        sys.exit(1)
    result = cloudformation.estimate_stack_cost(region, template)
    sys.stdout.write('Stack Cost Calculator URL: {0}\n'.format(result))


def _update_stack(region, template, debug):
    if debug:
        print('Stack Template: ')
        print(template.as_json())
    try:
        cloudformation.update_stack(region, template)
    except cloudformation.RequestException as error:
        sys.stdout.write(str(error) + "\n")
        sys.exit(1)


def _validate_config_dir(config_dir):
    files = ['amis.yaml', 'mapping.yaml', 'instances.yaml']
    return any([path.exists(path.join(config_dir, f)) for f in files])


def run():

    parser = argparse.ArgumentParser(description=DESCRIPTION)
    _add_commands(parser)
    parser.add_argument('-c', '--config-dir',
                        default=path.abspath('.'),
                        help='Specify the path to the configuration directory. '
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

    if not _validate_config_dir(args.config_dir):
        sys.stderr.write('Invalid configuration directory: %s\n' %
                         args.config_dir)
        sys.exit(0)

    if args.command == 'create':
        if args.type == 'network':
            _create_network_stack(args.region,
                                  args.name,
                                  args.config_dir,
                                  args.verbose)
        elif args.type == 'rds':
            _create_rds_stack(args.region,
                              args.environment,
                              args.name,
                              args.config_dir,
                              args.verbose)
        elif args.type == 'service':
            _create_service_stack(args.region,
                                  args.environment,
                                  args.name,
                                  args.config_dir,
                                  args.verbose)
    elif args.command == 'update':
        if args.type == 'network':
            _update_network_stack(args.region,
                                  args.name,
                                  args.config_dir,
                                  args.verbose)
        elif args.type == 'rds':
            _update_rds_stack(args.region,
                              args.environment,
                              args.name,
                              args.config_dir,
                              args.verbose)
        elif args.type == 'service':
            _update_service_stack(args.region,
                                  args.environment,
                                  args.name,
                                  args.config_dir,
                                  args.verbose)
