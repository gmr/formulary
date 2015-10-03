"""
Formulary Command Line Interface

"""
import argparse
import logging.config
from os import path
import sys

from formulary import main

from formulary import LOG_DEBUG, LOG_INFO, LOG_WARNING

DESCRIPTION = 'AWS CloudFormation Stack Management'
RESOURCE_TYPES = ['service', 'vpc']


class CLI(object):
    def __init__(self):
        self._parser = self._create_parser()

    def run(self):
        args = self._parser.parse_args()
        self._configure_logging(args)
        try:
            if args.command in ['create', 'delete', 'update']:
                self._run_cloudformation_command(args)
            elif args.command == 'cleanup':
                self._run_cleanup_command(args)
            else:
                self._parser.print_usage()

        except main.FormularyException as error:
            sys.stderr.write('ERROR: {}\n'.format(error))
            sys.exit(1)

    @staticmethod
    def _add_commands(parser):
        commands = parser.add_subparsers(title='Commands', dest='command')
        create = commands.add_parser('create',
                                     help='Create a CloudFormation stack')
        create.add_argument('type',
                            choices=RESOURCE_TYPES,
                            help='The type of stack to create')
        create.add_argument('name', help='The name of the stack to create')
        create.add_argument('vpc',
                            default=None,
                            nargs='?',
                            help='The VPC to create the stack in')

        delete = commands.add_parser('delete',
                                     help='Delete a CloudFormation stack')
        delete.add_argument('type',
                            choices=RESOURCE_TYPES,
                            help='The type of stack to delete')
        delete.add_argument('name', help='The name of the stack to delete')
        delete.add_argument('vpc',
                            default=None,
                            nargs='?',
                            help='The VPC to delete the stack from')

        update = commands.add_parser('update',
                                     help='Update a CloudFormation stack')
        update.add_argument('type',
                            choices=RESOURCE_TYPES,
                            help='The type of stack to update')
        update.add_argument('name', help='The name of the stack to update')
        update.add_argument('vpc',
                            default=None,
                            nargs='?',
                            help='The VPC to update the stack in')

        commands.add_parser('cleanup', help='Cleanup stale stack data in S3')

    def _create_parser(self):
        parser = argparse.ArgumentParser(description=DESCRIPTION)
        self._add_commands(parser)
        default_path = path.abspath('.')
        parser.add_argument('-c',
                            dest='config_dir',
                            default=default_path,
                            help='Specify the path to the configuration '
                            'directory. Default: {}'.format(default_path))
        parser.add_argument('-d',
                            dest="dry_run",
                            action='store_true',
                            help='Dry-Run Execution')
        parser.add_argument('-p', '--profile',
                            help='AWS credentials profile. Default: default')
        parser.add_argument('-v',
                            dest='verbose',
                            action='store_true',
                            help='Verbose output')
        parser.add_argument('-vv',
                            dest='debug',
                            action='store_true',
                            help='Debug output')
        return parser

    @staticmethod
    def _configure_logging(args):
        if args.debug is True:
            logging.config.dictConfig(LOG_DEBUG)
        elif args.verbose is True:
            logging.config.dictConfig(LOG_INFO)
        else:
            logging.config.dictConfig(LOG_WARNING)

    @staticmethod
    def _run_cleanup_command(args):
        obj = main.Maintenance(args.profile, args.vpc)
        obj.s3cleanup()

    @staticmethod
    def _run_cloudformation_command(args):
        obj = main.CloudFormation(args.profile, args.config_dir, args.type,
                                  args.name, args.dry_run, args.vpc)
        if args.command == 'create':
            obj.create_stack()
        elif args.command == 'delete':
            obj.delete_stack()
        elif args.command == 'update':
            obj.update_stack()


def run():
    CLI().run()
