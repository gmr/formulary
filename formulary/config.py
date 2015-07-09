"""
Builder Configuration

"""
import logging
from os import path
import yaml

LOGGER = logging.getLogger(__name__)

CONFIG_FILES = {'amis.yaml', 'mapping.yaml', 'instances.yaml',
                'environments', 'rds', 'services'}

STACK_FOLDERS = {'elasticache': 'elasticache',
                 'environment': 'environments',
                 'rds': 'rds',
                 'service': 'services',
                 'stack': 'stacks'}


class BuilderConfig(object):

    """Configuration class for Builder objects"""
    def __init__(self, settings, mappings, region, s3_bucket, s3_prefix,
                 profile, environment=None, service=None):
        """Create a new instance of a Config class

        :param dict settings: Settings from configuration files
        :param dict mappings: Mapping configuration
        :param str region: AWS region name
        :param str s3_bucket: The formulary S3 work bucket
        :param str s3_prefix: s3 work prefix
        :param str profile: The AWS credentials profile to use
        :param str|None environment: The optional formulary environment name
        :param str|None service:  Formulary service name if set

        """
        self.settings = self._flatten_settings(settings, environment)
        self.environment = environment
        self.mappings = mappings
        self.region = region
        self.profile = profile
        self.s3_bucket = s3_bucket
        self.s3_prefix = s3_prefix
        self.service = service

    def _flatten_settings(self, settings, environment):
        out = {}
        for key, value in settings.items():
            if isinstance(value, dict):
                for value_key in settings[key].keys():
                    if value_key == environment:
                        out[key] = settings[key][value_key]
                        break
                    elif value_key == 'default':
                        out[key] = settings[key]['default']
                        break
                    else:
                        out[key] = self._flatten_settings(value, environment)
            else:
                out[key] = value
        return out


class ResourceConfig(object):

    def __init__(self, base_path, resource_type, resource, environment):
        self.base_path = self._normalize_path(base_path)
        self.environment = environment
        self._resource = resource
        self._resource_type = resource_type

    def _flatten_config(self, cfg):
        """Take a given config dictionary and if it contains environment
        specific values, map the environment values to the associated
        top level keys.

        :param dict cfg: The configuration to flatten
        :rtype: dict

        """
        output = {}
        for key, value in cfg.items():
            if isinstance(value, dict):
                if self.environment in value.keys():
                    output[key] = value[self.environment]
                else:
                    output[key] = self._flatten_config(value)
            elif isinstance(value, list):
                output[key] = []
                for list_value in value:
                    if isinstance(list_value, dict):
                        output[key].append(self._flatten_config(list_value))
                    else:
                        output[key].append(list_value)
            else:
                output[key] = value
        return output

    def load(self):
        """Return the config for the specified resource type

        :rtype: dict

        """
        if self._resource_type in ['environment', 'service']:
            settings = self.load_file(self.resource_folder, self._resource_type)
        else:
            settings = self.load_file(self.resource_folder, self._resource)
        return self._flatten_config(settings)

    def load_file(self, folder, file):
        """Return the contents of the specified configuration file in the
        specified configuration folder.


        :param str folder: The folder to load the configuration file from
        :param str file: The file to load
        :rtype: dict

        """
        file_path = path.join(self.base_path, folder, '{0}.yaml'.format(file))
        if path.exists(file_path):
            LOGGER.debug('Loading configuration from %s', file_path)
            with open(file_path, 'r') as handle:
                return yaml.load(handle)
        LOGGER.debug('Configuration file not found: %s', file_path)
        return {}

    def environment_config(self):
        """Return the environment configuration

        :rtype: dict

        """
        if not self.environment:
            return {}
        return self.load_file(path.join(STACK_FOLDERS['environment'],
                                        self.environment), 'environment')

    def environment_mappings(self):
        """Return the mappings from the environment folder

        :rtype: dict

        """
        if not self.environment:
            return {}
        return self.load_file(path.join(STACK_FOLDERS['environment'],
                                        self.environment), 'mappings')

    def mappings(self):
        """Return the mapping data from the various config dirs and return
        merged mapping values in order of precedence of global, environment,
        or service/entity.

        :rtype: dict

        """
        mappings = dict()
        mappings.update(self.load_file(self.base_path, 'mappings'))
        if not self._resource == 'environment':
            self.merge(mappings, self.environment_mappings())
        mappings.update(self.load_file(self.resource_folder, 'mappings'))
        return mappings

    def merge(self, a, b, key_path=None):
        if key_path is None: key_path = []
        for key in b:
            if key in a:
                if isinstance(a[key], dict) and isinstance(b[key], dict):
                    self.merge(a[key], b[key], key_path + [str(key)])
            else:
                a[key] = b[key]
        return a

    @staticmethod
    def _normalize_path(value): # pragma: no cover
        """Normalize the specified path value returning the absolute
        path for it.

        :param str value: The path value to normalize
        :rtype: str

        """
        return path.abspath(path.normpath(value))

    @property
    def resource_folder(self):
        """Return the folder that contains the resource's configuration data

        :rtype: str

        """
        if self._resource_type in ['environment', 'service']:
            return path.join(self.base_path, STACK_FOLDERS[self._resource_type],
                             self._resource)
        return path.join(self.base_path, STACK_FOLDERS[self._resource_type])

    @staticmethod
    def validate_config_path(config_path):
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
    def validate_environment(config_path, env):
        """Validate that the expected environment ``network.yaml``
        configuration file exists within the config path for the environment.

        :param str config_path: The base config path
        :param str env: The environment name
        :rtype: bool

        """
        if not env:
            return False
        return path.exists(path.join(config_path,
                                     STACK_FOLDERS['environment'],
                                     env, 'environment.yaml'))

    @staticmethod
    def validate_resource(config_path, resource_type, resource):
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
