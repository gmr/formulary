"""
Main Formulary Controller

"""
import logging
import sys
import uuid

from os import path

from formulary.builders import elasticache
from formulary.builders import environment
from formulary.builders import rds
from formulary.builders import service
from formulary.builders import stack
from formulary import cloudformation
from formulary import config
from formulary import template

LOGGER = logging.getLogger(__name__)

ACTIONS = {'create', 'update'}
RESOURCE_TYPES = {'environment', 'service', 'elasticache', 'rds',  'stack'}


class Controller(object):
    """The controller implements the top-level application behavior"""

    def __init__(self, config_path, action, env, resource_type, resource,
                 verbose, dry_run, profile):
        self._config_obj = config.ResourceConfig(config_path,
                                                 resource_type,
                                                 resource,
                                                 env)

        self._validate_arguments(config_path, action, env,
                                 resource_type, resource)

        self._action = action
        self._s3_prefix = str(uuid.uuid4())
        LOGGER.debug('S3 prefix: %s', self._s3_prefix)
        self._config_path = config_path
        self._environment = env
        self._profile = profile
        self._resource = resource
        self._resource_type = resource_type
        self._verbose = verbose
        self._dry_run = dry_run

        self._amis = self._config_obj.load_file('.', 'amis')
        self._instances = self._config_obj.load_file('.', 'instances')
        self._config = self._config_obj.load()
        self._environment_config = self._config_obj.environment_config()
        self._s3_bucket = self._environment_config.get('s3bucket')
        if not self._s3_bucket:
            self._s3_bucket = self._config.get('s3bucket')

        LOGGER.debug('S3bucket: %s', self._s3_bucket)

        if not self._s3_bucket:
            raise ValueError('s3bucket not configured in environment')

        self._mappings = self._config_obj.mappings()
        self._template = template.Template(self._template_name)
        self._environment_stack = self._get_environment_stack()
        self._cloud_formation = cloudformation.CloudFormation(self._profile,
                                                              self._region,
                                                              self._s3_bucket,
                                                              self._s3_prefix)

    def execute(self):
        """Create or update a Cloud Formation stack"""
        builder = self._build_template_resources()

        if self._config.get('description'):
            self._template.set_description(self._config['description'])

        self._template.update_outputs(builder.outputs)
        self._template.update_parameters(builder.parameters)
        self._template.update_resources(builder.resources)

        template_value = self._template.as_json()

        if self._dry_run:
            print(template_value)
            return

        env = self._resource if not self._environment else self._environment
        service_name = self._resource if self._environment else None

        if self._action == 'create':
            try:
                stack_id = self._cloud_formation.create_stack(self._template,
                                                              env,
                                                              service_name)
                print('Stack {0} created'.format(stack_id))
            except cloudformation.RequestException as error:
                self._error(str(error))

        elif self._action == 'update':
            try:
                self._cloud_formation.update_stack(self._template)
                print('Stack updated')
            except cloudformation.RequestException as error:
                self._error(str(error))

    def _build_environment_resources(self):
        builder_config = config.BuilderConfig(self._config, self._mappings,
                                              self._region, self._s3_bucket,
                                              self._s3_prefix, self._profile)
        builder = environment.Environment(builder_config, self._resource)
        return builder

    def _build_elasticache_resources(self, builder_config):
        return elasticache.Cache(builder_config, self._resource,
                                 self._environment_stack)

    def _build_rds_resources(self, builder_config):
        return rds.RDS(builder_config, self._resource, self._environment_stack)

    def _build_service_resources(self, builder_config):
        service_path = path.join(self._config_path,
                                 self._config_obj.resource_folder)
        return service.Service(builder_config, self._resource, self._amis,
                               service_path, self._environment_stack,
                               users=self._get_user_cloud_config())

    def _build_stack_resources(self, builder_config):
        return stack.Stack(builder_config, self._resource,
                           self._config_obj.base_path, self._amis,
                           self._environment_stack,
                           users=self._get_user_cloud_config())

    def _build_template_resources(self):
        self._template.update_mappings(self._mappings)
        if self._resource_type == 'environment':
            return self._build_environment_resources()

        self._template.update_mappings(self._environment_stack.mappings)

        builder_config = self._get_builder_config()
        if builder_config.settings.get('stack-only'):
            self._error("The specified service is designated as stack-only.")

        if self._resource_type == 'elasticache':
            return self._build_elasticache_resources(builder_config)
        elif self._resource_type == 'rds':
            return self._build_rds_resources(builder_config)
        elif self._resource_type == 'service':
            return self._build_service_resources(builder_config)
        elif self._resource_type == 'stack':
            return self._build_stack_resources(builder_config)

    def _get_builder_config(self):
        return config.BuilderConfig(self._config, self._mappings,
                                    self._region, self._s3_bucket,
                                    self._s3_prefix, self._profile,
                                    self._environment, self._resource)

    @staticmethod
    def _error(message):
        """Write out an error message and exit.

        :param str message: The error message

        """
        sys.stderr.write('ERROR: {0}\n'.format(message))
        sys.exit(1)

    def _get_environment_stack(self):
        """Return a stack instance if the environment is not

        """
        if self._resource_type == 'environment':
            return
        return cloudformation.EnvironmentStack(self._environment,
                                               self._environment_config,
                                               None, self._profile)

    def _get_user_cloud_config(self):
        """Return the opaque string that is appended to the bottom
        of user-data strings if ``include_users`` is true.

        :rtype: str

        """
        file_path = path.join(self._config_path, 'users.yaml')
        if path.exists(file_path):
            with open(file_path, 'r') as handle:
                return handle.read()

    @property
    def _region(self):
        """Return the region value from the environment config,
        defaulting to us-east-1

        :rtype: str

        """
        return self._environment_config.get('region', 'us-east-1')

    @property
    def _template_name(self):
        """Return the template name based upon the

        :rtype: str

        """
        if self._environment and self._resource_type != 'environment':
            return '{0}-{1}-{2}'.format(self._environment, self._resource_type,
                                        self._resource)
        return self._resource

    def _validate_arguments(self, config_path, action, env,
                            resource_type, resource):
        """Validate the initialization arguments, raising ``ValueError`` if any
        do not validate.

        :raises: ValueError

        """
        if not self._validate_action(action):
            raise ValueError('Invalid action: {0}'.format(action))

        if not self._validate_resource_type(resource_type):
            raise ValueError('Invalid resource type: {0}'.format(resource_type))

        if not self._config_obj.validate_config_path(config_path):
            raise ValueError('Invalid config path: {0}'.format(config_path))

        if resource_type != 'environment':
            if not env:
                raise ValueError('Environment not specified')
            elif not self._config_obj.validate_environment(config_path, env):
                raise ValueError('Invalid environment: {0}'.format(env))

        if not self._config_obj.validate_resource(config_path,
                                                  resource_type,
                                                  resource):
            raise ValueError('Invalid resource: {0}'.format(resource))

    @staticmethod
    def _validate_action(action):
        """Validate the action is a valid action

        :param str action: The action to validate
        :rtype: bool

        """
        return action in ACTIONS

    @staticmethod
    def _validate_resource_type(resource_type):
        """Validate the resource is valid

        :param str resource_type: The resource type specified
        :rtype: bool

        """
        return resource_type in RESOURCE_TYPES
