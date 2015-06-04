"""
Interface for creating Cloud Formation configuration and submitting it

"""
import collections
import json

import arrow
from boto import cloudformation
from dateutil import tz

StackResource = collections.namedtuple('StackResource',
                                       ('id', 'type', 'name', 'status'))


def create_stack(region, template):
    """Create a stack in the specified region with the given template.

    :param str region: The region name to create the stack in
    :param Template template: The template to use

    """
    connection = cloudformation.connect_to_region(region)
    template_body = template.as_json()
    if not connection.validate_template(template_body):
        raise ValueError('The specified template did not validate')
    connection.create_stack(template.name, template_body)
    connection.close()


def update_stack(region, template):
    """Create a stack in the specified region with the given template.

    :param str region: The region name to create the stack in
    :param Template template: The template to use

    """
    connection = cloudformation.connect_to_region(region)
    template_body = template.as_json()
    if not connection.validate_template(template_body):
        raise ValueError('The specified template did not validate')
    connection.update_stack(template.name, template_body)
    connection.close()


def describe_stack(region, stack_name):
    connection = cloudformation.connect_to_region(region)
    print(connection.describe_stacks(stack_name))
    print(connection.describe_stack_resources(stack_name))
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

    def __init__(self, name):
        """Create a new Cloud Formation configuration template instance"""
        self._name = name
        self._description = 'Formulary created Cloud Formation stack'
        self._conditions = {}
        self._mappings = {}
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
