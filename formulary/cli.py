"""
Formulary Command Line Interface

"""
import argparse

from formulary import __version__
from formulary import network

DESCRIPTION = 'AWS Cloud Formation Stack Management'


def _add_commands(parser):
    commands = parser.add_subparsers(title='Commands', dest='command')

def run():

    parser = argparse.ArgumentParser(description=DESCRIPTION)
    _add_commands(parser)

    try:
        args = parser.parse_args()
    except IOError as error:
        exit('Error opening file: {0}'.format(error))

    obj = network.Network('staging-us-east-1',
                          '/Users/gavinr/Source/formulary/config')
    print(obj.as_json())
