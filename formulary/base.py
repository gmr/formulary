"""
Base Classes

"""
import logging

from formulary import utils

LOGGER = logging.getLogger(__name__)


class Builder(object):
    def __init__(self, config, name, environment, mappings):
        self._config = self._flatten_config(config, environment)
        self._name = name
        self._environment = environment
        self._mappings = mappings
        self._resources = {}

    @property
    def environment(self):
        """Return the environment value

        :rtype: str

        """
        return self._environment

    @property
    def name(self):
        """Return the builder's resource name

        :rtype: str

        """
        return self._name

    @property
    def resources(self):
        """Return the resource dictionary for the builder"""
        return dict(self._resources)

    def _add_resource(self, name, resource):
        """Add a resource to the template, returning the cloud formation
        template reference name for the resource.

        :param str name: The underscore delimited resource name
        :param Resource resource: The resource to add
        :rtype: str

        """
        resource_id = utils.camel_case(name)
        self._resources[resource_id] = resource
        return resource_id

    @staticmethod
    def _flatten_config(config, environment):
        for key, value in config.items():
            if value == environment:
                config[key] = config[key][environment]
        return config

    def _maybe_replace_with_mapping(self, value):
        """If the value is a ^map macro, replace the with the value from the
        mappings dict. For example, if the value is ``^map Foo.Bar.Baz``
        return self._mappings['Foo']['Bar']['Baz'].

        :param str value: The value to check for the map macro
        :rtype: str|dict
        :raises: ValueError

        """
        if value.startswith('^map '):
            ref = value[5:].split('.')
            if len(ref) != 3:
                raise ValueError('Invalid map reference: {}'.format(value[5:]))
            return self._mappings[ref[0]][ref[1]][ref[2]]
        return value


class Property(object):
    def __init__(self):
        self._values = dict()

    def as_dict(self):
        values = dict(self._values)
        for key, value in self._values.items():
            if value is None or value == [] or value == {}:
                del values[key]
        return values


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
        self._prune_empty_properties()
        dict_val = dict({'Type': self._type, 'Properties': self._properties})
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

    def _prune_empty_properties(self):
        for key, value in list(self._properties.items()):
            if self._properties[key] is None:
                del self._properties[key]
