"""
Build Cloud Formation stacks

"""
import logging
from os import path

from formulary.builders import base
from formulary.resources import cloudformation
from formulary import config
from formulary.builders import service
from formulary import utils

LOGGER = logging.getLogger(__name__)


class Stack(base.Builder):

    def __init__(self, config, name, base_path, amis, environment_stack):
        super(Stack, self).__init__(config, name)
        self._amis = amis
        self._base_path = base_path
        self._config = config
        self._mappings = config.mappings
        self._mappings.update(environment_stack.mappings)
        self._environment_stack = environment_stack
        self._process_resources()

    def _get_builder_config(self, resource, config_values):
        return config.BuilderConfig(config_values,
                                    self._mappings,
                                    self._config.region,
                                    self._config.s3_bucket,
                                    self._config.s3_prefix,
                                    self._config.profile,
                                    self._config.environment,
                                    resource)

    def _process_resources(self):
        for resource in self._config.settings.get('resources'):
            if resource['type'] == 'service':
                LOGGER.debug('Add service: %r', resource['name'])
                cfg_obj = config.ResourceConfig(self._base_path,
                                                resource['type'],
                                                resource['name'],
                                                self._config.environment)
                builder_cfg = self._get_builder_config(resource['name'],
                                                       cfg_obj.load())

                dependency = self._maybe_camel_case(resource.get('dependency'))
                handle = self._maybe_camel_case(resource.get('wait-handle'))
                
                builder = service.Service(builder_cfg, resource['name'],
                                          self._amis, cfg_obj.resource_folder,
                                          self._environment_stack,
                                          dependency,
                                          handle)

                self._outputs.update(builder.outputs)
                self._resources.update(builder.resources)

            elif resource['type'] == 'rds':
                LOGGER.debug('Add RDS: %r', resource['name'])

            elif resource['type'] == 'wait':
                LOGGER.debug('Add wait-condition: %r', resource['name'])
                handle = {'Ref': utils.camel_case(resource['wait-handle'])}
                obj = cloudformation.WaitCondition(resource.get('count'),
                                                   handle,
                                                   resource.get('timeout'))
                self._add_resource(resource['name'], obj)

            elif resource['type'] == 'wait-handle':
                LOGGER.debug('Add wait handle: %s', resource['name'])
                self._add_resource(resource['name'],
                                   cloudformation.WaitConditionHandle())

            else:
                ValueError('Unsupported resource type: %s', resource['type'])

    @staticmethod
    def _maybe_camel_case(value):
        return utils.camel_case(value) if value else None
