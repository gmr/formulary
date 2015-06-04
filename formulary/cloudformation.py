"""
Cloud Formation methods and interfaces

"""
import collections
import json
import logging
from os import path

import arrow
from boto import cloudformation
from boto import exception
from dateutil import tz
import yaml

LOGGER = logging.getLogger(__name__)

StackResource = collections.namedtuple('StackResource',
                                       ('id', 'type', 'name', 'status'))


def create_stack(region, template):
    """Create a stack in the specified region with the given template.

    :param str region: The region name to create the stack in
    :param Template template: The template to use
    :raises: RequestException

    """
    connection = cloudformation.connect_to_region(region)
    template_body = template.as_json()
    if not connection.validate_template(template_body):
        raise RequestException('The specified template did not validate')
    try:
        connection.create_stack(template.name, template_body)
    except exception.BotoServerError as error:
        raise RequestException(error)
    connection.close()


def update_stack(region, template):
    """Update a stack in the specified region with the given template.

    :param str region: The region name to create the stack in
    :param Template template: The template to use
    :raises: RequestException

    """
    connection = cloudformation.connect_to_region(region)
    template_body = template.as_json()
    if not connection.validate_template(template_body):
        raise RequestException('The specified template did not validate')
    try:
        connection.update_stack(template.name, template_body)
    except exception.BotoServerError as error:
        raise RequestException(error)
    connection.close()


class Stack(object):
    """Represents a Cloud Formation Stack. This is meant to be extended by
    more specific ``Stack`` classes such as the
    ``formulary.network.NetworkStack``

    """
    def __init__(self, name, region='us-east-1'):
        """Create a new instance of a Stack for the given region and stack name

        :param str name: The stack name
        :param str region: The AWS region, defaults to ``us-east-1``

        """
        self._name = name
        self._connection = cloudformation.connect_to_region(region)
        self._stack = self._fetch_description()
        self._resources = self._fetch_resources()

    @property
    def created_at(self):
        """When the Cloud Formation stack was created

        :rtype: datetime.datetime

        """
        return arrow.get(self._stack.creation_time, tz.tzutc()).datetime

    @property
    def description(self):
        """Return the stack description

        :rtype: str

        """
        return self._stack.description

    @property
    def id(self):
        """Return the stack id

        :rtype: str

        """
        return self._stack.stack_id

    @property
    def name(self):
        """Return the stack name

        :rtype: str

        """
        return self._name

    @property
    def status(self):
        """Return the stack status

        :rtype: str

        """
        return self._stack.stack_status

    @property
    def updated_at(self):
        """When the Cloud Formation stack was last updated

        :rtype: datetime.datetime

        """
        return arrow.get(self._stack.LastUpdatedTime).datetime

    def _fetch_description(self):
        result = self._connection.describe_stacks(self._name)
        return result[0]

    def _fetch_resources(self):
        resources = []
        for resource in self._connection.describe_stack_resources(self._name):
            resources.append(StackResource(resource.physical_resource_id,
                                           resource.resource_type,
                                           resource.logical_resource_id,
                                           resource.resource_status))
        return resources


