#!/usr/bin/env python3
"""Generates Zabbix templates for Eltex MES2408C (6.0 and 7.4) into ../zabbix-<ver>/."""
import uuid, pathlib

ROOT = pathlib.Path(__file__).resolve().parent.parent
TPL = "Eltex MES2408C SNMP"
NS = uuid.UUID("6f0c1d3e-5a7b-4c2d-9e1f-0a1b2c3d4e5f")


def uid(name):
    h = uuid.uuid5(NS, name).hex
    return h[:12] + "4" + h[13:16] + "8" + h[17:]



def q(s):
    return "'" + str(s).replace("'", "''") + "'"


def item(key, name, oid, indent, vt="FLOAT", units="", delay="1m", prep=None,
         tags=(), desc="", snmp=True, proto=False, history="7d", trends="365d", trigs=()):
    p = " " * indent
    L = [f"{p}- uuid: {uid(name + key)}"]
    L.append(f"{p}  name: {q(name)}")
    L.append(f"{p}  type: {'SNMP_AGENT' if snmp else 'SIMPLE'}")
    if snmp:
        L.append(f"{p}  snmp_oid: {q(oid)}")
    L.append(f"{p}  key: {q(key)}")
    L.append(f"{p}  delay: {delay}")
    L.append(f"{p}  history: {history}")
    if vt != "TEXT":
        L.append(f"{p}  trends: {trends}")
    if vt != "FLOAT":
        L.append(f"{p}  value_type: {vt}")
    if units:
        L.append(f"{p}  units: {q(units)}")
    if desc:
        L.append(f"{p}  description: {q(desc)}")
    if prep:
        L.append(f"{p}  preprocessing:")
        for t, params in prep:
            L.append(f"{p}    - type: {t}")
            L.append(f"{p}      parameters:")
            L.append(f"{p}        - {q(params)}")
    if tags:
        L.append(f"{p}  tags:")
        for k, v in tags:
            L.append(f"{p}    - tag: {k}")
            L.append(f"{p}      value: {q(v)}")
    if trigs:
        L.append(f"{p}  trigger_prototypes:" if proto else f"{p}  triggers:")
        for nm, expr, prio, d in trigs:
            L.append(f"{p}    - uuid: {uid('t' + nm + key)}")
            L.append(f"{p}      expression: {q(expr)}")
            L.append(f"{p}      name: {q(nm)}")
            L.append(f"{p}      priority: {prio}")
            L.append(f"{p}      description: {q(d)}")
    return L


def drule(name, key, oid_disc, indent, filt, protos, desc):
    p = " " * indent
    L = [f"{p}- uuid: {uid('dr' + key)}",
         f"{p}  name: {q(name)}",
         f"{p}  type: SNMP_AGENT",
         f"{p}  snmp_oid: {q(oid_disc)}",
         f"{p}  key: {key}",
         f"{p}  delay: 1h",
         f"{p}  description: {q(desc)}"]
    if filt:
        macro, val = filt
        L += [f"{p}  filter:", f"{p}    evaltype: AND_OR", f"{p}    conditions:",
              f"{p}      - macro: {q(macro)}", f"{p}        value: {q(val)}",
              f"{p}        formulaid: A"]
    L.append(f"{p}  item_prototypes:")
    L += protos
    return L


