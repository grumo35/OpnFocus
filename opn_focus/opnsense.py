#!/usr/bin/env python3
import re
from datetime import datetime, timezone
from pprint import pformat

from opn_focus.util import DataNode, hasattr_r


class OPNsenseNode(DataNode):
    def __init__(self, parent=None):
        self._parent = parent

    def __getattr__(self, name):
        # This trick hides PyLint error messages...
        return super().__getattribute__(name)

    def __call__(self, content):
        pass # discard content

    def __repr__(self):
        return pformat(self.data)

    def __str__(self):
        return str(self.data)

    @property
    def parents(self):
        obj = self
        while obj._parent:
            yield obj._parent
            obj = obj._parent

    @property
    def rootdoc(self):
        return list(self.parents)[-1]

class OPNsenseString(OPNsenseNode):
    string = None

    def __call__(self, content):
        self.string = str(content)

    @property
    def data(self):
        return self.string

class OPNsenseInteger(OPNsenseNode):
    integer = None

    def __call__(self, content):
        self.integer = int(content)

    @property
    def data(self):
        return self.integer

class OPNsenseTimestamp(OPNsenseNode):
    datetime = None

    def __call__(self, content):
        self.datetime = datetime.fromtimestamp(float(content), timezone.utc)

    @property
    def data(self):
        return self.datetime

class OPNsenseInterfacesNode(OPNsenseNode):
    def __getattr__(self, name):
        if name.startswith('_opt'):
            return self._opt
        return super().__getattribute__(name)

class OPNsenseFlag(OPNsenseNode):
    @property
    def data(self):
        return True

class OPNsenseAliasString(OPNsenseString):
    @property
    def data(self):
        data = super().data
        if hasattr_r(self.rootdoc.opnsense, 'aliases.alias'):
            for alias in self.rootdoc.opnsense.aliases.alias:
                if alias.name.string == data:
                    return {'alias': alias.data}
        return data

class OPNsensePortString(OPNsenseAliasString):
    PORT_STRING = re.compile(r'(\d+((:|-)(\d+))?|[a-zA-Z0-9_]+)')

    def __call__(self, content):
        super().__call__(content)
        if self.PORT_STRING.fullmatch(self.string) is None:
            raise RuntimeError("Invalid port string: {}".format(self.string))

class OPNsenseChange(OPNsenseNode):
    _time = OPNsenseTimestamp
    _username = OPNsenseString

class OPNsenseRange(OPNsenseNode):
    _from = OPNsenseString
    _to = OPNsenseString

class OPNsenseSysCtlItem(OPNsenseNode):
    _tunable = OPNsenseString
    _value = OPNsenseString
    _descr = OPNsenseString

class OPNsenseSysCtl(OPNsenseNode):
    _item = [OPNsenseSysCtlItem]

class OPNsenseStaticMap(OPNsenseNode):
    _mac = OPNsenseString
    _ipaddr = OPNsenseString
    _hostname = OPNsenseString

class OPNsenseDhcpdItem(OPNsenseNode):
    _range = [OPNsenseRange]
    _staticmap = [OPNsenseStaticMap]
    _defaultleasetime = OPNsenseInteger
    _maxleasetime = OPNsenseInteger
    _enable = OPNsenseFlag

class OPNsenseDhcpd(OPNsenseInterfacesNode):
    _wan = OPNsenseDhcpdItem
    _lan = OPNsenseDhcpdItem
    _opt = OPNsenseDhcpdItem

class OPNsenseRuleAlias(OPNsenseString):
    @property
    def data(self):
        data = super().data
        for interface_name, interface_data in self.rootdoc.opnsense.interfaces.data.items():
            alias_name = data
            if alias_name.endswith('ip'):
                alias_name = alias_name[:-2]
            if interface_name == alias_name:
                interface_data['name'] = data
                return {'interface': interface_data}
        if hasattr_r(self.rootdoc.opnsense, 'aliases.alias'):
            for alias in self.rootdoc.opnsense.aliases.alias:
                if alias.name.string == data:
                    return {'alias': alias.data}
        return data

class OPNsenseRuleInterface(OPNsenseString):
    @property
    def data(self):
        data = super().data
        if data is None:
            return data
        data_list = []
        for iface_name in data.split(','):
            found = False
            for interface_name, interface_data in self.rootdoc.opnsense.interfaces.data.items():
                if interface_name == iface_name:
                    interface_data['name'] = iface_name
                    data_list.append({'interface': interface_data})
                    found = True
                    break
            if not found:
                data_list.append(iface_name)
        return data_list

