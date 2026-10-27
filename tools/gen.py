#!/usr/bin/env python3
"""Генератор шаблонов Zabbix для Eltex MES2408C (SNMP). Использование: gen.py 6.0|7.4"""
import sys, uuid

ver = sys.argv[1]
NAME = "Eltex MES2408C SNMP"
GROUP = "Templates/Network devices"


def u(key):
    h = list(uuid.uuid5(uuid.NAMESPACE_DNS, f"mes2408c-{ver}-{key}").hex)
    h[12] = "4"
    h[16] = "8"
    return "".join(h)


out = []


def w(s=""):
    out.append(s)


def q(s):
    return "'" + s.replace("'", "''") + "'"


def item(key, name, oid=None, itype="SNMP_AGENT", vtype="UNSIGNED", units=None, delay="1m",
         valuemap=None, preproc=None, ind=8, trigs=None, proto=False, desc=None, history="7d",
         tags=None):
    p = " " * ind
    w(f"{p}- uuid: {u(key + name)}")
    w(f"{p}  name: {q(name)}")
    if itype != "ZABBIX_PASSIVE":
        w(f"{p}  type: {itype}")
    if oid:
        w(f"{p}  snmp_oid: {q(oid)}")
    w(f"{p}  key: {q(key)}")
    w(f"{p}  delay: {delay}")
    w(f"{p}  history: {history}")
    if vtype != "UNSIGNED":
        w(f"{p}  value_type: {vtype}")
    if vtype == "FLOAT" or vtype == "TEXT" or vtype == "CHAR":
        pass
    if units:
        w(f"{p}  units: {q(units)}")
    if valuemap:
        w(f"{p}  valuemap:")
        w(f"{p}    name: {q(valuemap)}")
    if desc:
        w(f"{p}  description: {q(desc)}")
    if vtype in ("TEXT", "CHAR"):
        w(f"{p}  trends: '0'")
    if preproc:
        w(f"{p}  preprocessing:")
        for t, params in preproc:
            w(f"{p}    - type: {t}")
            if params:
                w(f"{p}      parameters:")
                w(f"{p}        - {q(params)}")
    if tags:
        w(f"{p}  tags:")
        for k, v in tags:
            w(f"{p}    - tag: {k}")
            w(f"{p}      value: {q(v)}")
    if trigs:
        w(f"{p}  trigger_prototypes:" if proto else f"{p}  triggers:")
        for tname, expr, prio in trigs:
            w(f"{p}    - uuid: {u(key + tname)}")
            w(f"{p}      expression: {q(expr)}")
            w(f"{p}      name: {q(tname)}")
            w(f"{p}      priority: {prio}")


def lld(key, name, oid_disc, filt_macro, filt_re, protos):
    w(f"        - uuid: {u(key)}")
    w(f"          name: {q(name)}")
    w(f"          type: SNMP_AGENT")
    w(f"          snmp_oid: {q(oid_disc)}")
    w(f"          key: {q(key)}")
    w(f"          delay: 1h")
    if filt_macro:
        w(f"          filter:")
        w(f"            conditions:")
        w(f"              - macro: {q(filt_macro)}")
        w(f"                value: {q(filt_re)}")
        w(f"                formulaid: A")
    w(f"          item_prototypes:")
    for p in protos:
        item(**p, ind=12, proto=True)


w("zabbix_export:")
w(f"  version: '{ver}'")
if ver == "6.0":
    w(f"  date: '2026-10-27T00:00:00Z'")
w("  groups:")
w(f"    - uuid: {u('group')}")
w(f"      name: {q(GROUP)}")
w("  templates:")
w(f"    - uuid: {u('template')}")
w(f"      template: {q(NAME)}")
w(f"      name: {q(NAME)}")
w("      description: |")
w("        Мониторинг коммутатора Eltex MES2408C по ICMP и SNMP v2c/v3.")
w("        Пинг, порты (admin/oper статус, скорость, трафик), SFP, блоки питания, температура.")
w("        Версия Zabbix: " + ver)
w("      groups:")
w(f"        - name: {q(GROUP)}")
w("      items:")

