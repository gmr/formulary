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


class CLI(object):

    def __init__(self):
        self._parser = self._create_parser()

    def run(self):
        args = self._parser.parse_args()
        if not self._validate_config_dir(args.config_dir):
            sys.stderr.write('Invalid configuration directory: %s\n' %
                             args.config_dir)
            sys.exit(0)

        if args.verbose:
            logging.basicConfig(level=logging.INFO)

        template_class = self._get_template(args.type)
        template = template_class(args.name, args.environment,
                                  args.config_dir, args.region)

        if args.dry_run:
            print(template.as_json())
            sys.exit(0)

        if args.command == 'create':
            self._create_stack(args.region, template, args.verbose)
        elif args.command == 'update':
            self._update_stack(args.region, template, args.verbose)

    @staticmethod
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

    def _create_parser(self):
        parser = argparse.ArgumentParser(description=DESCRIPTION)
        self._add_commands(parser)
        parser.add_argument('-c', '--config-dir',
                            default=path.abspath('.'),
                            help='Specify the path to the configuration '
                                 'directory. Default: .')
        parser.add_argument('-d', '--dry-run', action='store_true')
        parser.add_argument('-e', '--environment', required=True,
                            help='The formulary environment name (Required)')
        parser.add_argument('-r', '--region', dest='region',
                            default='us-east-1',
                            help='Specify the region for the stack. '
                                 'Default: us-east-1')
        parser.add_argument('-v', '--verbose', action='store_true')
        return parser

    @staticmethod
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

    @staticmethod
    def _update_stack(region, template, debug):
        if debug:
            print('Stack Template: ')
            print(template.as_json())
        try:
            cloudformation.update_stack(region, template)
        except cloudformation.RequestException as error:
            sys.stdout.write(str(error) + "\n")
            sys.exit(1)

    @staticmethod
    def _get_template(template_type):
        if template_type == 'network':
            return network.NetworkTemplate
        elif template_type == 'rds':
            return rds.RDSTemplate
        elif template_type == 'service':
            return service.ServiceTemplate

    @staticmethod
    def _validate_config_dir(config_dir):
        files = ['amis.yaml', 'mapping.yaml', 'instances.yaml']
        return any([path.exists(path.join(config_dir, f)) for f in files])


def run():
    CLI().run()
