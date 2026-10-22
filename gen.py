#!/usr/bin/env python3
"""Генератор шаблонов Eltex MES2408C для Zabbix 6.0 и 7.4 (python3 gen.py)."""
import uuid, json

def u(): return uuid.uuid4().hex
def q(s): return json.dumps(s, ensure_ascii=False)

def item(name, key, oid, vt="FLOAT", units="", delay="1m", app="", extra="", t="SNMP_AGENT", ver="6.0"):
    s = f"""          - uuid: {u()}
            name: {q(name)}
            type: {t}
"""
    if oid: s += f"            snmp_oid: {q(oid)}\n"
    s += f"            key: {q(key)}\n            delay: {delay}\n            history: 7d\n"
    if vt != "FLOAT": s += f"            value_type: {vt}\n"
    if units: s += f"            units: {q(units)}\n"
    if vt in ("CHAR","TEXT"): s += "            trends: '0'\n"
    s += extra
    s += f"            tags:\n              - tag: component\n                value: {app}\n"
    return s

def trig(name, expr, prio="WARNING", ind=14):
    p=" "*(ind-14)
    return p+f"""              - uuid: {u()}
                name: {q(name)}
                expression: {q(expr)}
                priority: {prio}
""".replace("\n","\n"+p).rstrip(" ")

