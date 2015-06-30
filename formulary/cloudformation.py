"""
Cloud Formation methods and interfaces

"""
import collections
import logging
import uuid

from boto3 import session
from botocore import exceptions

from formulary import s3

LOGGER = logging.getLogger(__name__)
MAX_TEMPLATE_SIZE = 51200

StackResource = collections.namedtuple('StackResource',
                                       ('id', 'type', 'name', 'status'))


class CloudFormation(object):
    """Class for interfacing with Cloud Formation and related APIs"""

    def __init__(self, profile, region, s3bucket_name, s3bucket_path):
        """Estimate the cost of the stack in EC2

        :param str region: The region name to create the stack in
        :param str bucket: The bucket to use for large templates
        :param str profile: The credentials profile to use

        """
        self._s3 = s3.S3(s3bucket_name, s3bucket_path, profile)

        self._session = session.Session(profile_name=profile,
                                        region_name=region)
        self._client = self._session.client('cloudformation')

    def create_stack(self, template, environment, service=None):
        """Create a stack in the specified region with the given template,
        returning the stack id.

        :param Template template: The template to use
        :param str environment: The environment to set in a stack tag
        :param str|None service: The service name to set in a stack tag
        :rtype: str

        """
        template_id = str(uuid.uuid4())
        url = self._s3.upload(template_id, template.as_json())
        tags = [{'Key': 'Environment', 'Value': environment}]
        if service:
            tags.append({'Key': 'Service', 'Value': service})

        try:
            result = self._client.create_stack(StackName=template.name,
                                               TemplateURL=url,
                                               Tags=tags)
        except exceptions.ClientError as error:
            self._s3.delete(template_id)
            raise RequestException(error)

        LOGGER.debug('Created stack ID: %r', result['StackId'])
        return result['StackId']

    def update_stack(self, template, environment, service=None):
        """Update a stack in the specified region with the given template.

        :param Template template: The template to use
        :param str environment: The environment to set in a stack tag
        :param str|None service: The service name to set in a stack tag
        :raises: RequestException

        """
        template_id = str(uuid.uuid4())
        url = self._s3.upload(template_id, template.as_json())
        tags = [{'Key': 'Environment', 'Value': environment}]
        if service:
            tags.append({'Key': 'Service', 'Value': service})

        try:
            result = self._client.update_stack(StackName=template.name,
                                               TemplateURL=url,
                                               Tags=tags)
        except exceptions.ClientError as error:
            self._s3.delete(template_id)
            raise RequestException(error)

        LOGGER.debug('Updated stack ID: %r', result['StackId'])


class RequestException(Exception):
    def __init__(self, error):
        self._message = error.response['Error']['Message']

    def __repr__(self):
        return '<{0} "{1}">'.format(self._message)

    def __str__(self):
        return self._message