def build(ver):
    I = 6  # indent of list items under template: items
    ok = [("Eltex MES2408C", "Network")]
    # ---- plain items
    items = []
    items += item("icmpping", "ICMP ping", "", I, vt="UNSIGNED", snmp=False, delay="1m", trends="365d",
                  tags=[("component", "network")], desc="1 - host reachable, 0 - not reachable",
                  trigs=[("Eltex: no ICMP response from {HOST.NAME}", f"max(/{TPL}/icmpping,#3)=0", "HIGH", "Switch does not answer ping")])
    items += item("icmppingloss", "ICMP loss", "", I, snmp=False, units="%", tags=[("component", "network")],
                  trigs=[("Eltex: high ICMP loss on {HOST.NAME}", f"min(/{TPL}/icmppingloss,5m)>{{$ICMP_LOSS_WARN}}", "WARNING", "")])
    items += item("icmppingsec", "ICMP response time", "", I, snmp=False, units="s", tags=[("component", "network")],
                  trigs=[("Eltex: high ICMP response time on {HOST.NAME}", f"min(/{TPL}/icmppingsec,5m)>{{$ICMP_RESPONSE_TIME_WARN}}", "WARNING", "")])
    items += item("sysUpTime", "Uptime", "1.3.6.1.2.1.1.3.0", I, units="uptime", prep=[("MULTIPLIER", "0.01")], tags=[("component", "system")])
    items += item("sysDescr", "System description", "1.3.6.1.2.1.1.1.0", I, vt="CHAR", delay="1h", history="7d", tags=[("component", "system")])
    # power supply (rlPhdUnitEnvParam, unit 1): 1 normal 2 warning 3 critical 4 shutdown 5 notPresent 6 notFunctioning 7 restore 8 notAvailable
    PSMAP = "1 - normal, 2 - warning, 3 - critical, 4 - shutdown, 5 - notPresent, 6 - notFunctioning, 7 - restore, 8 - notAvailable"
    items += item("psu.main.status", "Power supply: main status", "1.3.6.1.4.1.89.53.15.1.2.1", I, vt="UNSIGNED",
                  tags=[("component", "power")], desc=PSMAP,
                  trigs=[("Eltex: main power supply problem on {HOST.NAME}", f"last(/{TPL}/psu.main.status)>=2 and last(/{TPL}/psu.main.status)<>5 and last(/{TPL}/psu.main.status)<>8", "HIGH", PSMAP)])
    items += item("psu.redundant.status", "Power supply: redundant status", "1.3.6.1.4.1.89.53.15.1.3.1", I, vt="UNSIGNED",
                  tags=[("component", "power")], desc=PSMAP,
                  trigs=[("Eltex: redundant power supply problem on {HOST.NAME}", f"last(/{TPL}/psu.redundant.status)>=2 and last(/{TPL}/psu.redundant.status)<>5 and last(/{TPL}/psu.redundant.status)<>8", "AVERAGE", "Not triggered when no redundant PSU is installed (notPresent). " + PSMAP)])
    # temperature
    items += item("temp.value", "Temperature", "1.3.6.1.4.1.89.53.15.1.10.1", I, units="°C", tags=[("component", "temperature")],
                  desc="rlPhdUnitEnvParamTempSensorValue",
                  trigs=[("Eltex: temperature is above {$TEMP_WARN}°C on {HOST.NAME}", f"min(/{TPL}/temp.value,5m)>{{$TEMP_WARN}}", "WARNING", ""),
                         ("Eltex: temperature is above {$TEMP_CRIT}°C on {HOST.NAME}", f"min(/{TPL}/temp.value,5m)>{{$TEMP_CRIT}}", "HIGH", "")])
    items += item("temp.status", "Temperature sensor status", "1.3.6.1.4.1.89.53.15.1.9.1", I, vt="UNSIGNED",
                  tags=[("component", "temperature")], desc="1 - ok, 2 - unavailable, 3 - nonoperational, 4 - warning, 5 - critical (verify with snmpwalk on your firmware)",
                  trigs=[("Eltex: temperature sensor reports problem on {HOST.NAME}", f"last(/{TPL}/temp.status)>=4", "HIGH", "")])

    # ---- discovery: ports
    D = 8  # indent of prototype list items (under item_prototypes at 8)
    ifs = "{#SNMPINDEX}"
    tg = [("component", "network"), ("interface", "{#IFNAME}")]
    pp = []
    pp += item(f"net.if.status[{ifs}]", "Interface {#IFNAME}: operational status", f"1.3.6.1.2.1.2.2.1.8.{ifs}", D, vt="UNSIGNED", proto=True,
               tags=tg, desc="IF-MIB ifOperStatus: 1 up, 2 down, 3 testing, 5 dormant, 7 lowerLayerDown",
               trigs=[("Interface {#IFNAME}: link down", f"last(/{TPL}/net.if.status[{ifs}])=2 and last(/{TPL}/net.if.admin[{ifs}])=1", "AVERAGE", "Port is administratively up but link is down (disconnected)")])
    pp += item(f"net.if.admin[{ifs}]", "Interface {#IFNAME}: administrative status", f"1.3.6.1.2.1.2.2.1.7.{ifs}", D, vt="UNSIGNED", proto=True,
               tags=tg, desc="1 up (enabled), 2 down (disabled)")
    pp += item(f"net.if.speed[{ifs}]", "Interface {#IFNAME}: bandwidth (negotiated speed)", f"1.3.6.1.2.1.31.1.1.1.15.{ifs}", D, proto=True, units="bps",
               prep=[("MULTIPLIER", "1000000")], tags=tg, desc="IF-MIB ifHighSpeed, converted from Mbps to bps")
    pp += item(f"net.if.in[{ifs}]", "Interface {#IFNAME}: bits received", f"1.3.6.1.2.1.31.1.1.1.6.{ifs}", D, proto=True, units="bps",
               prep=[("CHANGE_PER_SECOND", ""), ("MULTIPLIER", "8")], tags=tg, desc="ifHCInOctets")
    pp += item(f"net.if.out[{ifs}]", "Interface {#IFNAME}: bits sent", f"1.3.6.1.2.1.31.1.1.1.10.{ifs}", D, proto=True, units="bps",
               prep=[("CHANGE_PER_SECOND", ""), ("MULTIPLIER", "8")], tags=tg, desc="ifHCOutOctets")
    pp += item(f"net.if.in.errors[{ifs}]", "Interface {#IFNAME}: inbound errors", f"1.3.6.1.2.1.2.2.1.14.{ifs}", D, proto=True, units="pps",
               prep=[("CHANGE_PER_SECOND", "")], tags=tg)
    pp += item(f"net.if.out.errors[{ifs}]", "Interface {#IFNAME}: outbound errors", f"1.3.6.1.2.1.2.2.1.20.{ifs}", D, proto=True, units="pps",
               prep=[("CHANGE_PER_SECOND", "")], tags=tg)
    # ifType 6 = ethernetCsmacd
    disc_if = "discovery[{#IFNAME},1.3.6.1.2.1.31.1.1.1.1,{#IFALIAS},1.3.6.1.2.1.31.1.1.1.18,{#IFTYPE},1.3.6.1.2.1.2.2.1.3]"

    # ---- discovery: SFP via ENTITY-MIB
    sg = [("component", "sfp"), ("entity", "{#ENT_NAME}")]
    sp = []
    sp += item(f"sfp.descr[{ifs}]", "SFP {#ENT_NAME}: description", f"1.3.6.1.2.1.47.1.1.1.1.2.{ifs}", D, vt="CHAR", proto=True, delay="1h", history="30d", tags=sg)
    sp += item(f"sfp.model[{ifs}]", "SFP {#ENT_NAME}: model", f"1.3.6.1.2.1.47.1.1.1.1.13.{ifs}", D, vt="CHAR", proto=True, delay="1h", history="30d", tags=sg)
    sp += item(f"sfp.vendor[{ifs}]", "SFP {#ENT_NAME}: vendor", f"1.3.6.1.2.1.47.1.1.1.1.12.{ifs}", D, vt="CHAR", proto=True, delay="1h", history="30d", tags=sg)
    sp += item(f"sfp.serial[{ifs}]", "SFP {#ENT_NAME}: serial number", f"1.3.6.1.2.1.47.1.1.1.1.11.{ifs}", D, vt="CHAR", proto=True, delay="1h", history="30d", tags=sg)
    disc_sfp = "discovery[{#ENT_NAME},1.3.6.1.2.1.47.1.1.1.1.7,{#ENT_DESCR},1.3.6.1.2.1.47.1.1.1.1.2]"

    L = []
    if ver == "6.0":
        L += ["zabbix_export:", "  version: '6.0'", "  date: '2026-10-24T00:00:00Z'", "  groups:"]
        L += [f"    - uuid: {uid('group')}", "      name: Templates/Network devices"]
    else:
        L += ["zabbix_export:", "  version: '7.4'", "  template_groups:"]
        L += [f"    - uuid: {uid('group')}", "      name: Templates/Network devices"]
    L += ["  templates:", f"    - uuid: {uid('template')}", f"      template: {q(TPL)}",
          f"      name: {q(TPL)}",
          "      description: 'Eltex MES2408C monitoring via SNMP (v2c/v3) and ICMP. Zabbix " + ver + ".'",
          "      vendor:", "        name: Eltex", "        version: MES2408C" if ver == "7.4" else "", "      groups:",
          "        - name: Templates/Network devices"]
    L = [x for x in L if x != ""]
    if ver == "6.0":
        L = [x for x in L if not x.startswith("      vendor:") and not x.startswith("        name: Eltex") and "version: MES2408C" not in x]
    L.append("      items:")
    L += items
    L.append("      discovery_rules:")
    L += drule("Port discovery", "net.if.discovery", disc_if, 6,
               ("{#IFTYPE}", "^6$"), pp,
               "Discovers Ethernet ports (ifType=6). Exclude/include ports with {$IF.NAME.MATCHES}-style filters by editing the rule.")
    L += drule("SFP module discovery", "sfp.discovery", disc_sfp, 6,
               ("{#ENT_DESCR}", "{$SFP.DESCR.MATCHES}"), sp,
               "Discovers inserted SFP modules from ENTITY-MIB (entPhysicalTable); the module appears there only when it is present.")
    L += ["      macros:"]
    for m, v, d in [("{$SNMP_COMMUNITY}", "public", "SNMP v2c community"),
                    ("{$TEMP_WARN}", "55", "Temperature warning threshold, °C"),
                    ("{$TEMP_CRIT}", "70", "Temperature critical threshold, °C"),
                    ("{$ICMP_LOSS_WARN}", "20", "ICMP loss warning, %"),
                    ("{$ICMP_RESPONSE_TIME_WARN}", "0.15", "ICMP response time warning, s"),
                    ("{$SFP.DESCR.MATCHES}", "(?i)sfp|transceiver|gbic", "Regex of entPhysicalDescr treated as an SFP module")]:
        L += [f"        - macro: {q(m)}", f"          value: {q(v)}", f"          description: {q(d)}"]
    return "\n".join(L) + "\n"


for v in ("6.0", "7.4"):
    (ROOT / f"zabbix-{v}" / "template_eltex_mes2408c_snmp.yaml").write_text(build(v), encoding="utf-8")
