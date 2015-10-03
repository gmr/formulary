"""
Base CloudFormation Stack

"""
import uuid

import troposphere

from formulary import utils


class Stack(object):
    """Stack objects are responsible for creating a CloudFormation stack
    template.

    """

    def __init__(self, config, name, vpc):
        """Create a new instance of the Stack

        :param dict config: Stack configuration
        :param str name: The stack name
        :param str vpc: The VPC name

        """
        self._id = uuid.uuid4().hex
        self._config = config
        self._name = name
        self._vpc = vpc
        self._template = troposphere.Template()
        self._template.add_version()

    @property
    def id(self):
        """Return a UUID for this stack

        :rtype: str

        """
        return self._id

    @property
    def name(self):
        """Return the name of the stack

        :rtype: str

        """
        return self._name

    @property
    def ref(self):
        """Return the ref name for the stack. If the name is foo-bar-baz,
        the ref name will be FooBarBaz.

        :rtype: str

        """
        return utils.camel_case(self._name)

    @property
    def resources(self):
        """Return the resources associated with the stack

        :rtype: list

        """
        return self._template.resources

    @property
    def service(self):
        return None

    def to_json(self, indent=None):
        """Return the stack template as JSON

        :param int indent: Indent the JSON with the specified number of spaces
        :rtype: str

        """
        return self._template.to_json(indent)

    @property
    def vpc(self):
        """Return the VPC name

        :rtype: str

        """
        return self._vpc

    def _add_output(self, output):
        """Add an output to the template

        :param troposphere.Output output: The output to add to the template

        """
        self._template.add_output(output)

    def _add_parameter(self, parameter):
        """Add a parameter to the template

        :param troposphere.Parameter: The parameter to add to the template

        """
        self._template.add_parameter(parameter)

    def _add_resource(self, resource):
        """Add a resource to the template

        :param troposphere.AWSObject resource: The resource to add

        """
        self._template.add_resource(resource)
