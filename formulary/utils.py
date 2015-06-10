"""
Common Utility Methods

"""
DEFAULT_PROTOCOL = 'tcp'


def camel_case(value):
    """Convert a underscore or dash delimited value to camelCase

    :param str value: The value to convert
    :rtype: str

    """
    return ''.join(x.capitalize() for x in value.replace('-', '_').split('_'))


def find_in_map(value):
    """If the value is a ^map macro, replace it with a Cloud Formation
    Formation ``Fn::FindInMap`` function, splitting up the period delimited
    reference. For example if a value is ``^map Foo.Bar.Baz`` it will be
    returned as ``dict({'Fn::FindInMap': ['Foo', 'Bar', Baz'})``.

    :param str value: The value to check for the map macro
    :rtype: str|dict
    :raises: ValueError

    """
    if value.startswith('^map '):
        ref = value[5:].split('.')
        if len(ref) != 3:
            raise ValueError('Invalid map reference: {}'.format(value[5:]))
        return {'Fn::FindInMap': ref}
    return value


def parse_port_value(value, default_protocol=None):
    """Parse a string containing port information and return a normalized
    tuple of ``protocol``, ``from_port``, and ``to_port``.

    :param str|int value: The value to parse
    :return: str, int, int

    """
    if isinstance(value, int):
        return default_protocol or DEFAULT_PROTOCOL, value, value

    protocol = default_protocol or DEFAULT_PROTOCOL
    from_port, to_port = value, value

    if '-' in value:
        from_port, to_port = value.split('-')
        from_protocol, to_protocol = None, None
        if '/' in from_port:
            from_port, from_protocol = from_port.split('/')
        if '/' in to_port:
            to_port, to_protocol = to_port.split('/')
        protocol = (from_protocol or to_protocol or
                    default_protocol or DEFAULT_PROTOCOL)

    elif '/' in value:
        port, protocol = value.split('/')
        from_port, to_port = port, port

    if isinstance(protocol, str):
        protocol = protocol.lower()

    return protocol, int(from_port), int(to_port)