# --- Пинг ---
item("icmpping", "ICMP ping", itype="SIMPLE", valuemap="Service state", delay="1m",
     trigs=[("Eltex MES2408C: нет ответа на ping ({HOST.NAME})",
             "max(/%s/icmpping,#3)=0" % NAME, "HIGH")], ind=8)
item("icmppingsec", "ICMP response time", itype="SIMPLE", vtype="FLOAT", units="s", ind=8)
item("icmppingloss", "ICMP loss", itype="SIMPLE", vtype="FLOAT", units="%", ind=8)
# --- Система ---
item("system.descr", "System description", oid="1.3.6.1.2.1.1.1.0", vtype="TEXT", delay="1h", ind=8)
item("system.uptime", "Uptime", oid="1.3.6.1.2.1.1.3.0", units="uptime", ind=8,
     preproc=[("MULTIPLIER", "0.01")], vtype="FLOAT")
# --- Температура (Eltex/Marvell rlPhdUnitEnvParamTable, unit 1) ---
item("eltex.temp[1]", "Temperature", oid="1.3.6.1.4.1.89.53.15.1.10.1", units="°C", ind=8,
     trigs=[("Eltex MES2408C: высокая температура ({ITEM.LASTVALUE1})",
             "min(/%s/eltex.temp[1],5m)>{$MES.TEMP.WARN}" % NAME, "WARNING"),
            ("Eltex MES2408C: критическая температура ({ITEM.LASTVALUE1})",
             "min(/%s/eltex.temp[1],5m)>{$MES.TEMP.CRIT}" % NAME, "HIGH")])
item("eltex.temp.status[1]", "Temperature sensor status", oid="1.3.6.1.4.1.89.53.15.1.9.1",
     valuemap="Eltex sensor state", ind=8,
     trigs=[("Eltex MES2408C: датчик температуры в состоянии warning/critical",
             "last(/%s/eltex.temp.status[1])>=3" % NAME, "HIGH")])

w("      discovery_rules:")
# --- Порты ---
PORT_FILT = "{$IF.NAME.MATCHES}"
lld("net.if.discovery", "Network interfaces discovery", "discovery[{#IFDESCR},1.3.6.1.2.1.2.2.1.2,{#IFALIAS},1.3.6.1.2.1.31.1.1.1.18]",
    "{#IFDESCR}", "{$IF.NAME.MATCHES}", [
    dict(key="net.if.admin[{#SNMPINDEX}]", name="Port {#IFDESCR}: Admin status (up/down)",
         oid="1.3.6.1.2.1.2.2.1.7.{#SNMPINDEX}", valuemap="IF admin status"),
    dict(key="net.if.oper[{#SNMPINDEX}]", name="Port {#IFDESCR}: Link state (connected/disconnected)",
         oid="1.3.6.1.2.1.2.2.1.8.{#SNMPINDEX}", valuemap="IF oper status",
         trigs=[("Eltex MES2408C: порт {#IFDESCR} - нет линка (disconnected)",
                 "last(/%s/net.if.oper[{#SNMPINDEX}])=2 and last(/%s/net.if.admin[{#SNMPINDEX}])=1" % (NAME, NAME), "WARNING")]),
    dict(key="net.if.speed[{#SNMPINDEX}]", name="Port {#IFDESCR}: Bandwidth (negotiated speed)",
         oid="1.3.6.1.2.1.31.1.1.1.15.{#SNMPINDEX}", units="bps",
         preproc=[("MULTIPLIER", "1000000")]),
    dict(key="net.if.in[{#SNMPINDEX}]", name="Port {#IFDESCR}: Incoming traffic",
         oid="1.3.6.1.2.1.31.1.1.1.6.{#SNMPINDEX}", units="bps", vtype="FLOAT",
         preproc=[("CHANGE_PER_SECOND", None), ("MULTIPLIER", "8")]),
    dict(key="net.if.out[{#SNMPINDEX}]", name="Port {#IFDESCR}: Outgoing traffic",
         oid="1.3.6.1.2.1.31.1.1.1.10.{#SNMPINDEX}", units="bps", vtype="FLOAT",
         preproc=[("CHANGE_PER_SECOND", None), ("MULTIPLIER", "8")]),
    dict(key="net.if.in.errors[{#SNMPINDEX}]", name="Port {#IFDESCR}: Incoming errors",
         oid="1.3.6.1.2.1.2.2.1.14.{#SNMPINDEX}", units="pps", vtype="FLOAT",
         preproc=[("CHANGE_PER_SECOND", None)]),
    dict(key="net.if.out.errors[{#SNMPINDEX}]", name="Port {#IFDESCR}: Outgoing errors",
         oid="1.3.6.1.2.1.2.2.1.20.{#SNMPINDEX}", units="pps", vtype="FLOAT",
         preproc=[("CHANGE_PER_SECOND", None)]),
])
# --- Блоки питания ---
lld("eltex.psu.discovery", "Power supply discovery", "discovery[{#PSUDESCR},1.3.6.1.4.1.89.83.1.2.1.2]",
    None, None, [
    dict(key="eltex.psu.state[{#SNMPINDEX}]", name="PSU {#PSUDESCR}: State",
         oid="1.3.6.1.4.1.89.83.1.2.1.3.{#SNMPINDEX}", valuemap="Eltex sensor state",
         trigs=[("Eltex MES2408C: блок питания {#PSUDESCR} неисправен",
                 "last(/%s/eltex.psu.state[{#SNMPINDEX}])>=2 and last(/%s/eltex.psu.state[{#SNMPINDEX}])<>5" % (NAME, NAME), "HIGH")]),
])
# --- SFP ---
lld("eltex.sfp.discovery", "SFP modules discovery (ENTITY-MIB)",
    "discovery[{#SFPDESCR},1.3.6.1.2.1.47.1.1.1.1.2]",
    "{#SFPDESCR}", "{$MES.SFP.MATCHES}", [
    dict(key="eltex.sfp.model[{#SNMPINDEX}]", name="SFP {#SFPDESCR}: Model",
         oid="1.3.6.1.2.1.47.1.1.1.1.13.{#SNMPINDEX}", vtype="CHAR", delay="1h"),
    dict(key="eltex.sfp.serial[{#SNMPINDEX}]", name="SFP {#SFPDESCR}: Serial number",
         oid="1.3.6.1.2.1.47.1.1.1.1.11.{#SNMPINDEX}", vtype="CHAR", delay="1h"),
    dict(key="eltex.sfp.vendor[{#SNMPINDEX}]", name="SFP {#SFPDESCR}: Vendor",
         oid="1.3.6.1.2.1.47.1.1.1.1.12.{#SNMPINDEX}", vtype="CHAR", delay="1h"),
])

