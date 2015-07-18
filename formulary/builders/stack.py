"""
Build Cloud Formation stacks

"""
import logging

from formulary.builders import base
from formulary.resources import cloudformation
from formulary import config
from formulary.builders import elasticache
from formulary.builders import rds
from formulary.builders import service
from formulary import utils

LOGGER = logging.getLogger(__name__)


class Stack(base.Builder):

    def __init__(self, config, name, base_path, amis, environment_stack, users):
        super(Stack, self).__init__(config, name)
        self._amis = amis
        self._base_path = base_path
        self._config = config
        self._mappings = config.mappings
        self._mappings.update(environment_stack.mappings)
        self._environment_stack = environment_stack
        self._users = users
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
                handle = self._maybe_camel_case(resource.get('wait'))
                builder = service.Service(builder_cfg,
                                          resource['name'],
                                          self._amis,
                                          cfg_obj.resource_folder,
                                          self._environment_stack,
                                          dependency,
                                          handle,
                                          resource['name'],
                                          users=self._users)

                self._outputs += builder.outputs
                self._resources += builder.resources

            elif resource['type'] == 'elasticache':
                LOGGER.debug('Add Elasticache: %r', resource['name'])
                cfg_obj = config.ResourceConfig(self._base_path,
                                                resource['type'],
                                                resource['name'],
                                                self._config.environment)
                builder_cfg = self._get_builder_config(resource['name'],
                                                       cfg_obj.load())

                builder = elasticache.Cache(builder_cfg,
                                            resource['name'],
                                            self._environment_stack)

                self._outputs += builder.outputs
                self._resources += builder.resources

            elif resource['type'] == 'rds':
                LOGGER.debug('Add RDS: %r', resource['name'])
                cfg_obj = config.ResourceConfig(self._base_path,
                                                resource['type'],
                                                resource['name'],
                                                self._config.environment)
                builder_cfg = self._get_builder_config(resource['name'],
                                                       cfg_obj.load())

                builder = rds.RDS(builder_cfg,
                                  resource['name'],
                                  self._environment_stack)

                self._outputs += builder.outputs
                self._resources += builder.resources

            elif resource['type'] == 'wait':
                LOGGER.debug('Add wait-condition: %r', resource['name'])
                if resource.get('handle'):
                    handle = {'Ref': utils.camel_case(resource['handle'])}
                    wait = cloudformation.WaitCondition(resource.get('count',1),
                                                        handle,
                                                        resource.get('timeout',
                                                                     3600))
                else:
                    wait = cloudformation.WaitCondition()
                    wait.set_creation_policy(resource['count'],
                                             resource['timeout'])
                if resource.get('dependency'):
                    wait.set_dependency(resource['dependency'])
                self._add_resource(resource['name'], wait)

                cc_name = utils.camel_case(resource['name'])
                self._add_output(cc_name + 'Data',
                                 'WaitCondition return data',
                                  {'Fn::GetAtt': [cc_name, 'Data']})

            elif resource['type'] == 'wait-handle':
                LOGGER.debug('Add wait handle: %s', resource['name'])
                self._add_resource(resource['name'],
                                   cloudformation.WaitConditionHandle())

            else:
                ValueError('Unsupported resource type: %s', resource['type'])

    @staticmethod
    def _maybe_camel_case(value):
        return utils.camel_case(value) if value else None
