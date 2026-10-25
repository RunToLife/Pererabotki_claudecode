#!/usr/bin/env python3
"""Generates Zabbix templates for Eltex MES2408C (Zabbix 6.0 and 7.4)."""
import uuid

NS = uuid.UUID('6f1c2f0e-5d1a-4c55-9a53-0e17e1c0a001')
def U(name): return uuid.uuid5(NS, name).hex

GROUP = 'Templates/Network devices'
NAME = 'Eltex MES2408C by SNMP'
IFTAGS = "      tags:\n        - tag: component\n          value: {}\n"

def tags(v): return f"          tags:\n            - tag: component\n              value: {v}"

def render(ver):
    o = f"""zabbix_export:
  version: '{ver}'
  template_groups:
    - uuid: {U('group')}
      name: '{GROUP}'
  templates:
    - uuid: {U('tpl')}
      template: '{NAME}'
      name: '{NAME}'
      description: |
        Eltex MES2408C: ICMP ping, ports (status, speed, traffic), SFP modules, power supplies, temperature.
        Requires SNMP (v2c/v3) on the device. Vendor OIDs are exposed as macros - verify with snmpwalk.
      groups:
        - name: '{GROUP}'
      macros:
        - macro: '{{$SNMP.TIMEOUT}}'
          value: 5m
        - macro: '{{$ICMP.LOSS.WARN}}'
          value: '20'
        - macro: '{{$ICMP.RESPONSE.WARN}}'
          value: '0.15'
        - macro: '{{$IF.NAME.NOT_MATCHES}}'
          value: '^(vlan|Vlan|VLAN|Null|loopback|Loopback|tunnel|Tunnel|CPU|oob).*$'
          description: Interfaces excluded from discovery
        - macro: '{{$TEMP.WARN}}'
          value: '60'
        - macro: '{{$TEMP.CRIT}}'
          value: '75'
        - macro: '{{$OID.PSU.MAIN}}'
          value: 1.3.6.1.4.1.89.53.15.1.2.1
          description: rlPhdUnitEnvParamMainPSStatus (1 normal,2 warning,3 critical,4 shutdown,5 notPresent,6 notFunctioning)
        - macro: '{{$OID.PSU.REDUNDANT}}'
          value: 1.3.6.1.4.1.89.53.15.1.3.1
          description: rlPhdUnitEnvParamRedundantPSStatus
        - macro: '{{$OID.TEMP}}'
          value: 1.3.6.1.4.1.89.53.15.1.10.1
          description: rlPhdUnitEnvParamTempSensorValue (degrees C)
        - macro: '{{$OID.SFP.TABLE}}'
          value: 1.3.6.1.4.1.35265.1.23.53.1.1.1
          description: eltPhdTransceiverInfoTable entry; indexed by ifIndex
        - macro: '{{$OID.SFP.VENDOR}}'
          value: 1.3.6.1.4.1.35265.1.23.53.1.1.1.5
          description: SFP vendor name column (verify)
        - macro: '{{$OID.SFP.TYPE}}'
          value: 1.3.6.1.4.1.35265.1.23.53.1.1.1.3
          description: SFP type/compliance column (verify)
        - macro: '{{$OID.SFP.SERIAL}}'
          value: 1.3.6.1.4.1.35265.1.23.53.1.1.1.8
          description: SFP serial number column (verify)
      items:
        - uuid: {U('sysdescr')}
          name: System description
          type: SNMP_AGENT
          snmp_oid: 1.3.6.1.2.1.1.1.0
          key: system.descr
          delay: 1h
          trends: '0'
          value_type: TEXT
{tags('general')}
        - uuid: {U('uptime')}
          name: Uptime
          type: SNMP_AGENT
          snmp_oid: 1.3.6.1.2.1.1.3.0
          key: system.uptime
          delay: 1m
          units: uptime
          preprocessing:
            - type: MULTIPLIER
              parameters:
                - '0.01'
{tags('general')}
        - uuid: {U('ping')}
          name: ICMP ping
          type: SIMPLE
          key: icmpping
          delay: 1m
          valuemap:
            name: 'Service state'
          triggers:
            - uuid: {U('tr-ping')}
              expression: 'max(/{NAME}/icmpping,#3)=0'
              name: 'Eltex MES2408C: Unavailable by ICMP ping'
              priority: HIGH
{tags('availability')}
        - uuid: {U('loss')}
          name: ICMP loss
          type: SIMPLE
          key: icmppingloss
          delay: 1m
          value_type: FLOAT
          units: '%'
          triggers:
            - uuid: {U('tr-loss')}
              expression: 'min(/{NAME}/icmppingloss,5m)>{{$ICMP.LOSS.WARN}} and min(/{NAME}/icmppingloss,5m)<100'
              name: 'Eltex MES2408C: High ICMP ping loss'
              priority: WARNING
{tags('availability')}
        - uuid: {U('rtt')}
          name: ICMP response time
          type: SIMPLE
          key: icmppingsec
          delay: 1m
          value_type: FLOAT
          units: s
          triggers:
            - uuid: {U('tr-rtt')}
              expression: 'avg(/{NAME}/icmppingsec,5m)>{{$ICMP.RESPONSE.WARN}}'
              name: 'Eltex MES2408C: High ICMP ping response time'
              priority: WARNING
{tags('availability')}
        - uuid: {U('temp')}
          name: Temperature
          type: SNMP_AGENT
          snmp_oid: '{{$OID.TEMP}}'
          key: sensor.temp.value
          delay: 1m
          units: C
          triggers:
            - uuid: {U('tr-tw')}
              expression: 'min(/{NAME}/sensor.temp.value,5m)>{{$TEMP.WARN}}'
              name: 'Eltex MES2408C: High temperature (over {{$TEMP.WARN}}C)'
              priority: WARNING
              dependencies:
                - name: 'Eltex MES2408C: Critical temperature (over {{$TEMP.CRIT}}C)'
                  expression: 'min(/{NAME}/sensor.temp.value,5m)>{{$TEMP.CRIT}}'
            - uuid: {U('tr-tc')}
              expression: 'min(/{NAME}/sensor.temp.value,5m)>{{$TEMP.CRIT}}'
              name: 'Eltex MES2408C: Critical temperature (over {{$TEMP.CRIT}}C)'
              priority: HIGH
{tags('environment')}
        - uuid: {U('psu1')}
          name: 'Power supply: main status'
          type: SNMP_AGENT
          snmp_oid: '{{$OID.PSU.MAIN}}'
          key: sensor.psu.main.status
          delay: 1m
          valuemap:
            name: 'Eltex PSU state'
          triggers:
            - uuid: {U('tr-psu1')}
              expression: 'last(/{NAME}/sensor.psu.main.status)>=3 and last(/{NAME}/sensor.psu.main.status)<>5'
              name: 'Eltex MES2408C: Main power supply is not OK'
              priority: HIGH
{tags('power')}
        - uuid: {U('psu2')}
          name: 'Power supply: redundant status'
          type: SNMP_AGENT
          snmp_oid: '{{$OID.PSU.REDUNDANT}}'
          key: sensor.psu.redundant.status
          delay: 1m
          valuemap:
            name: 'Eltex PSU state'
          triggers:
            - uuid: {U('tr-psu2')}
              expression: 'last(/{NAME}/sensor.psu.redundant.status)>=3 and last(/{NAME}/sensor.psu.redundant.status)<>5'
              name: 'Eltex MES2408C: Redundant power supply is not OK'
              priority: AVERAGE
{tags('power')}
      discovery_rules:
        - uuid: {U('dr-if')}
          name: 'Network interfaces discovery'
          type: SNMP_AGENT
          snmp_oid: 'discovery[{{#IFNAME}},1.3.6.1.2.1.31.1.1.1.1,{{#IFALIAS}},1.3.6.1.2.1.31.1.1.1.18,{{#IFADMIN}},1.3.6.1.2.1.2.2.1.7]'
          key: net.if.discovery
          delay: 1h
          filter:
            conditions:
              - macro: '{{#IFNAME}}'
                value: '{{$IF.NAME.NOT_MATCHES}}'
                operator: NOT_MATCHES_REGEX
                formulaid: A
          item_prototypes:
            - uuid: {U('ip-oper')}
              name: 'Interface {{#IFNAME}}({{#IFALIAS}}): Operational status'
              type: SNMP_AGENT
              snmp_oid: '1.3.6.1.2.1.2.2.1.8.{{#SNMPINDEX}}'
              key: 'net.if.status[ifOperStatus.{{#SNMPINDEX}}]'
              delay: 1m
              valuemap:
                name: 'IF-MIB::ifOperStatus'
              tags:
                - tag: component
                  value: network
                - tag: interface
                  value: '{{#IFNAME}}'
              trigger_prototypes:
                - uuid: {U('tp-down')}
                  expression: 'last(/{NAME}/net.if.status[ifOperStatus.{{#SNMPINDEX}}])=2 and {{#IFADMIN}}=1'
                  name: 'Interface {{#IFNAME}}({{#IFALIAS}}): Link down (disconnected)'
                  priority: AVERAGE
                  manual_close: 'YES'
            - uuid: {U('ip-speed')}
              name: 'Interface {{#IFNAME}}({{#IFALIAS}}): Speed (bandwidth)'
              type: SNMP_AGENT
              snmp_oid: '1.3.6.1.2.1.31.1.1.1.15.{{#SNMPINDEX}}'
              key: 'net.if.speed[ifHighSpeed.{{#SNMPINDEX}}]'
              delay: 5m
              units: bps
              preprocessing:
                - type: MULTIPLIER
                  parameters:
                    - '1000000'
              tags:
                - tag: component
                  value: network
                - tag: interface
                  value: '{{#IFNAME}}'
            - uuid: {U('ip-in')}
              name: 'Interface {{#IFNAME}}({{#IFALIAS}}): Bits received'
              type: SNMP_AGENT
              snmp_oid: '1.3.6.1.2.1.31.1.1.1.6.{{#SNMPINDEX}}'
              key: 'net.if.in[ifHCInOctets.{{#SNMPINDEX}}]'
              delay: 1m
              units: bps
              preprocessing:
                - type: CHANGE_PER_SECOND
                  parameters:
                    - ''
                - type: MULTIPLIER
                  parameters:
                    - '8'
              tags:
                - tag: component
                  value: network
                - tag: interface
                  value: '{{#IFNAME}}'
            - uuid: {U('ip-out')}
              name: 'Interface {{#IFNAME}}({{#IFALIAS}}): Bits sent'
              type: SNMP_AGENT
              snmp_oid: '1.3.6.1.2.1.31.1.1.1.10.{{#SNMPINDEX}}'
              key: 'net.if.out[ifHCOutOctets.{{#SNMPINDEX}}]'
              delay: 1m
              units: bps
              preprocessing:
                - type: CHANGE_PER_SECOND
                  parameters:
                    - ''
                - type: MULTIPLIER
                  parameters:
                    - '8'
              tags:
                - tag: component
                  value: network
                - tag: interface
                  value: '{{#IFNAME}}'
        - uuid: {U('dr-sfp')}
          name: 'SFP modules discovery'
          type: SNMP_AGENT
          snmp_oid: 'discovery[{{#SFPVENDOR}},{{$OID.SFP.VENDOR}}]'
          key: sfp.discovery
          delay: 1h
          item_prototypes:
            - uuid: {U('sp-vendor')}
              name: 'SFP {{#SNMPINDEX}}: Vendor'
              type: SNMP_AGENT
              snmp_oid: '{{$OID.SFP.VENDOR}}.{{#SNMPINDEX}}'
              key: 'sfp.vendor[{{#SNMPINDEX}}]'
              delay: 1h
              trends: '0'
              value_type: CHAR
              tags:
                - tag: component
                  value: sfp
            - uuid: {U('sp-type')}
              name: 'SFP {{#SNMPINDEX}}: Type'
              type: SNMP_AGENT
              snmp_oid: '{{$OID.SFP.TYPE}}.{{#SNMPINDEX}}'
              key: 'sfp.type[{{#SNMPINDEX}}]'
              delay: 1h
              trends: '0'
              value_type: CHAR
              tags:
                - tag: component
                  value: sfp
            - uuid: {U('sp-serial')}
              name: 'SFP {{#SNMPINDEX}}: Serial number'
              type: SNMP_AGENT
              snmp_oid: '{{$OID.SFP.SERIAL}}.{{#SNMPINDEX}}'
              key: 'sfp.serial[{{#SNMPINDEX}}]'
              delay: 1h
              trends: '0'
              value_type: CHAR
              tags:
                - tag: component
                  value: sfp
      valuemaps:
        - uuid: {U('vm-svc')}
          name: 'Service state'
          mappings:
            - value: '0'
              newvalue: Down
            - value: '1'
              newvalue: Up
        - uuid: {U('vm-if')}
          name: 'IF-MIB::ifOperStatus'
          mappings:
            - value: '1'
              newvalue: up
            - value: '2'
              newvalue: down
            - value: '3'
              newvalue: testing
            - value: '4'
              newvalue: unknown
            - value: '5'
              newvalue: dormant
            - value: '6'
              newvalue: notPresent
            - value: '7'
              newvalue: lowerLayerDown
        - uuid: {U('vm-psu')}
          name: 'Eltex PSU state'
          mappings:
            - value: '1'
              newvalue: normal
            - value: '2'
              newvalue: warning
            - value: '3'
              newvalue: critical
            - value: '4'
              newvalue: shutdown
            - value: '5'
              newvalue: notPresent
            - value: '6'
              newvalue: notFunctioning
"""
    return o

import re
for ver, fn in (('6.0', 'zabbix_6.0/template_eltex_mes2408c_snmp.yaml'),
                ('7.4', 'zabbix_7.4/template_eltex_mes2408c_snmp.yaml')):
    import os; os.makedirs(os.path.dirname(fn), exist_ok=True)
    open(fn, 'w').write(render(ver))