class OPNsenseRuleLocation(OPNsenseNode):
    _any = OPNsenseNode
    _network = OPNsenseRuleAlias
    _address = OPNsenseRuleAlias
    _port = OPNsensePortString
    _not = OPNsenseFlag

class OPNsenseFilterRule(OPNsenseNode):
    _id = OPNsenseString
    _tracker = OPNsenseString
    _type = OPNsenseString
    _interface = OPNsenseRuleInterface
    _ipprotocol = OPNsenseString
    _tag = OPNsenseString
    _tagged = OPNsenseString
    _max = OPNsenseString
    _max_src_nodes = OPNsenseString
    _max_src_conn = OPNsenseString
    _max_src_states = OPNsenseString
    _statetimeout = OPNsenseString
    _statetype = OPNsenseString
    _os = OPNsenseString
    _protocol = OPNsenseString
    _source = OPNsenseRuleLocation
    _destination = OPNsenseRuleLocation
    _descr = OPNsenseString
    _associated_rule_id = OPNsenseString
    _created = OPNsenseChange
    _updated = OPNsenseChange
    _disabled = OPNsenseFlag

class OPNsenseFilter(OPNsenseNode):
    _rule = [OPNsenseFilterRule]

class OPNsenseNatOutboundRule(OPNsenseNode):
    _interface = OPNsenseRuleInterface
    _source = OPNsenseRuleLocation
    _dstport = OPNsensePortString
    _target = OPNsenseString
    _targetip = OPNsenseString
    _targetip_subnet = OPNsenseString
    _destination = OPNsenseRuleLocation
    _natport = OPNsensePortString
    _staticnatport = OPNsensePortString
    _descr = OPNsenseString
    _created = OPNsenseChange
    _updated = OPNsenseChange
    _disabled = OPNsenseFlag

class OPNsenseNatOutbound(OPNsenseNode):
    _mode = OPNsenseString
    _rule = [OPNsenseNatOutboundRule]

class OPNsenseNatRule(OPNsenseNode):
    _source = OPNsenseRuleLocation
    _destination = OPNsenseRuleLocation
    _protocol = OPNsenseString
    _target = OPNsenseRuleAlias
    _local_port = OPNsensePortString
    _interface = OPNsenseRuleInterface
    _descr = OPNsenseString
    _associated_rule_id = OPNsenseString
    _created = OPNsenseChange
    _updated = OPNsenseChange
    _disabled = OPNsenseFlag

class OPNsenseNat(OPNsenseNode):
    _outbound = OPNsenseNatOutbound
    _rule = [OPNsenseNatRule]

class OPNsenseAlias(OPNsenseNode):
    _name = OPNsenseString
    _type = OPNsenseString
    _address = OPNsenseString
    _descr = OPNsenseString
    _detail = OPNsenseString

class OPNsenseAliases(OPNsenseNode):
    _alias = [OPNsenseAlias]

class OPNsenseDnsMasqDomainOverride(OPNsenseNode):
    _domain = OPNsenseString
    _ip = OPNsenseString
    _idx = OPNsenseInteger
    _descr = OPNsenseString

class OPNsenseDnsMasqHostAliasItem(OPNsenseNode):
    _host = OPNsenseString
    _domain = OPNsenseString
    _description = OPNsenseString

class OPNsenseDnsMasqHostAliases(OPNsenseNode):
    _item = [OPNsenseDnsMasqHostAliasItem]

class OPNsenseDnsMasqHost(OPNsenseNode):
    _host = OPNsenseString
    _domain = OPNsenseString
    _ip = OPNsenseString
    _descr = OPNsenseString
    _aliases = OPNsenseDnsMasqHostAliases

class OPNsenseDnsMasq(OPNsenseNode):
    _enable = OPNsenseFlag
    _reqdhcp = OPNsenseFlag
    _reqdhcpstatic = OPNsenseFlag
    _strict_order = OPNsenseFlag
    _custom_options = OPNsenseString
    _interface = OPNsenseRuleInterface
    _hosts = [OPNsenseDnsMasqHost]
    _domainoverrides = [OPNsenseDnsMasqDomainOverride]

class OPNsenseOpenVpnClient(OPNsenseNode):
    _vpnid = OPNsenseInteger
    _auth_user = OPNsenseString
    _mode = OPNsenseString
    _protocol = OPNsenseString
    _dev_mode = OPNsenseString
    _interface = OPNsenseRuleInterface
    _ipaddr = OPNsenseString
    _local_port = OPNsenseInteger
    _server_addr = OPNsenseString
    _server_port = OPNsenseInteger
    _crypto = OPNsenseString
    _digest = OPNsenseString
    _tunnel_network = OPNsenseString
    _remote_network = OPNsenseString
    _local_network = OPNsenseString
    _topology = OPNsenseString
    _description = OPNsenseString
    _custom_options = OPNsenseString