class Template(object):
    """Used to create a Cloud Formation configuration template"""
    CONFIG_PREFIX = ''
    PARENT_CONFIG_PREFIX = 'vpcs'

    def __init__(self, name, parent, config_path):
        """Create a new Cloud Formation configuration template instance"""
        self._config_path = config_path
        self._description = 'Formulary created Cloud Formation stack'
        self._name = name
        self._parent = parent

        self._conditions = {}
        self._mappings = self._load_mappings()
        self._metadata = {}
        self._outputs = {}
        self._parameters = {}
        self._resources = {}

    def add_resource(self, resource_id, resource):
        """Add a resource to the template

        :param str resource_id: The camelCase resource_id
        :param Resource resource: The resource to add

        """
        self._resources[resource_id] = resource

    def as_json(self, indent=2):
        """Return the cloud-formation template as JSON

        :param int indent: spaces to indent the JSON by

        """
        resources = dict({})
        for key, value in self._resources.items():
            resources[key] = value.as_dict()
        return json.dumps({'AWSTemplateFormatVersion': '2010-09-09',
                           'Conditions': self._conditions,
                           'Description': self._description,
                           'Mappings': self._mappings,
                           'Metadata': self._metadata,
                           'Outputs': self._outputs,
                           'Parameters': self._parameters,
                           'Resources': resources},
                          indent=indent, sort_keys=True)

    @property
    def name(self):
        """Return the template name to use when creating a stack.

        :rtype: str

        """
        return self._name

    def set_description(self, description):
        """Set the template description

        :param str description: The description value
        """
        self._description = description

    def update_mappings(self, mappings):
        """Update the template's mappings with values from another mapping
        dictionary.

        :param dict mappings: Additional mappings to add

        """
        self._mappings.update(mappings)

    @staticmethod
    def _load_config(cfg_path, name):
        """Load YAML configuration for the specified name from the path.

        :param str cfg_path: The path prefix for the config file
        :param str name: The name of the config file
        :rtype: dict

        """
        config_file = path.normpath(path.join(cfg_path,
                                              '{0}.yaml'.format(name)))
        LOGGER.debug('Loading configuration from %s', config_file)
        if path.exists(config_file):
            with open(config_file) as handle:
                return yaml.load(handle)

    def _load_mappings(self):
        """Load the mapping files for the template, pulling in first the top
        level mappings, then the environment specific VPC mappings.

        :rtype: dict

        """
        mappings = self._load_config(self._config_path, 'mapping') or {}
        mappings.update(self._load_config(self._parent_path, 'mapping') or {})
        mappings.update(self._load_config(self._local_path, 'mapping') or {})
        return mappings

    @property
    def _local_path(self):
        """Return a path to the config file local to the Template type being
        created.

        :rtype: str

        """
        return path.join(self._config_path, self.CONFIG_PREFIX, self.name)

    @property
    def _parent_path(self):
        """Return the path to the parent template, if set

        :rtype: str|None

        """
        return path.join(self._config_path, self.PARENT_CONFIG_PREFIX,
                         self._parent) if self._parent else ''


class Resource(object):
    """Cloud Formation Resource

    Represents a Cloud Formation resource as a class

    """
    def __init__(self, resource_type):
        """Create a new resource specifying the resource type

        :param str resource_type: Resource type such as ``AWS::EC2::Route``

        """
        self._attributes = {}
        self._name = None
        self._properties = {}
        self._tags = {}
        self._type = resource_type

    def add_attribute(self, name, value):
        """Add a top-level attribute to the resource such as ``DependsOn`` in
        ``AWS::EC2::Route``

        :param str name: The attribute name
        :param str value: The attribute value

        """
        self._attributes[name] = value

    def add_property(self, name, value):
        """Add a property to the resource

        :param str name: The name of the property
        :param str|dict|list|bool|int value: The property value

        """
        self._properties[name] = value

    def add_tag(self, name, value):
        """Add a tag to the resource

        :param str name: The name of the tag
        :param str value: The tag value

        """
        self._tags[name] = value

    def as_dict(self):
        """Return the resource as a dictionary for building the cloud-formation
        configuration.

        :return: dict

        """
        dict_val = dict({'Type': self._type, 'Properties': self._properties})
        if self._tags:
            dict_val['Properties']['Tags'] = []
            for key, value in self._tags.items():
                dict_val['Properties']['Tags'].append(
                    {'Key': key,
                     'Value': value})
            if self._name:
                dict_val['Properties']['Tags'].append(
                    {'Key': 'Name',
                     'Value': self._name})
        for key, value in self._attributes.items():
            dict_val[key] = value
        return dict_val

    def set_name(self, name):
        """Set the resource name for use as a tag

        :param str name: The resource name

        """
        self._name = name


class RequestException(Exception):
    def __init__(self, error):
        error = str(error)
        payload = json.loads(error[error.find('{'):])
        self._message = payload['Error']['Message']

    def __repr__(self):
        return '<{0} "{1}">'.format(self._message)

    def __str__(self):
        return self._message
