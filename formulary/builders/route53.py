"""
Build the resources for a RDS Instance

"""
from formulary.builders import base
from formulary.resources import route53


class Route53RecordSet(base.Builder):

    def __init__(self, config, name, settings):
        super(Route53RecordSet, self).__init__(config, name)
        self._add_parameter('DNSName', {'Type': 'String'})
        self._add_parameter('HostedZoneId', {'Type': 'String'})
        alias = route53.Route53AliasTarget({'Ref': 'DNSName'},
                                           {'Ref': 'HostedZoneId'})
        self._add_resource('route53-{0}-a'.format(settings['hostname']),
                           route53.Route53RecordSet(settings['domain_name'],
                                                    settings['hostname'], None,
                                                    alias.as_dict(), 'A'))
