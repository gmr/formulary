"""
Main Formulary Controller

"""
import logging
import uuid

from formulary import aws
from formulary import config
from formulary import stacks

LOGGER = logging.getLogger(__name__)

DEFAULT_REGION = 'us-east-1'


class CloudFormation(object):
    """Perform CloudFormation stack management"""

    def __init__(self, aws_profile, config_path, resource_type, resource_name,
                 dry_run, vpc_name=None):
        """Create a new instance of the CloudFormation stack manager

        :param str aws_profile: The name of the AWS credentials profile to use
        :param str config_path: The path to the Formulary configuration dir
        :param str resource_type: The type of Formulary resource to manage
        :param str resource_name: The name of the Formulary resource to manage
        :param bool dry_run: Do not actually submit the CloudFormation command
        :param str vpc_name: The name of the VPC for the Formulary resource

        """
        if resource_type == 'vpc' and vpc_name:
            raise FormularyException('Do not specify vpc with vpc type')

        self._aws_profile = aws_profile
        self._config_path = config_path
        self._resource_type = resource_type
        self._resource_name = resource_name
        self._dry_run = dry_run
        self._vpc_name = vpc_name

        self._config = config.Resource(config_path, resource_type,
                                       resource_name, vpc_name)
        self._vpc_config = self._config.vpc_config()

    def create_stack(self):
        stack = self._get_stack()
        if self._dry_run:
            LOGGER.info('Formulary Create Stack Dry-Run Output:\n')
            return print(stack.to_json(2))

        cloudformation = self._cloudformation(stack)
        try:
            stack_id = cloudformation.create_stack(stack)
        except Exception as error:
            raise FormularyException(error)

        LOGGER.info('Stack creation submitted (%s)', stack_id)

    def delete_stack(self):
        stack = self._get_stack()
        if self._dry_run:
            LOGGER.info('Formulary Delete Stack Dry-Run Complete\n')
            return
        cloudformation = self._cloudformation(stack)
        cloudformation.delete_stack(stack)

    def update_stack(self):
        stack = self._get_stack()
        if self._dry_run:
            LOGGER.info('Formulary Update Stack Dry-Run Output:\n')
            return print(stack.to_json(2))
        cloudformation = self._cloudformation(stack)
        cloudformation.update_stack(stack)

    @property
    def region(self):
        """Return the Amazon AWS Region for the VPC

        :rtype: str

        """
        return self._vpc_config.get('region', DEFAULT_REGION)

    def _cloudformation(self, stack):
        """Return a CloudFormation client

        :rtype: formulary.aws.CloudFormation

        """
        return aws.CloudFormation(self._aws_profile,
                                  self.region,
                                  self._vpc_config['s3bucket'],
                                  stack.id)

    def _get_stack(self):
        if self._resource_type == 'service':
            return self._get_service_stack()
        elif self._resource_type == 'vpc':
            return self._get_vpc_stack()

        raise NotImplementedError

    def _get_service_stack(self):
        return stacks.Service(config.Stack(self._config_path, 'service',
                                           self._resource_name,
                                           self._aws_profile),
                              self._resource_name,
                              self._vpc_name)

    def _get_vpc_stack(self):
        if not self._config.validate_vpc(self._resource_name):
            raise FormularyException('Invalid VPC configuration')
        return stacks.VPC(self._config.load(), self._resource_name)


class Maintenance(object):
    """Maintenance related commands that do not interact with stacks."""

    def __init__(self, aws_profile, vpc_name=None):
        if not vpc_name:
            raise FormularyException('VPC is required')
        self._aws_profile = aws_profile
        self._vpc_name = vpc_name

    def s3cleanup(self):
        LOGGER.info('Starting S3 Cleanup of %s stack files', self._vpc_name)


class FormularyException(Exception):
    pass
