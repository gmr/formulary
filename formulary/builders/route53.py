"""
Build the resources for a RDS Instance

"""
from formulary.builders import base
from formulary.resources import route53


class Route53RecordSet(base.Builder):

    def __init__(self, config, name, settings, instances=None):
        super(Route53RecordSet, self).__init__(config, name)
        self._add_parameter('DNSName', {'Type': 'String'})
        self._add_parameter('HostedZoneId', {'Type': 'String'})
        if instances:
            self._add_instance_rr(settings, instances)
        else:
            self._add_alias_record(settings)

    def _add_alias_record(self, settings):
        alias = route53.Route53AliasTarget({'Ref': 'DNSName'},
                                           {'Ref': 'HostedZoneId'})
        self._add_resource('route53-{0}-a'.format(settings['hostname']),
                           route53.Route53RecordSet(settings['domain_name'],
                                                    settings['hostname'], None,
                                                    alias.as_dict(), 'A'))

    def _add_instance_rr(self, settings, instances):
        for instance in instances:
            self._add_parameter(instance, {'Type': 'String'})
        resources = [{'Ref': ref_id} for ref_id in instances]
        self._add_resource('route53-{0}-a'.format(settings['hostname']),
                           route53.Route53RecordSet(settings['domain_name'],
                                                    settings['hostname'],
                                                    resources, None, 'A'))