def build(ver):
    T = "Template Eltex MES2408C SNMP"
    h = f"""zabbix_export:
  version: '{ver}'
  template_groups:
    - uuid: {u()}
      name: Templates/Network devices
  templates:
    - uuid: {u()}
      template: {q(T)}
      name: {q(T)}
      description: Мониторинг Eltex MES2408C по SNMP (v2c). Макрос {{$SNMP_COMMUNITY}}.
      groups:
        - name: Templates/Network devices
      macros:
        - macro: '{{$SNMP_COMMUNITY}}'
          value: public
        - macro: '{{$TEMP.WARN}}'
          value: '60'
        - macro: '{{$TEMP.CRIT}}'
          value: '75'
        - macro: '{{$PORT.UTIL.WARN}}'
          value: '90'
      items:
"""
    # ping
    h += f"""          - uuid: {u()}
            name: ICMP ping
            type: SIMPLE
            key: icmpping
            delay: 1m
            history: 7d
            valuemap:
              name: Service state
            tags:
              - tag: component
                value: network
            triggers:
{trig('Eltex MES2408C: нет ответа на ping {HOST.NAME}', 'max(/Template Eltex MES2408C SNMP/icmpping,#3)=0', 'HIGH')}"""
    h += f"""          - uuid: {u()}
            name: ICMP время ответа
            type: SIMPLE
            key: icmppingsec
            delay: 1m
            history: 7d
            units: s
            tags:
              - tag: component
                value: network
"""
    # psu/temp: rlPhdUnitEnvParamTable (unit 1)
    ps = "1.3.6.1.4.1.89.53.15.1"
    st = "Статус: 1 normal, 2 warning, 3 critical, 4 shutdown, 5 notPresent, 6 notFunctioning"
    for nm, k, o in (("Блок питания основной: статус","psu.main",f"{ps}.2.1"),("Блок питания резервный: статус","psu.redundant",f"{ps}.3.1")):
        h += item(nm, f"eltex.{k}.status", o, app="power", ver=ver,
                  extra=f"            description: {q(st)}\n            triggers:\n"
                        + trig(nm.split(':')[0] + ": неисправность {HOST.NAME}", f"last(/{T}/eltex.{k}.status)>=3 and last(/{T}/eltex.{k}.status)<>5", "HIGH"))
    h += item("Температура", "eltex.temperature", f"{ps}.10.1", units="°C", app="temperature", ver=ver,
              extra="            triggers:\n"
              + trig("Температура выше порога {$TEMP.WARN}°C на {HOST.NAME}", f"min(/{T}/eltex.temperature,5m)>{{$TEMP.WARN}}")
              + trig("Температура критическая {$TEMP.CRIT}°C на {HOST.NAME}", f"min(/{T}/eltex.temperature,5m)>{{$TEMP.CRIT}}", "HIGH"))
    h += item("Системное время работы (uptime)", "sys.uptime", "1.3.6.1.2.1.1.3.0", units="uptime", app="system", ver=ver)
    h += item("Модель", "sys.descr", "1.3.6.1.2.1.1.1.0", vt="CHAR", delay="1h", app="system", ver=ver)

    def proto(name,key,oid,vt="FLOAT",units="",extra="",pre="",app="interface"):
        s = f"""              - uuid: {u()}
                name: {q(name)}
                type: SNMP_AGENT
                snmp_oid: {q(oid)}
                key: {q(key)}
                delay: 1m
                history: 7d
"""
        if vt!="FLOAT": s+=f"                value_type: {vt}\n"
        if vt in ("CHAR","TEXT"): s+="                trends: '0'\n"
        if units: s+=f"                units: {q(units)}\n"
        s+=pre
        s+=f"                tags:\n                  - tag: component\n                    value: {app}\n"
        return s+extra

    delta = """                preprocessing:
                  - type: CHANGE_PER_SECOND
                    parameters:
                      - ''
                  - type: MULTIPLIER
                    parameters:
                      - '8'
"""
    nl="\n"
    ifs_trig = trig('Порт {#IFDESCR} ({#IFALIAS}) недоступен (down) на {HOST.NAME}', f"last(/{T}/net.if.status[{{#SNMPINDEX}}])=2", "AVERAGE", 18)
    delta_only = delta.split("                  - type: MULTIPLIER")[0]
    P = {}
    P["st"] = proto('Порт {#IFDESCR}: состояние (1 up, 2 down)','net.if.status[{#SNMPINDEX}]','1.3.6.1.2.1.2.2.1.8.{#SNMPINDEX}',extra="                trigger_prototypes:\n"+ifs_trig)
    P["adm"] = proto('Порт {#IFDESCR}: административное состояние','net.if.admin[{#SNMPINDEX}]','1.3.6.1.2.1.2.2.1.7.{#SNMPINDEX}')
    P["con"] = proto('Порт {#IFDESCR}: connected/disconnected (carrier)','net.if.connected[{#SNMPINDEX}]','1.3.6.1.2.1.2.2.1.8.{#SNMPINDEX}',pre="                valuemap:\n                  name: IF oper status\n")
    P["spd"] = proto('Порт {#IFDESCR}: полоса пропускания (скорость)','net.if.speed[{#SNMPINDEX}]','1.3.6.1.2.1.31.1.1.1.15.{#SNMPINDEX}',units='Mbps')
    P["in"] = proto('Порт {#IFDESCR}: входящий трафик','net.if.in[{#SNMPINDEX}]','1.3.6.1.2.1.31.1.1.1.6.{#SNMPINDEX}',units='bps',pre=delta)
    P["out"] = proto('Порт {#IFDESCR}: исходящий трафик','net.if.out[{#SNMPINDEX}]','1.3.6.1.2.1.31.1.1.1.10.{#SNMPINDEX}',units='bps',pre=delta)
    P["err"] = proto('Порт {#IFDESCR}: ошибки входящие','net.if.in.errors[{#SNMPINDEX}]','1.3.6.1.2.1.2.2.1.14.{#SNMPINDEX}',units='pps',pre=delta_only)
    P["mod"] = proto('SFP {#SFPDESCR}: модель','eltex.sfp.model[{#SNMPINDEX}]','1.3.6.1.2.1.47.1.1.1.1.13.{#SNMPINDEX}',vt='CHAR',app='sfp')
    P["ser"] = proto('SFP {#SFPDESCR}: серийный номер','eltex.sfp.serial[{#SNMPINDEX}]','1.3.6.1.2.1.47.1.1.1.1.11.{#SNMPINDEX}',vt='CHAR',app='sfp')
    h += f"""      discovery_rules:
        - uuid: {u()}
          name: Обнаружение портов
          type: SNMP_AGENT
          snmp_oid: 'discovery[{{#IFDESCR}},1.3.6.1.2.1.2.2.1.2,{{#IFALIAS}},1.3.6.1.2.1.31.1.1.1.18,{{#IFTYPE}},1.3.6.1.2.1.2.2.1.3]'
          key: net.if.discovery
          delay: 1h
          filter:
            evaltype: AND_OR
            conditions:
              - macro: '{{#IFTYPE}}'
                value: '^6$'
                formulaid: A
          item_prototypes:
{P['st']}{P['adm']}{P['con']}{P['spd']}{P['in']}{P['out']}{P['err']}        - uuid: {u()}
          name: Обнаружение SFP модулей
          type: SNMP_AGENT
          snmp_oid: 'discovery[{{#SFPDESCR}},1.3.6.1.2.1.47.1.1.1.1.2,{{#SFPMODEL}},1.3.6.1.2.1.47.1.1.1.1.13,{{#SFPSERIAL}},1.3.6.1.2.1.47.1.1.1.1.11]'
          key: eltex.sfp.discovery
          delay: 1h
          filter:
            evaltype: AND_OR
            conditions:
              - macro: '{{#SFPDESCR}}'
                value: '(?i)sfp|transceiver'
                formulaid: A
          item_prototypes:
{P['mod']}{P['ser']}      valuemaps:
        - uuid: {u()}
          name: Service state
          mappings:
            - value: '0'
              newvalue: Down
            - value: '1'
              newvalue: Up
        - uuid: {u()}
          name: IF oper status
          mappings:
            - value: '1'
              newvalue: connected
            - value: '2'
              newvalue: disconnected
            - value: '7'
              newvalue: lowerLayerDown
"""
    return h

for v,d in (("6.0","zabbix-6.0"),("7.4","zabbix-7.4")):
    open(f"{d}/template_eltex_mes2408c.yaml","w",encoding="utf-8").write(build(v))
