VPC Configuration
=================
Formulary requires at least one configured VPC to work.


Options
-------

+---------------+---------+---------------------------+
| Variable Name | Type    | Default                   |
+===============+=========+===========================+
| description   | String  | ``Formulary created VPC`` |
+---------------+---------+---------------------------+
| dns-support   | Boolean | ``True``                  |
+---------------+---------+---------------------------+
| cidr          | String  | ``192.168.0.0/16``        |
+---------------+---------+---------------------------+
| dns-support   | Boolean | ``True``                  |
+---------------+---------+---------------------------+
| dns-hostnames | Boolean | ``True``                  |
+---------------+---------+---------------------------+
| region        | String  | ``us-east-1``             |
+---------------+---------+---------------------------+
| s3bucket      | String  | None                      |
+---------------+---------+---------------------------+
| tenancy       | String  | ``default``               |
+---------------+---------+---------------------------+
| dhcp-options  | Map     | See DHCP Options          |
+---------------+---------+---------------------------+
| network-acls  | Array   | See Network ACLs          |
+---------------+---------+---------------------------+
| subnets       | Map     | See Subnets               |
+---------------+---------+---------------------------+

DHCP Options
````````````
+----------------------+-----------------+---------------------------+
| Variable Name        | Type            | Default Value             |
+======================+=================+===========================+
| domain-name          | String          | None                      |
+----------------------+-----------------+---------------------------+
| name-servers         | List of Strings | [ ``AmazonProvidedDNS`` ] |
+----------------------+-----------------+---------------------------+
| netbios-name-servers | List of Strings | None                      |
+----------------------+-----------------+---------------------------+
| netbios-node-type    | Integer         | None                      |
+----------------------+-----------------+---------------------------+
| ntp-servers          | List of String  | None                      |
+----------------------+-----------------+---------------------------+
| tags                 | Map             | None                      |
+----------------------+-----------------+---------------------------+

Network ACLs
````````````
+----------------------+-----------------+---------------------------+
| Variable Name        | Type            | Default Value             |
+======================+=================+===========================+
| cidr          | String          | No default
| egress        | Boolean          | ``False``
| protocol      | Integer
| action        | | ``allow``
| number        | Integer | ACL position if not specified
| ports         | String | 0-65535

Subnets
```````
+-------------------+--------+
| Variable Name     | Type   |
+===================+========+
| availability-zone | String |
+-------------------+--------+
| cidr              | String |
+-------------------+--------+

Example
-------

.. code:: yaml

    %YAML 1.2
    ---
    description: Amazon US-East-1 Testing Network Stack
    cidr: 192.168.0.0/16
    dns-hostnames: true
    dns-support: true
    tenancy: default
    region: us-east-1
    s3bucket: tld.domain.formulary-test

    dhcp-options:
      domain-name: ec2.internal
      name-servers:
        - AmazonProvidedDNS
      ntp-servers:
        - 208.75.89.4
        - 132.163.4.102
        - 66.79.167.34
        - 204.2.134.164

    network-acls:
      - cidr: 0.0.0.0/0
        egress: false
        protocol: -1
        action: allow
        number: 100
        ports: 0-65535
      - cidr: 0.0.0.0/0
        egress: true
        protocol: -1
        action: allow
        number: 100
        ports: 0-65535

    subnets:
      a:
        availability_zone: us-east-1a
        cidr: 10.10.0.0/18
      b:
        availability_zone: us-east-1b
        cidr: 10.10.64.0/18
      d:
        availability_zone: us-east-1d
        cidr: 10.10.128.0/18
      e:
        availability_zone: us-east-1e
        cidr: 10.10.192.0/18
