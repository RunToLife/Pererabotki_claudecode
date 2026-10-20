#!/usr/bin/env python3
"""Генератор шаблонов Zabbix для Eltex MES2408C (6.0 и 7.4)."""
import uuid, sys

NS = uuid.UUID('6f1c1a52-0000-4000-8000-00000000e17e')
def u(name): return uuid.uuid5(NS, name).hex
Q = lambda s: "'" + s.replace("'", "''") + "'"

def build(ver):
    grp = 'template_groups' if ver == '7.4' else 'groups'
    T = 'Eltex MES2408C by SNMP'
    o = []
    a = o.append
    a(f"zabbix_export:\n  version: {Q(ver)}\n  {grp}:\n    - uuid: {u('grp'+ver)}\n      name: Templates/Network devices")
    a(f"  templates:\n    - uuid: {u('tpl'+ver)}\n      template: {Q(T)}\n      name: {Q(T)}\n      description: |\n        Eltex MES2408C: ping, порты, SFP, блоки питания, температура. SNMP v2c/v3.\n        Макросы: {{$SNMP_COMMUNITY}}, {{$TEMP_WARN}}, {{$TEMP_CRIT}}.\n      {grp}:\n        - name: Templates/Network devices")
    def item(name, key, typ, oid=None, units=None, vt=None, vm=None, pre=None, delay='1m', tags=None, ind='        ', trig=None, extra=''):
        s = [f"{ind}- uuid: {u(ver+key+name)}", f"{ind}  name: {Q(name)}"]
        if typ != 'SIMPLE' or True: s.append(f"{ind}  type: {typ}")
        if oid: s.append(f"{ind}  snmp_oid: {Q(oid)}")
        s.append(f"{ind}  key: {Q(key)}")
        s.append(f"{ind}  delay: {delay}")
        if vt: s.append(f"{ind}  value_type: {vt}")
        if units: s.append(f"{ind}  units: {Q(units)}")
        if vm: s.append(f"{ind}  valuemap:\n{ind}    name: {Q(vm)}")
        if pre: s.append(f"{ind}  preprocessing:\n" + "\n".join(f"{ind}    - type: {t}\n{ind}      parameters:\n{ind}        - {Q(p)}" for t, p in pre))
        if tags: s.append(f"{ind}  tags:\n" + "\n".join(f"{ind}    - tag: {k}\n{ind}      value: {Q(v)}" for k, v in tags))
        if trig: s.append(f"{ind}  {'trigger_prototypes' if '{#' in key else 'triggers'}:\n" + "\n".join(trig))
        return "\n".join(s)
    def trg(name, expr, pri, ind, rec=None):
        s = f"{ind}- uuid: {u(ver+name+expr)}\n{ind}  expression: {Q(expr)}\n{ind}  name: {Q(name)}\n{ind}  priority: {pri}"
        if rec: s += f"\n{ind}  recovery_mode: RECOVERY_EXPRESSION\n{ind}  recovery_expression: {Q(rec)}"
        return s
    K = 'Eltex MES2408C by SNMP'
    items = [
        item('ICMP ping', 'icmpping', 'SIMPLE', vm='Service state', tags=[('component','network')],
             trig=[trg('Eltex: нет ответа на ping (host {HOST.NAME})', f'max(/{K}/icmpping,#3)=0', 'HIGH', '            ')]),
        item('ICMP loss', 'icmppingloss', 'SIMPLE', vt='FLOAT', units='%', tags=[('component','network')],
             trig=[trg('Eltex: потери ICMP > 20%', f'min(/{K}/icmppingloss,5m)>20 and max(/{K}/icmpping,#3)=1', 'WARNING', '            ')]),
        item('ICMP response time', 'icmppingsec', 'SIMPLE', vt='FLOAT', units='s', tags=[('component','network')]),
        item('System description', 'sysDescr', 'SNMP_AGENT', '1.3.6.1.2.1.1.1.0', vt='CHAR', delay='1h', tags=[('component','system')]),
        item('Uptime', 'sysUpTime', 'SNMP_AGENT', '1.3.6.1.2.1.1.3.0', units='uptime', pre=[('MULTIPLIER','0.01')], tags=[('component','system')]),
    ]
    a("      items:\n" + "\n".join(items))
    ind = '            '
    def lld(name, key, oid, protos, filt=None):
        s = [f"        - uuid: {u(ver+key)}", f"          name: {Q(name)}", "          type: SNMP_AGENT", f"          snmp_oid: {Q(oid)}", f"          key: {Q(key)}", "          delay: 1h"]
        if filt: s.append(filt)
        s.append("          item_prototypes:\n" + "\n".join(protos))
        return "\n".join(s)
    port = lambda n,k,oid,**kw: item(n,k,'SNMP_AGENT',oid,ind=ind,tags=[('component','port'),('port','{#IFNAME}')],**kw)
    ps = [
        port('Port {#IFNAME}: Operational status', 'ifOperStatus[{#SNMPINDEX}]', '1.3.6.1.2.1.2.2.1.8.{#SNMPINDEX}', vm='IF-MIB::ifOperStatus',
             trig=[trg('Port {#IFNAME} ({#IFALIAS}): link down (host {HOST.NAME})', f'last(/{K}/ifOperStatus[{{#SNMPINDEX}}])=2 and last(/{K}/ifAdminStatus[{{#SNMPINDEX}}])=1', 'AVERAGE', ind+'    ')]),
        port('Port {#IFNAME}: Admin status', 'ifAdminStatus[{#SNMPINDEX}]', '1.3.6.1.2.1.2.2.1.7.{#SNMPINDEX}', vm='IF-MIB::ifAdminStatus'),
        port('Port {#IFNAME}: Connection', 'ifConnection[{#SNMPINDEX}]', '1.3.6.1.2.1.2.2.1.8.{#SNMPINDEX}', vm='Port connection'),
        port('Port {#IFNAME}: Bandwidth (speed)', 'ifHighSpeed[{#SNMPINDEX}]', '1.3.6.1.2.1.31.1.1.1.15.{#SNMPINDEX}', units='bps', pre=[('MULTIPLIER','1000000')], delay='5m'),
        port('Port {#IFNAME}: Inbound traffic', 'ifInOctets[{#SNMPINDEX}]', '1.3.6.1.2.1.31.1.1.1.6.{#SNMPINDEX}', units='bps', pre=[('CHANGE_PER_SECOND',''),('MULTIPLIER','8')]),
        port('Port {#IFNAME}: Outbound traffic', 'ifOutOctets[{#SNMPINDEX}]', '1.3.6.1.2.1.31.1.1.1.10.{#SNMPINDEX}', units='bps', pre=[('CHANGE_PER_SECOND',''),('MULTIPLIER','8')]),
    ]
    ifd = 'discovery[{#IFNAME},1.3.6.1.2.1.31.1.1.1.1,{#IFALIAS},1.3.6.1.2.1.31.1.1.1.18,{#IFTYPE},1.3.6.1.2.1.2.2.1.3]'
    filt = "          filter:\n            evaltype: AND\n            conditions:\n              - macro: '{#IFTYPE}'\n                value: '^6$'\n                formula: A"
    sd = lambda n,k,oid,**kw: item(n,k,'SNMP_AGENT',oid,ind=ind,vt='CHAR',delay='1h',tags=[('component','sfp')],**kw)
    sfp = [
        sd('SFP {#SFPNAME}: Model', 'sfp.model[{#SNMPINDEX}]', '1.3.6.1.2.1.47.1.1.1.1.13.{#SNMPINDEX}'),
        sd('SFP {#SFPNAME}: Vendor', 'sfp.vendor[{#SNMPINDEX}]', '1.3.6.1.2.1.47.1.1.1.1.12.{#SNMPINDEX}'),
        sd('SFP {#SFPNAME}: Serial number', 'sfp.serial[{#SNMPINDEX}]', '1.3.6.1.2.1.47.1.1.1.1.11.{#SNMPINDEX}'),
    ]
    sfpd = 'discovery[{#SFPNAME},1.3.6.1.2.1.47.1.1.1.1.2,{#SFPMODEL},1.3.6.1.2.1.47.1.1.1.1.13]'
    sfpf = "          filter:\n            evaltype: AND\n            conditions:\n              - macro: '{#SFPMODEL}'\n                value: '.+'\n                formula: A\n              - macro: '{#SFPNAME}'\n                value: '(?i)sfp|transceiver'\n                formula: B"
    pw = [
        item('PSU {#PSUNAME}: Status', 'psu.status[{#SNMPINDEX}]', 'SNMP_AGENT', '1.3.6.1.4.1.89.83.1.2.1.3.{#SNMPINDEX}', ind=ind, vm='Eltex PSU/Fan state', tags=[('component','psu')],
             trig=[trg('PSU {#PSUNAME}: неисправен (host {HOST.NAME})', f'last(/{K}/psu.status[{{#SNMPINDEX}}])>=3 and last(/{K}/psu.status[{{#SNMPINDEX}}])<=6', 'HIGH', ind+'    ')])]
    pwd = 'discovery[{#PSUNAME},1.3.6.1.4.1.89.83.1.2.1.2]'
    tp = [
        item('Temperature sensor {#SNMPINDEX}', 'sensor.temp[{#SNMPINDEX}]', 'SNMP_AGENT', '1.3.6.1.4.1.89.53.15.1.10.{#SNMPINDEX}', ind=ind, units='°C', tags=[('component','temperature')],
             trig=[trg('Температура {#SNMPINDEX} выше {$TEMP_WARN}°C', f'min(/{K}/sensor.temp[{{#SNMPINDEX}}],5m)>{{$TEMP_WARN}}', 'WARNING', ind+'    ', rec=f'max(/{K}/sensor.temp[{{#SNMPINDEX}}],5m)<{{$TEMP_WARN}}-3'),
                  trg('Температура {#SNMPINDEX} выше {$TEMP_CRIT}°C', f'min(/{K}/sensor.temp[{{#SNMPINDEX}}],5m)>{{$TEMP_CRIT}}', 'HIGH', ind+'    ')])]
    tpd = 'discovery[{#SENSOR},1.3.6.1.4.1.89.53.15.1.10]'
    a("      discovery_rules:\n" + "\n".join([
        lld('Port discovery','port.discovery',ifd,ps,filt),
        lld('SFP discovery','sfp.discovery',sfpd,sfp,sfpf),
        lld('PSU discovery','psu.discovery',pwd,pw),
        lld('Temperature discovery','temp.discovery',tpd,tp)]))
    a("      macros:\n        - macro: '{$TEMP_WARN}'\n          value: '60'\n        - macro: '{$TEMP_CRIT}'\n          value: '75'\n      valuemaps:")
    def vmap(n, m): return f"        - uuid: {u(ver+n)}\n          name: {Q(n)}\n          mappings:\n" + "\n".join(f"            - value: {Q(v)}\n              newvalue: {Q(t)}" for v,t in m)
    a("\n".join([
        vmap('Service state',[('0','Down'),('1','Up')]),
        vmap('IF-MIB::ifOperStatus',[('1','up'),('2','down'),('3','testing'),('4','unknown'),('5','dormant'),('6','notPresent'),('7','lowerLayerDown')]),
        vmap('IF-MIB::ifAdminStatus',[('1','up'),('2','down'),('3','testing')]),
        vmap('Port connection',[('1','connected'),('2','disconnected'),('3','disconnected'),('4','disconnected'),('5','disconnected'),('6','disconnected'),('7','disconnected')]),
        vmap('Eltex PSU/Fan state',[('1','normal'),('2','warning'),('3','critical'),('4','shutdown'),('5','notPresent'),('6','notFunctioning')])]))
    return "\n".join(o) + "\n"

if __name__ == '__main__':
    for v, d in (('6.0','zabbix_6.0'),('7.4','zabbix_7.4')):
        open(f'{d}/template_eltex_mes2408c_snmp.yaml','w').write(build(v))
