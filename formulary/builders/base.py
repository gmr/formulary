"""
Base Builder Class

"""
import uuid

from formulary import s3
from formulary import template
from formulary import utils
from formulary.resources import cloudformation


class Builder(object):
    """Build CloudFormation stack templates"""
    def __init__(self, config, name):
        """Create a new instance of the stack builder

        :param fomulary.builders.Config config: Stack configuration
        :param str name: The name of the builder/stack resource

        """
        self._config = config
        self._environment = config.environment
        self._name = name
        self._outputs = []
        self._parameters = []
        self._resources = []
        self._templates = []

    def add_output(self, name, description, value):
        """Add an output that will be added to the template

        :param str name: The name of the output
        :param str|dict value: The value of the output

        """
        return self._add_output(name, description, value)

    def add_parameter(self, name, value):
        """Add a parameter that will be added to the template

        :param str name: The name of the parameter
        :param str|dict value: The value of the parameter

        """
        return self._add_parameter(name, value)

    def add_resource(self, name, resource):
        """Add a resource to the template, returning the cloud formation
        template reference name for the resource.

        :param str name: The underscore delimited resource name
        :param Resource resource: The resource to add
        :rtype: str

        """
        return self._add_resource(name, resource)

    @property
    def environment(self):
        """Return the environment value

        :rtype: str

        """
        return self._environment

    @property
    def full_name(self):
        """Return the builder's full name

        :rtype: str

        """
        if '-' in self.name:
            return self.name
        return '-'.join([self._config.service, self.name])

    @property
    def mappings(self):
        """Return the mappings dictionary for the builder

        :rtype: dict

        """
        return self._config.mappings

    @property
    def name(self):
        """Return the builder's resource name

        :rtype: str

        """
        return self._name

    @property
    def outputs(self):
        """Return the outputs dictionary for the builder

        :rtype: list

        """
        return self._outputs

    @property
    def parameters(self):
        """Return the parameters dictionary for the builder

        :rtype: list

        """
        return self._parameters

    @property
    def logical_id(self):
        return self.name

    @property
    def reference_id(self):
        """Return the camel case reference ID for the builder

        :rtype: str

        """
        return utils.camel_case(self.name)

    @property
    def resources(self):
        """Return the resource dictionary for the builder

        :rtype: list

        """
        return [(k, v.as_dict() if not isinstance(v, dict) else v) for k,v in self._resources]

    def upload(self, owner):
        """Upload a template for this builder to S3, returning the ID and
        the URL to the template

        :rtype: str, str

        """
        stack = template.Template(self._name)
        stack.set_description('Nested {0} stack owned by the '
                              '{1}-{2} stack'.format(self.__class__.__name__,
                                                     self.environment, owner))
        stack.update_mappings(self._config.mappings)
        stack.update_outputs(self.outputs)
        stack.update_parameters(self.parameters)
        stack.update_resources(self.resources)
        value = stack.as_json()
        template_id = str(uuid.uuid4())

        s3client = s3.S3(self._config.s3_bucket,
                         self._config.s3_prefix,
                         self._config.profile)
        return template_id, s3client.upload(template_id, value)

    def _add_output(self, name, description, value):
        """Add an output that will be added to the template

        :param str name: The name of the output
        :param str description: The description of the output
        :param str|dict value: The value of the output

        """
        output = {'Description': description, 'Value': value}
        self._outputs.append((name, output))

    def _add_parameter(self, name, value):
        """Add an parameter that will be added to the template

        :param str name: The name of the parameter
        :param str|dict value: The value of the parameter

        """
        self._parameters.append((name, value))

    def _add_resource(self, name, resource):
        """Add a resource to the template, returning the cloud formation
        template reference name for the resource.

        :param str name: The underscore delimited resource name
        :param Resource resource: The resource to add
        :rtype: str

        """
        resource_id = utils.camel_case(name)
        self._resources.append((resource_id, resource))
        return resource_id

    def _add_stack(self, name, template_url, parameters=None,
                   timeout=None, notifications=None, dependency=None):
        """Add a stack

        :param str template_url: URL to the stack to add
        :param dict parameters: Parameters to pass into the stack
        :param int timeout: Time out duration in minutes
        :param list notifications: A list of notification ARNs for the stack

        """
        stack = cloudformation.Stack(template_url, parameters,
                                     notifications, timeout)
        if dependency:
            stack.set_dependency(dependency)
        self._add_resource(name, stack)

    def _add_tag_to_resources(self, tag, value):
        for (k, resource) in self._resources:
            resource.add_tag(tag, value)

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
            return self._config.mappings[ref[0]][ref[1]][ref[2]]
        return value

    @property
    def _tags(self):
        return {'Environment': self._config.environment,
                'Service': self._config.service}
