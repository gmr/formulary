"""
Build the resources for a RDS Instance

"""
from formulary.builders import base
from formulary.resources import route53
from formulary import utils


class Route53RecordSet(base.Builder):

    def __init__(self, config, name, settings):
        super(Route53RecordSet, self).__init__(config, name)

        alias_target = route53.Route53AliasTarget({'Ref': 'DNSName'},
                                                  {'Ref': 'HostedZoneId'})

        self._add_parameter('DNSName', {'Ref': 'DNSName'})
        self._add_parameter('HostedZoneId', {'Ref': 'HostedZoneId'})

        self._add_resource('route53-{0}-a'.format(settings['hostname']),
                           route53.Route53RecordSet(settings['domain_name'],
                                                    settings['hostname'], None,
                                                    alias_target.as_dict(),
                                                    'A'))