class OPNsenseOpenVpnServer(OPNsenseNode):
    _vpnid = OPNsenseInteger
    _mode = OPNsenseString
    _authmode = OPNsenseString
    _protocol = OPNsenseString
    _dev_mode = OPNsenseString
    _interface = OPNsenseRuleInterface
    _ipaddr = OPNsenseString
    _local_port = OPNsenseInteger
    _crypto = OPNsenseString
    _digest = OPNsenseString
    _tunnel_network = OPNsenseString
    _remote_network = OPNsenseString
    _local_network = OPNsenseString
    _dynamic_ip = OPNsenseString
    _pool_enable = OPNsenseString
    _topology = OPNsenseString
    _description = OPNsenseString
    _custom_options = OPNsenseString

class OPNsenseOpenVpnCsc(OPNsenseNode):
    _server_list = OPNsenseString
    _common_name = OPNsenseString
    _description = OPNsenseString
    _tunnel_network = OPNsenseString

class OPNsenseOpenVpn(OPNsenseNode):
    _openvpn_server = [OPNsenseOpenVpnServer]
    _openvpn_client = [OPNsenseOpenVpnClient]
    _openvpn_csc = [OPNsenseOpenVpnCsc]

class OPNsenseRoute(OPNsenseNode):
    _network = OPNsenseString
    _gateway = OPNsenseString
    _descr = OPNsenseString

class OPNsenseStaticRoutes(OPNsenseNode):
    _route = [OPNsenseRoute]

class OPNsenseGatewayItem(OPNsenseNode):
    _interface = OPNsenseRuleInterface
    _gateway = OPNsenseString
    _name = OPNsenseString
    _weight = OPNsenseInteger
    _ipprotocol = OPNsenseString
    _interval = OPNsenseInteger
    _alert_interval = OPNsenseInteger
    _descr = OPNsenseString
    _defaultgw = OPNsenseFlag

class OPNsenseGateways(OPNsenseNode):
    _gateway_item = [OPNsenseGatewayItem]

class OPNsenseVlan(OPNsenseNode):
    _vlanif = OPNsenseString
    _tag = OPNsenseInteger
    _if = OPNsenseString
    _descr = OPNsenseString

class OPNsenseVlans(OPNsenseNode):
    _vlan = [OPNsenseVlan]

class OPNsenseBridged(OPNsenseNode):
    _bridgeif = OPNsenseString
    _members = OPNsenseRuleInterface
    _descr = OPNsenseString

class OPNsenseBridges(OPNsenseNode):
    _bridged = [OPNsenseBridged]

class OPNsenseInterface(OPNsenseNode):
    _if = OPNsenseString
    _descr = OPNsenseString
    _ipaddr = OPNsenseString
    _subnet = OPNsenseString
    _enable = OPNsenseFlag

class OPNsenseInterfaces(OPNsenseInterfacesNode):
    _wan = OPNsenseInterface
    _lan = OPNsenseInterface
    _opt = OPNsenseInterface

class OPNsenseSyslog(OPNsenseNode):
    _nentries = OPNsenseInteger
    _logfilesize = OPNsenseInteger
    _remoteserver = OPNsenseString
    _remoteserver2 = OPNsenseString
    _remoteserver3 = OPNsenseString
    _sourceip = OPNsenseRuleInterface
    _ipproto = OPNsenseString
    _logall = OPNsenseFlag
    _enable = OPNsenseFlag

class OPNsenseSystem(OPNsenseNode):
    _optimization = OPNsenseString
    _hostname = OPNsenseString
    _domain = OPNsenseString
    _timeservers = OPNsenseString
    _timezone = OPNsenseString
    _language = OPNsenseString
    _dnsserver = [OPNsenseString]

class OPNsenseConfig(OPNsenseNode):
#    _version = OPNsenseString
    _system = OPNsenseSystem
    _interfaces = OPNsenseInterfaces
    _vlans = OPNsenseVlans
    _bridges = OPNsenseBridges
    _gateways = OPNsenseGateways
    _staticroutes = OPNsenseStaticRoutes
    _aliases = OPNsenseAliases
    _nat = OPNsenseNat
    _filter = OPNsenseFilter
    _dnsmasq = OPNsenseDnsMasq
    _dhcpd = OPNsenseDhcpd
    _openvpn = OPNsenseOpenVpn
    _syslog = OPNsenseSyslog
    _sysctl = OPNsenseSysCtl

class OPNsenseDocument(OPNsenseNode):
    _opnsense = OPNsenseConfig
