# -*- coding: utf-8 -*-
'''
Module for handling Cluster management in salt
'''
import re

def __virtual__():
    '''
    No deps. Load the module
    '''
    return 'cluster_ops'


def list_sls(machine=None):
    '''
    Get list of sls to apply from pillar data
    '''
    host_sls = []
    for role in list_roles(machine):
        for sls in __pillar__.get('sls', {}).get(role, []):
            if sls not in host_sls:
                host_sls.append(sls)
    return host_sls


def list_roles(machine=None):
    '''
    Get list of roles played by host
    '''
    if not machine:
        machine = __grains__['id']
    return [cluster_entity for cluster_entity in
            __pillar__.get('cluster_entities', [])
            if machine in __pillar__.get(cluster_entity, [])]


def list_hosts():
    '''
    Get list of hosts available in cluster
    '''
    host_list = []
    for cluster_entity in __pillar__.get('cluster_entities', []):
        for host in __pillar__.get(cluster_entity, []):
            if host not in host_list:
                host_list.append(host)
    return host_list


def get_candidate(name=None):
    """
    Return the host runing the particular service
    """
    for host in list_hosts():
        for sls in list_sls(machine=host):
            if re.match(name, sls):
                return host


def get_install_flavor(name=None):
    """
    Return the particular flavor of a service
    queue.* would return rabbit if queue.rabbit is in list of sls
    """
    name = name.replace('*', '(.*)')
    for host in list_hosts():
        for sls in list_sls(machine=host):
            match = re.match(name, sls)
            if match:
                return match.group(1)


def get_vlan_ranges(network_type='flat'):
    if network_type == 'flat':
        return ','.join((physnet for physnet in __salt__['pillar.get']('neutron:type_drivers:flat:physnets', default=()) if __grains__['id'] in __pillar__['neutron']['type_drivers']['flat']['physnets'][physnet]['hosts']))
    else:
        return ','.join((':'.join((physnet, __pillar__['neutron']['type_drivers']['vlan']['physnets'][physnet]['vlan_range'])) for physnet in __salt__['pillar.get']('neutron:type_drivers:vlan:physnets', default=()) if __grains__['id'] in __pillar__['neutron']['type_drivers']['vlan']['physnets'][physnet]['hosts']))
    physical_iter = []
    for physical_network in __pillar__['neutron']['type_drivers'][network_type].get(__grains__['id'], {}):
		network_iter = [physical_network]
		for vlan in __pillar__['neutron']['type_drivers'][network_type][__grains__['id']][physical_network].get('vlan_range', []):
			network_iter.append(vlan)
		physical_iter.append(':'.join(network_iter))
    return ','.join(physical_iter)


def get_bridge_mappings():
    return ','.join((':'.join((physnet, __pillar__['neutron']['type_drivers'][network_type]['physnets'][physnet]['bridge'])) for network_type in ('flat', 'vlan') for physnet in __salt__['pillar.get']('neutron:type_drivers:%s:physnets' % network_type, default=()) if __grains__['id'] in __pillar__['neutron']['type_drivers'][network_type]['physnets'][physnet]['hosts']))
    bridge_iter = []
    for physical_network in __pillar__['neutron']['type_drivers'][network_type].get(__grains__['id'], {}):
        network_iter = [physical_network, __pillar__['neutron']['type_drivers'][network_type][__grains__['id']][physical_network]['bridge']]
        bridge_iter.append(':'.join(network_iter))
    return ','.join(bridge_iter)


def create_init_bridges():
	try:
		__salt__['cmd.run']('ovs-vsctl --no-wait add-br ' + __pillar__['neutron']['intergration_bridge'])
	except:
		pass
	for physical_network in __pillar__['neutron'].get(__grains__['id'], {}):
		try:
			__salt__['cmd.run']('ovs-vsctl --no-wait add-br ' +
								__pillar__['neutron'][__grains__['id']][physical_network]['bridge'])
			__salt__['cmd.run']('ovs-vsctl --no-wait add-port  %s %s' %
								(__pillar__['neutron'][__grains__['id']][physical_network]['bridge'],
								 __pillar__['neutron'][__grains__['id']][physical_network]['interface']))
			__salt__['cmd.run']('ip link set %s up' % __pillar__['neutron'][__grains__['id']][physical_network]['interface'])
			__salt__['cmd.run']('ip link set %s promisc on' % __pillar__['neutron'][__grains__['id']][physical_network]['interface'])
		except:
			pass
