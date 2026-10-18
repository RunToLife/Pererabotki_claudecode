import uuid, sys
def u(): return uuid.uuid4().hex
def snmp_item(name,key,oid,vt='FLOAT',units='',delay='1m',desc='',pre=None,tags=None,triggers=None,proto=False,vmap=None):
    s=f"- uuid: {u()}\n  name: '{name}'\n  type: SNMP_AGENT\n  snmp_oid: '{oid}'\n  key: '{key}'\n  delay: {delay}\n"
    if vt!='FLOAT': s+=f"  value_type: {vt}\n"
    if units: s+=f"  units: '{units}'\n"
    if desc: s+=f"  description: \"{desc}\"\n"
    if vmap: s+=f"  valuemap:\n    name: '{vmap}'\n"
    if pre: s+="  preprocessing:\n"+"".join(f"    - type: {t}\n      parameters:\n"+"".join(f"        - '{p}'\n" for p in ps) for t,ps in pre)
    s+="  tags:\n"+"".join(f"    - tag: {k}\n      value: {v}\n" for k,v in (tags or []))
    if triggers: s+="  triggers:\n"+triggers
    return s
def ind(t,n): return "".join(" "*n+l+"\n" for l in t.splitlines())
def trig(name,expr,prio,desc=''):
    return f"  - uuid: {u()}\n    expression: '{expr}'\n    name: '{name}'\n    priority: {prio}\n"+(f"    description: '{desc}'\n" if desc else "")
def proto_items(items): return ind("".join(items),0)

