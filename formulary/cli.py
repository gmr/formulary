"""
Formulary Command Line Interface

"""
import argparse
import logging.config
from os import path
import sys

from formulary import controller
from formulary import LOG_CONFIG

DESCRIPTION = 'AWS Cloud Formation Stack Management'


class CLI(object):

    def __init__(self):
        self._parser = self._create_parser()

    def run(self):
        args = self._parser.parse_args()
        if args.verbose:
            logging.config.dictConfig(LOG_CONFIG)
        try:
            obj = controller.Controller(args.config_dir,
                                        args.command,
                                        args.environment,
                                        args.type,
                                        args.name,
                                        args.verbose,
                                        args.dry_run,
                                        args.profile)
        except ValueError as error:
            sys.stderr.write('{}\n'.format(error))
            sys.exit(1)

        obj.execute()

    @staticmethod
    def _add_commands(parser):
        commands = parser.add_subparsers(title='Commands', dest='command')
        create = commands.add_parser('create',
                                     help='Create a Cloud Formation stack')
        create.add_argument('type', choices=controller.RESOURCE_TYPES,
                            help='The type of stack to create')
        create.add_argument('name', help='The name of the stack to create')

        update = commands.add_parser('update',
                                     help='Update a Cloud Formation stack')
        update.add_argument('type', choices=controller.RESOURCE_TYPES,
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
        parser.add_argument('-e', '--environment',
                            help='The formulary environment name')
        parser.add_argument('-p', '--profile',
                            help='The AWS credentials profile to use')
        parser.add_argument('-v', '--verbose', action='store_true')
        return parser


def run():
    CLI().run()
