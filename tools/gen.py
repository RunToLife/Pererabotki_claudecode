#!/usr/bin/env python3
"""Генератор шаблонов Eltex MES2408C для Zabbix 6.0 и 7.4 (YAML)."""
import uuid, sys

NS = uuid.UUID('6f1d2c3e-0000-4000-8000-00000000e1c0')
def u(name): return uuid.uuid5(NS, name).hex

ENV = '1.3.6.1.4.1.89.53.15.1'   # RADLAN rlPhdUnitEnvParamTable
TRX = '1.3.6.1.4.1.89.90.1.2.1'  # RADLAN transceiver info (проверить snmpwalk на устройстве)

def item(name, key, oid=None, itype='SNMP_AGENT', vt='FLOAT', units='', delay='1m', extra='', proto=False, tags=None, pre=''):
    s = f"          - uuid: {u(key)}\n            name: '{name}'\n            type: {itype}\n"
    if oid: s += f"            snmp_oid: '{oid}'\n"
    s += f"            key: '{key}'\n            delay: {delay}\n"
    if vt != 'FLOAT': s += f"            value_type: {vt}\n"
    if units: s += f"            units: '{units}'\n"
    if vt == 'CHAR' or vt == 'TEXT': s += "            trends: '0'\n"
    s += pre + extra
    s += f"            tags:\n              - tag: component\n                value: {tags}\n"
    return s

def top(name, key, oid, tag, **kw):
    return item(name, key, oid, tags=tag, **kw).replace('          - uuid', '      - uuid', 1).replace('\n  ', '\n  ')