def build(ver):
    T="Eltex MES2408C by SNMP"
    out=f"""zabbix_export:
  version: '{ver}'
  template_groups:
    - uuid: {u()}
      name: Templates/Network devices
  templates:
    - uuid: {u()}
      template: '{T}'
      name: '{T}'
      description: |
        Monitoring of the Eltex MES2408C switch via SNMP (v2c/v3).
        Covers ICMP ping, port state/speed/traffic, SFP modules, power supplies and temperature.
        Set macros {{$SNMP_COMMUNITY}} on the host. Vendor-specific OIDs (Radlan 1.3.6.1.4.1.89 / Eltex 1.3.6.1.4.1.35265)
        must be verified with snmpwalk on the actual firmware.
      groups:
        - name: Templates/Network devices
      items:
"""
    items=[]
    items.append(f"- uuid: {u()}\n  name: 'ICMP ping'\n  type: SIMPLE\n  key: icmpping\n  history: 7d\n  valuemap:\n    name: 'Service state'\n  tags:\n    - tag: component\n      value: health\n  triggers:\n"+trig("Eltex MES2408C: Unavailable by ICMP ping","max(/{T}/icmpping,#3)=0","HIGH","Last three ICMP checks failed.").replace("\n  ","\n    ").replace("  - uuid","    - uuid",1) if False else "")
    # simple builds below
    def raw(s): return s
    ping=f"""- uuid: {u()}
  name: 'ICMP ping'
  type: SIMPLE
  key: icmpping
  history: 7d
  valuemap:
    name: 'Service state'
  tags:
    - tag: component
      value: health
  triggers:
    - uuid: {u()}
      expression: 'max(/{T}/icmpping,#3)=0'
      name: 'Eltex MES2408C: Unavailable by ICMP ping'
      priority: HIGH
      description: 'Last three ICMP checks failed.'
- uuid: {u()}
  name: 'ICMP loss'
  type: SIMPLE
  key: icmppingloss
  value_type: FLOAT
  units: '%'
  tags:
    - tag: component
      value: health
- uuid: {u()}
  name: 'ICMP response time'
  type: SIMPLE
  key: icmppingsec
  value_type: FLOAT
  units: s
  tags:
    - tag: component
      value: health
- uuid: {u()}
  name: 'SNMP availability'
  type: INTERNAL
  key: 'zabbix[host,snmp,available]'
  tags:
    - tag: component
      value: health
  triggers:
    - uuid: {u()}
      expression: 'max(/{T}/zabbix[host,snmp,available],#3)=0'
      name: 'Eltex MES2408C: No SNMP data collection'
      priority: WARNING
- uuid: {u()}
  name: 'System description'
  type: SNMP_AGENT
  snmp_oid: 1.3.6.1.2.1.1.1.0
  key: system.descr
  delay: 1h
  value_type: CHAR
  trends: '0'
  tags:
    - tag: component
      value: system
- uuid: {u()}
  name: 'System uptime'
  type: SNMP_AGENT
  snmp_oid: 1.3.6.1.2.1.1.3.0
  key: system.uptime
  units: uptime
  preprocessing:
    - type: MULTIPLIER
      parameters:
        - '0.01'
  tags:
    - tag: component
      value: system
- uuid: {u()}
  name: 'Device temperature'
  type: SNMP_AGENT
  snmp_oid: 1.3.6.1.4.1.89.53.15.1.10.1
  key: sensor.temp.value
  units: '°C'
  description: 'rlPhdUnitEnvParamTempSensorValue (unit 1).'
  tags:
    - tag: component
      value: temperature
  triggers:
    - uuid: {u()}
      expression: 'min(/{T}/sensor.temp.value,5m)>{{$TEMP_WARN}}'
      name: 'Eltex MES2408C: High temperature (>{{$TEMP_WARN}}°C)'
      priority: WARNING
      dependencies:
        - name: 'Eltex MES2408C: Critical temperature (>{{$TEMP_CRIT}}°C)'
          expression: 'min(/{T}/sensor.temp.value,5m)>{{$TEMP_CRIT}}'
    - uuid: {u()}
      expression: 'min(/{T}/sensor.temp.value,5m)>{{$TEMP_CRIT}}'
      name: 'Eltex MES2408C: Critical temperature (>{{$TEMP_CRIT}}°C)'
      priority: HIGH
"""
    out+=ind(ping,8)
    def lld(name,key,oid,keyname,protos,filt=None,extra=''):
        s=f"""- uuid: {u()}
  name: '{name}'
  type: SNMP_AGENT
  snmp_oid: '{oid}'
  key: {key}
  delay: 1h
  description: '{extra}'
"""
        if filt: s+=filt
        s+="  item_prototypes:\n"+ind(protos,4)
        return s
    def ip(name,key,oid,vt='',units='',delay='1m',pre='',valuemap='',comp='interface',trg='',desc=''):
        s=f"- uuid: {u()}\n  name: '{name}'\n  type: SNMP_AGENT\n  snmp_oid: '{oid}'\n  key: '{key}'\n  delay: {delay}\n"
        if vt: s+=f"  value_type: {vt}\n"
        if vt=='CHAR' or vt=='TEXT': s+="  trends: '0'\n"
        if units: s+=f"  units: '{units}'\n"
        if desc: s+=f"  description: '{desc}'\n"
        if valuemap: s+=f"  valuemap:\n    name: '{valuemap}'\n"
        s+=pre
        s+=f"  tags:\n    - tag: component\n      value: {comp}\n"
        s+=trg
        return s
    delta="  preprocessing:\n    - type: CHANGE_PER_SECOND\n      parameters:\n        - ''\n    - type: MULTIPLIER\n      parameters:\n        - '8'\n"
    mult="  preprocessing:\n    - type: MULTIPLIER\n      parameters:\n        - '1000000'\n"
    # interfaces
    pr=""
    pr+=ip('Interface {#IFNAME}: Operational status','net.if.status[{#SNMPINDEX}]','1.3.6.1.2.1.2.2.1.8.{#SNMPINDEX}',valuemap='IF-MIB::ifOperStatus',desc='up(1) = connected, down(2) = disconnected',
      trg=f"""  trigger_prototypes:
    - uuid: {u()}
      expression: 'last(/{T}/net.if.status[{{#SNMPINDEX}}])=2 and last(/{T}/net.if.admin[{{#SNMPINDEX}}])=1'
      name: 'Eltex MES2408C: Interface {{#IFNAME}}: Link down'
      priority: AVERAGE
      description: 'Port is administratively up but the link is down (disconnected).'
      manual_close: 'YES'
""")
    pr+=ip('Interface {#IFNAME}: Administrative status','net.if.admin[{#SNMPINDEX}]','1.3.6.1.2.1.2.2.1.7.{#SNMPINDEX}',valuemap='IF-MIB::ifAdminStatus',desc='up(1) / down(2) as configured')
    pr+=ip('Interface {#IFNAME}: Bandwidth (speed)','net.if.speed[{#SNMPINDEX}]','1.3.6.1.2.1.31.1.1.1.15.{#SNMPINDEX}',units='bps',pre=mult,desc='ifHighSpeed, negotiated speed of the port')
    pr+=ip('Interface {#IFNAME}: Bits received','net.if.in[{#SNMPINDEX}]','1.3.6.1.2.1.31.1.1.1.6.{#SNMPINDEX}',units='bps',pre=delta,desc='Incoming traffic rate (ifHCInOctets)')
    pr+=ip('Interface {#IFNAME}: Bits sent','net.if.out[{#SNMPINDEX}]','1.3.6.1.2.1.31.1.1.1.10.{#SNMPINDEX}',units='bps',pre=delta,desc='Outgoing traffic rate (ifHCOutOctets)')
    pr+=ip('Interface {#IFNAME}: Inbound errors','net.if.in.errors[{#SNMPINDEX}]','1.3.6.1.2.1.2.2.1.14.{#SNMPINDEX}',units='pps',pre=delta.split("    - type: MULTIPLIER")[0])
    pr+=ip('Interface {#IFNAME}: Outbound errors','net.if.out.errors[{#SNMPINDEX}]','1.3.6.1.2.1.2.2.1.20.{#SNMPINDEX}',units='pps',pre=delta.split("    - type: MULTIPLIER")[0])
    pr+=ip('Interface {#IFNAME}: Description (alias)','net.if.alias[{#SNMPINDEX}]','1.3.6.1.2.1.31.1.1.1.18.{#SNMPINDEX}',vt='CHAR',delay='1h')
    filt="""  filter:
    evaltype: AND
    conditions:
      - macro: '{#IFNAME}'
        value: '{$IF.NAME.MATCHES}'
        formulaid: A
      - macro: '{#IFNAME}'
        value: '{$IF.NAME.NOT_MATCHES}'
        operator: NOT_MATCHES_REGEX
        formulaid: B
"""
    out+="      discovery_rules:\n"
    disc=f"""- uuid: {u()}
  name: 'Network interfaces discovery'
  type: SNMP_AGENT
  snmp_oid: 'discovery[{{#IFNAME}},1.3.6.1.2.1.31.1.1.1.1,{{#IFDESCR}},1.3.6.1.2.1.2.2.1.2]'
  key: net.if.discovery
  delay: 1h
{filt}  item_prototypes:
{ind(pr,4)}"""
    out+=ind(disc,8)
    # SFP
    sfp=""
    sfp+=ip('SFP {#SFPNAME}: Vendor','sfp.vendor[{#SNMPINDEX}]','1.3.6.1.4.1.35265.1.23.53.1.1.1.8.{#SNMPINDEX}',vt='CHAR',delay='1h',comp='sfp',desc='Transceiver vendor name (Eltex transceiver info table; verify OID column on firmware)')
    sfp+=ip('SFP {#SFPNAME}: Part number / type','sfp.type[{#SNMPINDEX}]','1.3.6.1.4.1.35265.1.23.53.1.1.1.9.{#SNMPINDEX}',vt='CHAR',delay='1h',comp='sfp')
    sfp+=ip('SFP {#SFPNAME}: Serial number','sfp.serial[{#SNMPINDEX}]','1.3.6.1.4.1.35265.1.23.53.1.1.1.10.{#SNMPINDEX}',vt='CHAR',delay='1h',comp='sfp')
    sfp+=ip('SFP {#SFPNAME}: Temperature','sfp.temp[{#SNMPINDEX}]','1.3.6.1.4.1.89.90.1.2.1.3.{#SNMPINDEX}.5',units='°C',comp='sfp',desc='rlPhyTestGetResult, DDM temperature (verify on firmware)')
    disc=f"""- uuid: {u()}
  name: 'SFP modules discovery'
  type: SNMP_AGENT
  snmp_oid: 'discovery[{{#SFPNAME}},1.3.6.1.4.1.35265.1.23.53.1.1.1.8]'
  key: sfp.discovery
  delay: 1h
  description: 'Discovers inserted SFP transceivers (rows exist only for present modules).'
  lifetime: 7d
  item_prototypes:
{ind(sfp,4)}"""
    out+=ind(disc,8)
    # PSU
    psu=ip('PSU {#PSUDESCR}: State','psu.state[{#SNMPINDEX}]','1.3.6.1.4.1.89.83.1.2.1.3.{#SNMPINDEX}',valuemap='Eltex PSU state',comp='power-supply',desc='rlEnvMonSupplyState: 1 normal, 2 warning, 3 critical, 4 shutdown, 5 notPresent, 6 notFunctioning',
      trg=f"""  trigger_prototypes:
    - uuid: {u()}
      expression: 'last(/{T}/psu.state[{{#SNMPINDEX}}])>=2 and last(/{T}/psu.state[{{#SNMPINDEX}}])<>5'
      name: 'Eltex MES2408C: Power supply {{#PSUDESCR}} is not normal'
      priority: HIGH
""")
    disc=f"""- uuid: {u()}
  name: 'Power supply discovery'
  type: SNMP_AGENT
  snmp_oid: 'discovery[{{#PSUDESCR}},1.3.6.1.4.1.89.83.1.2.1.2]'
  key: psu.discovery
  delay: 1h
  item_prototypes:
{ind(psu,4)}"""
    out+=ind(disc,8)
    out+=f"""      macros:
        - macro: '{{$TEMP_WARN}}'
          value: '55'
        - macro: '{{$TEMP_CRIT}}'
          value: '70'
        - macro: '{{$IF.NAME.MATCHES}}'
          value: '.*'
        - macro: '{{$IF.NAME.NOT_MATCHES}}'
          value: '^(vlan|Vlan|oob|Null|CPU).*'
      valuemaps:
        - uuid: {u()}
          name: 'Service state'
          mappings:
            - value: '0'
              newvalue: Down
            - value: '1'
              newvalue: Up
        - uuid: {u()}
          name: 'IF-MIB::ifOperStatus'
          mappings:
            - value: '1'
              newvalue: up
            - value: '2'
              newvalue: down
            - value: '3'
              newvalue: testing
            - value: '5'
              newvalue: dormant
            - value: '6'
              newvalue: notPresent
            - value: '7'
              newvalue: lowerLayerDown
        - uuid: {u()}
          name: 'IF-MIB::ifAdminStatus'
          mappings:
            - value: '1'
              newvalue: up
            - value: '2'
              newvalue: down
            - value: '3'
              newvalue: testing
        - uuid: {u()}
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
    return out
for v in ('6.0','7.4'):
    d={'6.0':'zabbix_6.0','7.4':'zabbix_7.4'}[v]
    import os; os.makedirs(f'/home/user/Pererabotki_claudecode/{d}',exist_ok=True)
    open(f'/home/user/Pererabotki_claudecode/{d}/template_eltex_mes2408c_snmp.yaml','w').write(build(v))
