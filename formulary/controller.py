"""
Main Formulary Controller

"""
import logging
from os import path
import sys

import boto.provider
import yaml

from formulary import builders
from formulary import cloudformation
from formulary import stack
from formulary import template

LOGGER = logging.getLogger(__name__)

ACTIONS = {'create', 'update'}
CONFIG_FILES = {'amis.yaml', 'mapping.yaml', 'instances.yaml',
                'environments', 'rds', 'services'}
RESOURCE_TYPES = {'environment', 'service', 'elasticache', 'rds',  'stack'}
STACK_FOLDERS = {'elasticache': 'elasticache',
                 'environment': 'environments',
                 'rds': 'rds',
                 'service': 'services',
                 'stack': 'stacks'}


class Controller(object):
    """The controller implements the top-level application behavior"""

    def __init__(self, config_path, action, environment, resource_type,
                 resource, verbose, dry_run, profile):
        config_path = self._normalize_path(config_path)
        self._validate_arguments(config_path, action, environment,
                                 resource_type, resource)

        self._action = action
        self._config_path = config_path
        self._environment = environment
        self._profile = profile
        self._resource = resource
        self._resource_type = resource_type
        self._verbose = verbose
        self._dry_run = dry_run

        self._amis = self._load_config_file('.', 'amis')
        self._instances = self._load_config_file('.', 'instances')
        self._config = self._load_config()
        self._environment_config = self._load_environment_config()
        self._mappings = self._load_mappings()
        self._template = template.Template(self._template_name)
        self._stack = self._get_stack()

    def execute(self):
        """Create or update a Cloud Formation stack"""
        self._build_template_resources()

        if self._config.get('description'):
            self._template.set_description(self._config['description'])

        template_value = self._template.as_json()
        if self._dry_run:
            print(template_value)
            return

        if self._action == 'create':
            try:
                cloudformation.create_stack(self._region, self._template,
                                            self._profile)
            except boto.provider.ProfileNotFoundError:
                self._error('AWS profile not found')
            print('Stack created')

        elif self._action == 'update':
            try:
                cloudformation.update_stack(self._region, self._template,
                                            self._profile)
            except boto.provider.ProfileNotFoundError:
                self._error('AWS profile not found')
            print('Stack updated')

        result = cloudformation.estimate_stack_cost(self._region,
                                                    self._template,
                                                    self._profile)
        print('Stack cost calculator URL: {0}'.format(result))

    def _build_environment_resources(self):
        builder = builders.Environment(self._config, self._resource,
                                       self._mappings)
        self._template.update_resources(builder.resources)

    def _build_rds_resources(self):
        builder = builders.RDS(self._config, self._resource, self._environment,
                               self._mappings, self._stack)
        self._template.update_resources(builder.resources)

    def _build_service_resources(self):
        service_path = path.join(self._config_path, self._resource_folder)
        builder = builders.Service(self._config, self._resource,
                                   self._environment, self._mappings,
                                   self._stack, self._region, self._amis,
                                   self._instances, service_path)
        self._template.update_resources(builder.resources)

    def _build_template_resources(self):
        self._template.update_mappings(self._mappings)
        if self._resource_type == 'environment':
            return self._build_environment_resources()

        self._template.update_mappings(self._stack.mappings)

        if self._resource_type == 'rds':
            self._build_rds_resources()

        elif self._resource_type == 'service':
            self._build_service_resources()

    def _error(self, message):
        """Write out an error message and exit.

        :param str message: The error message

        """
        sys.stderr.write('ERROR: {0}\n'.format(message))
        sys.exit(1)

    def _flatten_config(self, config):
        """Take a given config dictionary and if it contains environment
        specific values, map the environment values to the associated
        top level keys.

        :param dict config: The configuration to flatten
        :rtype: dict

        """
        output = {}
        for key, value in config.items():
            if isinstance(value, dict) and self._environment in value:
                output[key] = value[self._environment]
            else:
                output[key] = value
        return output

    def _get_stack(self):
        """Return a stack instance if the environment is not

        """
        if self._resource_type == 'environment':
            return
        return stack.Stack(self._environment, self._environment_config,
                           None, self._profile)

    def _load_config(self):
        """Return the config for the specified resource type

        :rtype: dict

        """
        if self._resource_type in ['environment', 'service']:
            config = self._load_config_file(self._resource_folder,
                                            self._resource_type)
        else:
            config = self._load_config_file(self._resource_folder,
                                            self._resource)
        return self._flatten_config(config)

    def _load_config_file(self, folder, file):
        """Return the contents of the specified configuration file in the
        specified configuration folder.


        :param str folder: The folder to load the configuration file from
        :param str file: The file to load
        :rtype: dict

        """
        file_path = path.join(self._config_path, folder,
                              '{}.yaml'.format(file))
        if path.exists(file_path):
            LOGGER.debug('Loading configuration from %s', file_path)
            with open(file_path, 'r') as handle:
                return yaml.load(handle)
        LOGGER.debug('Configuration file not found: %s', file_path)
        return {}

    def _load_environment_config(self):
        """Return the environment configuration

        :rtype: dict

        """
        if not self._environment:
            return {}
        return self._load_config_file(path.join(STACK_FOLDERS['environment'],
                                                self._environment),
                                      'environment')

    def _load_environment_mappings(self):
        """Return the mappings from the environment folder

        :rtype: dict

        """
        if not self._environment:
            return {}
        return self._load_config_file(path.join(STACK_FOLDERS['environment'],
                                                self._environment),
                                      'mappings')

    def _load_mappings(self):
        """Return the mapping data from the various config dirs and return
        merged mapping values in order of precedence of global, environment,
        or service/entity.

        :rtype: dict

        """
        mappings = dict()
        mappings.update(self._load_config_file(self._config_path, 'mappings'))
        if not self._resource == 'environment':
            mappings.update(self._load_environment_mappings())

        mappings.update(self._load_config_file(self._resource_folder,
                                               'mappings'))

        return mappings

    @staticmethod
    def _normalize_path(value): # pragma: no cover
        """Normalize the specified path value returning the absolute
        path for it.

        :param str value: The path value to normalize
        :rtype: str

        """
        return path.abspath(path.normpath(value))

    @property
    def _region(self):
        """Return the region value from the environment config,
        defaulting to us-east-1

        :rtype: str

        """
        return self._environment_config.get('region', 'us-east-1')

    @property
    def _resource_folder(self):
        """Return the folder that contains the resource's configuration data

        :rtype: str

        """
        if self._resource_type in ['environment', 'service']:
            return path.join('{}s'.format(self._resource_type),
                             self._resource)
        return self._resource_type

    @property
    def _template_name(self):
        """Return the template name based upon the

        :rtype: str

        """
        if self._environment:
            return '{0}-{1}-{2}'.format(self._environment, self._resource_type,
                                        self._resource)
        return self._resource

    @classmethod
    def _validate_arguments(cls, config_path, action, environment,
                            resource_type, resource):
        """Validate the initialization arguments, raising ``ValueError`` if any
        do not validate.

        :raises: ValueError

        """
        if not cls._validate_action(action):
            raise ValueError('Invalid action: {}'.format(action))

        if not cls._validate_resource_type(resource_type):
            raise ValueError('Invalid resource type: {}'.format(resource_type))

        if not cls._validate_config_path(config_path):
            raise ValueError('Invalid config path: {}'.format(config_path))

        if (resource_type != 'environment' and
                not cls._validate_environment(config_path, environment)):
            raise ValueError('Invalid environment: {}'.format(environment))

        if not cls._validate_resource(config_path, resource_type, resource):
            raise ValueError('Invalid resource: {}'.format(resource))

    @staticmethod
    def _validate_action(action):
        """Validate the action is a valid action

        :param str action: The action to validate
        :rtype: bool

        """
        return action in ACTIONS

    @staticmethod
    def _validate_config_path(config_path):
        """Validate that the specified configuration path exists and
        contains at least some of the files or folders expected.

        :param str config_path: The path to validate
        :rtype: bool

        """
        paths_found = [path.exists(config_path)]
        paths_found += [path.exists(path.join(config_path, f)) for f in
                        CONFIG_FILES]
        return any(paths_found)

    @staticmethod
    def _validate_environment(config_path, environment):
        """Validate that the expected environment ``network.yaml``
        configuration file exists within the config path for the environment.

        :param str config_path: The base config path
        :param str environment: The environment name
        :rtype: bool

        """
        return path.exists(path.join(config_path,
                                     STACK_FOLDERS['environment'],
                                     environment,
                                     'environment.yaml'))

    @staticmethod
    def _validate_resource(config_path, resource_type, resource):
        """Validate the resource configuration directory exists

        :param str resource_type: The resource type specified
        :param str resource: The resource to validate
        :rtype: bool

        """
        if resource_type in ['environment', 'service']:
            return path.exists(path.join(config_path,
                                         '{}s'.format(resource_type),
                                         resource,
                                         '{}.yaml'.format(resource_type)))
        return path.exists(path.join(config_path,
                                     STACK_FOLDERS[resource_type],
                                     '{}.yaml'.format(resource)))

    @staticmethod
    def _validate_resource_type(resource_type):
        """Validate the resource is valid

        :param str resource_type: The resource type specified
        :rtype: bool

        """
        return resource_type in RESOURCE_TYPES