w("      macros:")
for m, v, d in [
    ("{$MES.TEMP.WARN}", "60", "Порог температуры Warning, °C"),
    ("{$MES.TEMP.CRIT}", "75", "Порог температуры High, °C"),
    ("{$IF.NAME.MATCHES}", "^(gi|fa|te|Port|port|gigabitethernet|GigabitEthernet|oob|tengigabitethernet).*", "Фильтр портов для LLD"),
    ("{$MES.SFP.MATCHES}", "(?i)sfp|transceiver", "Фильтр SFP-модулей в ENTITY-MIB"),
    ("{$SNMP_COMMUNITY}", "public", "SNMP community"),
]:
    w(f"        - macro: {q(m)}")
    w(f"          value: {q(v)}")
    w(f"          description: {q(d)}")

w("      valuemaps:")
for name, mp in [
    ("Service state", [(0, "Down"), (1, "Up")]),
    ("IF admin status", [(1, "up"), (2, "down"), (3, "testing")]),
    ("IF oper status", [(1, "connected"), (2, "disconnected"), (3, "testing"), (4, "unknown"),
                        (5, "dormant"), (6, "notPresent"), (7, "lowerLayerDown")]),
    ("Eltex sensor state", [(1, "normal"), (2, "warning"), (3, "critical"), (4, "shutdown"),
                            (5, "notPresent"), (6, "notFunctioning")]),
]:
    w(f"        - uuid: {u('vm' + name)}")
    w(f"          name: {q(name)}")
    w(f"          mappings:")
    for v, t in mp:
        w(f"            - value: '{v}'")
        w(f"              newvalue: {q(t)}")

# valuemaps live at export root in Zabbix 6.0/7.x? -> inside template for >=5.4
open(f"zabbix-{ver}/template_eltex_mes2408c_snmp.yaml", "w", encoding="utf-8").write("\n".join(out) + "\n")
