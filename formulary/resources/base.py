"""
Base Resource and Property Classes

"""

class Property(object):
    """Cloud Formation Resource Property

    Represents a property of a Cloud Formation resource

    """
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
    tags = True

    def __init__(self, resource_type):
        """Create a new resource specifying the resource type

        :param str resource_type: Resource type such as ``AWS::EC2::Route``

        """
        self._attributes = {}
        self._dependency = None
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
        if self._tags and self.tags is True:
            dict_val['Properties']['Tags'] = []
            for key, value in self._tags.items():
                dict_val['Properties']['Tags'].append({'Key': key,
                                                       'Value': value})
            if self._name:
                dict_val['Properties']['Tags'].append({'Key': 'Name',
                                                       'Value': self._name})
        for key, value in self._attributes.items():
            dict_val[key] = value
        if self._dependency:
            dict_val['DependsOn'] = self._dependency
        if not dict_val['Properties']:
            del dict_val['Properties']
        return dict_val

    def set_dependency(self, dependency):
        """Set a dependency for the resource to be created

        :param str|dict dependency: The dependency name or reference

        """
        self._dependency = dependency

    def set_name(self, name):
        """Set the resource name for use as a tag

        :param str name: The resource name

        """
        self._name = name

    def _prune_empty_properties(self):
        for key, value in list(self._properties.items()):
            if self._properties[key] is None:
                del self._properties[key]


class CPResource(Resource):
    """CPResources are resources that support Creation Policies"""
    def __init__(self, resource_type):
        super(CPResource, self).__init__(resource_type)
        self._policy = {}

    def as_dict(self):
        """Return the resource as a dictionary for building the cloud-formation
        configuration.

        :return: dict

        """
        dict_val = super(CPResource, self).as_dict()
        if self._policy:
            dict_val['CreationPolicy'] = dict(self._policy)
        return dict_val

    def set_handle(self, handle):
        self._properties['Handle'] = handle

    def set_timeout(self, timeout):
        self._properties['Timeout'] = timeout

    def set_creation_policy(self, signal_count, timeout):
        """Set a dependency for the resource to be created

        :param str dependency: The dependency name or reference

        """
        self._policy = {'ResourceSignal':
                            {'Count': signal_count,
                             'Timeout': timeout}}
