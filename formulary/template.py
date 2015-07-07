"""
Cloud Formation Template

"""
import collections
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
        self._outputs = []
        self._parameters = []
        self._resources = []

    def add_output(self, name, description, reference):
        """Add an output to the template

        :param str name: The name of the output
        :param str description: The description of the output
        :param str reference: The object to reference

        """
        self._outputs.append((name, {'Description': description,
                                     'Value': {'Ref': reference}}))

    def add_resource(self, resource_id, resource):
        """Add a resource to the template

        :param str resource_id: The camelCase resource_id
        :param Resource resource: The resource to add

        """
        self._resources.append((resource_id, resource))

    def as_json(self, indent=2):
        """Return the cloud-formation template as JSON

        :param int indent: spaces to indent the JSON by

        """
        value = collections.OrderedDict([
            ('AWSTemplateFormatVersion', '2010-09-09'),
            ('Conditions', self._conditions),
            ('Description', self._description),
            ('Mappings', self._mappings),
            ('Metadata', self._metadata),
            ('Outputs', collections.OrderedDict(self._outputs)),
            ('Parameters', collections.OrderedDict(self._parameters)),
            ('Resources', collections.OrderedDict(self._resources))])

        return json.dumps(value, indent=indent, sort_keys=False)

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

    def update_outputs(self, outputs):
        """Update the outputs with values from another dict.

        :param list outputs: Additional outputs to add

        """
        self._outputs += outputs

    def update_parameters(self, parameters):
        """Update the parameters with values from another dict.

        :param list parameters: Dict of parameters to merge in

        """
        self._parameters += parameters

    def update_resources(self, resources):
        """Update the resources with the resources from another dict.

        :param list resources: Additional resources to add

        """
        self._resources += resources
