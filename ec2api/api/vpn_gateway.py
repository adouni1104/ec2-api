# Copyright 2014
# The Cloudscaling Group, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from ec2api.api import common
from ec2api.api import ec2utils
from ec2api.db import api as db_api
from ec2api import exception
from ec2api.i18n import _


Validator = common.Validator


def create_vpn_gateway(context, type, availability_zone=None):
    vpn_gateway = db_api.add_item(context, 'vgw', {})
    return {'vpnGateway': _format_vpn_gateway(vpn_gateway)}


def attach_vpn_gateway(context, vpc_id, vpn_gateway_id):
    vpn_gateway = ec2utils.get_db_item(context, vpn_gateway_id)
    vpc = ec2utils.get_db_item(context, vpc_id)
    if vpn_gateway['vpc_id'] and vpn_gateway['vpc_id'] != vpc['id']:
        raise exception.VpnGatewayAttachmentLimitExceeded()
    attached_vgw = next((gw for gw in db_api.get_items(context, 'vgw')
                         if (gw['id'] != vpn_gateway['id'] and
                             gw['vpc_id'] == vpc['id'])), None)
    if attached_vgw:
        raise exception.InvalidVpcState(vpc_id=vpc['id'],
                                        vgw_id=attached_vgw['id'])

    if not vpn_gateway['vpc_id']:
        vpn_gateway['vpc_id'] = vpc['id']
        db_api.update_item(context, vpn_gateway)

    return {'attachment': _format_attachment(vpn_gateway)}


def detach_vpn_gateway(context, vpc_id, vpn_gateway_id):
    vpn_gateway = ec2utils.get_db_item(context, vpn_gateway_id)
    if vpn_gateway['vpc_id'] != vpc_id:
        raise exception.InvalidVpnGatewayAttachmentNotFound(
            vgw_id=vpn_gateway_id, vpc_id=vpc_id)

    vpn_gateway['vpc_id'] = None
    db_api.update_item(context, vpn_gateway)
    return True


def delete_vpn_gateway(context, vpn_gateway_id):
    vpn_gateway = ec2utils.get_db_item(context, vpn_gateway_id)
    vpn_connections = db_api.get_items(context, 'vpn')
    if vpn_gateway['vpc_id']:
        raise exception.IncorrectState(reason=_('The VPN gateway is in use.'))
    db_api.delete_item(context, vpn_gateway['id'])
    return True


def describe_vpn_gateways(context, vpn_gateway_id=None, filter=None):
    formatted_vgws = VpnGatewayDescriber().describe(
        context, ids=vpn_gateway_id, filter=filter)
    return {'vpnGatewaySet': formatted_vgws}


class VpnGatewayDescriber(common.TaggableItemsDescriber,
                          common.NonOpenstackItemsDescriber):

    KIND = 'vgw'
    FILTER_MAP = {'attachment.state': ['attachments', 'state'],
                  'attachment.vpc-id': ['attachments', 'vpcId'],
                  'state': 'state',
                  'type': 'type',
                  'vpn-gateway-id': 'vpnGatewayId'}

    def format(self, vpn_gateway):
        return _format_vpn_gateway(vpn_gateway)


def _format_vpn_gateway(vpn_gateway):
    ec2_vgw = {'vpnGatewayId': vpn_gateway['id'],
               'state': 'available',
               'type': 'ipsec.1',
               'attachments': []}
    if vpn_gateway['vpc_id']:
        ec2_vgw['attachments'].append(_format_attachment(vpn_gateway))
    return ec2_vgw


def _format_attachment(vpn_gateway):
    return {'state': 'attached',
            'vpcId': vpn_gateway['vpc_id']}