def gen(ver):
    # плоская генерация без хитрых отступов: строим вручную
    L = []
    a = L.append
    a(f"zabbix_export:\n  version: '{ver}'\n  template_groups:\n    - uuid: {u('grp')}\n      name: Templates/Network devices\n  templates:\n    - uuid: {u('tpl'+ver)}\n      template: 'Eltex MES2408C SNMP'\n      name: 'Eltex MES2408C SNMP'\n      description: 'Ping, порты, SFP, блоки питания, температура. Макрос {{$SNMP_COMMUNITY}}.'\n      groups:\n        - name: Templates/Network devices\n      items:")
    def it(name, key, itype, oid=None, vt=None, units=None, delay='1m', comp='', pre=None):
        a(f"        - uuid: {u(ver+key)}\n          name: '{name}'\n          type: {itype}")
        if oid: a(f"          snmp_oid: '{oid}'")
        a(f"          key: '{key}'\n          delay: {delay}")
        if vt: a(f"          value_type: {vt}")
        if units: a(f"          units: '{units}'")
        if pre: a(pre)
        a(f"          tags:\n            - tag: component\n              value: {comp}")
    it('ICMP ping', 'icmpping', 'SIMPLE', vt='UNSIGNED', delay='30s', comp='network')
    it('ICMP packet loss', 'icmppingloss', 'SIMPLE', units='%', delay='1m', comp='network')
    it('ICMP response time', 'icmppingsec', 'SIMPLE', units='s', delay='1m', comp='network')
    it('SNMP availability', 'eltex.snmp.sysname', 'SNMP_AGENT', oid='1.3.6.1.2.1.1.5.0', vt='CHAR', comp='system')
    a("      discovery_rules:")
    def rule(name, key, oid, macro_filter, protos, extra_filter=''):
        a(f"        - uuid: {u(ver+key)}\n          name: '{name}'\n          type: SNMP_AGENT\n          snmp_oid: 'discovery[{{#IFNAME}}, 1.3.6.1.2.1.2.2.1.2, {{#IFALIAS}}, 1.3.6.1.2.1.31.1.1.1.18]'\n          key: '{key}'\n          delay: 1h") if False else None
    def drule(name, key, oid, fl='', lld_macros=''):
        a(f"        - uuid: {u(ver+key)}\n          name: '{name}'\n          type: SNMP_AGENT\n          snmp_oid: '{oid}'\n          key: '{key}'\n          delay: 1h\n          lifetime: 7d")
        if fl: a(fl)
        a("          item_prototypes:")
    def proto(name, key, itype, oid, vt=None, units=None, delay='1m', comp='', pre=None, trig=None):
        a(f"            - uuid: {u(ver+key)}\n              name: '{name}'\n              type: {itype}\n              snmp_oid: '{oid}'\n              key: '{key}'\n              delay: {delay}")
        if vt: a(f"              value_type: {vt}")
        if units: a(f"              units: '{units}'")
        if pre: a(pre)
        a(f"              tags:\n                - tag: component\n                  value: {comp}")
    # ---- порты
    flt = ("          filter:\n            evaltype: AND_OR\n            conditions:\n"
           "              - macro: '{#IFTYPE}'\n                value: '^6$'\n                formulaid: A")
    drule('Network interfaces discovery', 'eltex.if.discovery',
          'discovery[{#IFDESCR}, 1.3.6.1.2.1.2.2.1.2, {#IFTYPE}, 1.3.6.1.2.1.2.2.1.3, {#IFALIAS}, 1.3.6.1.2.1.31.1.1.1.18]', flt)
    P = lambda s: f"              preprocessing:\n{s}"
    cps = ("                - type: CHANGE_PER_SECOND\n                  parameters:\n                    - ''\n"
           "                - type: MULTIPLIER\n                  parameters:\n                    - '8'")
    proto('Port {#IFDESCR}: operational status (up/down, connected/disconnected)', 'eltex.if.oper[{#SNMPINDEX}]', 'SNMP_AGENT', '1.3.6.1.2.1.2.2.1.8.{#SNMPINDEX}', 'UNSIGNED', comp='port')
    proto('Port {#IFDESCR}: admin status', 'eltex.if.admin[{#SNMPINDEX}]', 'SNMP_AGENT', '1.3.6.1.2.1.2.2.1.7.{#SNMPINDEX}', 'UNSIGNED', comp='port')
    proto('Port {#IFDESCR}: bandwidth (link speed)', 'eltex.if.speed[{#SNMPINDEX}]', 'SNMP_AGENT', '1.3.6.1.2.1.31.1.1.1.15.{#SNMPINDEX}', 'UNSIGNED', 'bps', comp='port',
          pre=P("                - type: MULTIPLIER\n                  parameters:\n                    - '1000000'"))
    proto('Port {#IFDESCR}: incoming traffic', 'eltex.if.in[{#SNMPINDEX}]', 'SNMP_AGENT', '1.3.6.1.2.1.31.1.1.1.6.{#SNMPINDEX}', None, 'bps', comp='port', pre=P(cps))
    proto('Port {#IFDESCR}: outgoing traffic', 'eltex.if.out[{#SNMPINDEX}]', 'SNMP_AGENT', '1.3.6.1.2.1.31.1.1.1.10.{#SNMPINDEX}', None, 'bps', comp='port', pre=P(cps))
    a(f"          trigger_prototypes:\n            - uuid: {u(ver+'trg.if')}\n              expression: 'last(/Eltex MES2408C SNMP/eltex.if.oper[{{#SNMPINDEX}}])=2 and last(/Eltex MES2408C SNMP/eltex.if.admin[{{#SNMPINDEX}}])=1'\n              name: 'Port {{#IFDESCR}}: link down'\n              priority: WARNING")
    # ---- питание
    drule('Power supply discovery', 'eltex.psu.discovery', 'discovery[{#PSUIDX}, %s.2]' % ENV)
    proto('PSU {#SNMPINDEX}: main power supply status', 'eltex.psu.main[{#SNMPINDEX}]', 'SNMP_AGENT', ENV+'.2.{#SNMPINDEX}', 'UNSIGNED', comp='power')
    proto('PSU {#SNMPINDEX}: redundant power supply status', 'eltex.psu.red[{#SNMPINDEX}]', 'SNMP_AGENT', ENV+'.3.{#SNMPINDEX}', 'UNSIGNED', comp='power')
    a(f"          trigger_prototypes:\n            - uuid: {u(ver+'trg.psu')}\n              expression: 'last(/Eltex MES2408C SNMP/eltex.psu.main[{{#SNMPINDEX}}])>=3 and last(/Eltex MES2408C SNMP/eltex.psu.main[{{#SNMPINDEX}}])<>5'\n              name: 'PSU {{#SNMPINDEX}}: main power supply failure'\n              priority: HIGH\n              description: '1 normal, 2 warning, 3 critical, 4 shutdown, 5 notPresent, 6 notFunctioning'")
    # ---- температура
    drule('Temperature sensor discovery', 'eltex.temp.discovery', 'discovery[{#TEMPIDX}, %s.10]' % ENV)
    proto('Unit {#SNMPINDEX}: temperature', 'eltex.temp[{#SNMPINDEX}]', 'SNMP_AGENT', ENV+'.10.{#SNMPINDEX}', None, 'C', comp='temperature')
    proto('Unit {#SNMPINDEX}: temperature sensor status', 'eltex.temp.status[{#SNMPINDEX}]', 'SNMP_AGENT', ENV+'.9.{#SNMPINDEX}', 'UNSIGNED', comp='temperature')
    a(f"          trigger_prototypes:\n            - uuid: {u(ver+'trg.temp')}\n              expression: 'avg(/Eltex MES2408C SNMP/eltex.temp[{{#SNMPINDEX}}],5m)>{{$TEMP_WARN}}'\n              name: 'Unit {{#SNMPINDEX}}: high temperature (>{{$TEMP_WARN}}C)'\n              priority: WARNING")
    # ---- SFP
    drule('SFP transceiver discovery', 'eltex.sfp.discovery', 'discovery[{#SFPIDX}, %s.3]' % TRX)
    proto('SFP {#SNMPINDEX}: type', 'eltex.sfp.type[{#SNMPINDEX}]', 'SNMP_AGENT', TRX+'.3.{#SNMPINDEX}', 'CHAR', comp='sfp', delay='1h')
    proto('SFP {#SNMPINDEX}: vendor', 'eltex.sfp.vendor[{#SNMPINDEX}]', 'SNMP_AGENT', TRX+'.4.{#SNMPINDEX}', 'CHAR', comp='sfp', delay='1h')
    proto('SFP {#SNMPINDEX}: part number', 'eltex.sfp.pn[{#SNMPINDEX}]', 'SNMP_AGENT', TRX+'.5.{#SNMPINDEX}', 'CHAR', comp='sfp', delay='1h')
    proto('SFP {#SNMPINDEX}: serial number', 'eltex.sfp.sn[{#SNMPINDEX}]', 'SNMP_AGENT', TRX+'.6.{#SNMPINDEX}', 'CHAR', comp='sfp', delay='1h')
    # ---- триггеры и макросы
    a(f"      triggers:\n        - uuid: {u(ver+'trg.ping')}\n          expression: 'max(/Eltex MES2408C SNMP/icmpping,#3)=0'\n          name: 'Eltex MES2408C: no ping'\n          priority: HIGH")
    a("      macros:\n        - macro: '{$SNMP_COMMUNITY}'\n          value: public\n        - macro: '{$TEMP_WARN}'\n          value: '65'")
    return '\n'.join(x for x in L if x is not None) + '\n'

for v, d in (('6.0', 'zabbix-6.0'), ('7.4', 'zabbix-7.4')):
    open(f'{d}/template_eltex_mes2408c_snmp.yaml', 'w').write(gen(v))
