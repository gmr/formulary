"""
Cloud Formation Template

"""
import json


class Template(object):
    """Used to create a Cloud Formation configuration template"""
    PARENT_CONFIG_PREFIX = ''
    STACK_TYPE = ''

    def __init__(self, name):
        """Create a new Cloud Formation configuration template instance"""
        self._description = 'Formulary created Cloud Formation stack'
        self._name = name

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
        """Return the template name

        :rtype: str

        """
        return self._name

    def set_description(self, description):
        """Set the template description

        :param str description: The description value
        """
        self._description = description

    def update_mappings(self, mappings):
        """Update the mappings with values from another dict.

        :param dict mappings: Additional mappings to add

        """
        self._mappings.update(mappings)

    def update_resources(self, resources):
        """Update the resources with the resources from another dict.

        :param dict resources: Additional resources to add

        """
        self._resources.update(resources)
