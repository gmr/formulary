"""
Interface for creating Cloud-Formation configuration and submitting it

"""
import json


class Template(object):
    """Used to create a Cloud-Formation configuration template.

    """

    def __init__(self):
        self._mappings = {}
        self._outputs = {}
        self._parameters = {}
        self._resources = {}

    def add_resource(self, name, resource):
        """
        """
        self._resources[name] = resource

    def as_json(self, indent=2):
        """Return the cloud-formation template as JSON

        :param int indent: spaces to indent the JSON by

        """
        resources = dict({})
        for key, value in self._resources.items():
            resources[key] = value.as_dict()
        return json.dumps({'AWSTemplateFormatVersion': '2010-09-09',
                           'Mappings': self._mappings,
                           'Outputs': self._outputs,
                           'Parameters': self._parameters,
                           'Resources': resources},
                          indent=indent, sort_keys=True)

    def update_mappings(self, mappings):
        """
        """
        self._mappings.update(mappings)


class Resource(object):
    """
    Used for creating a cloud formation resource

    """
    def __init__(self, resource_type):
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
        dict_val = dict({'Type': self._type,
                         'Properties': self._properties})
        if self._tags:
            dict_val['Properties']['Tags'] = []
            for key, value in self._tags.items():
                dict_val['Properties']['Tags'].append({'Key': key,
                                                       'Value': value})
            if self._name:
                dict_val['Properties']['Tags'].append({'Key': 'Name',
                                                       'Value': self._name})
        for key, value in self._attributes.items():
            dict_val[key] = value
        return dict_val

    def set_name(self, name):
        """Set the resource name for use as a tag

        :param str name: The resource name

        """
        self._name = name
