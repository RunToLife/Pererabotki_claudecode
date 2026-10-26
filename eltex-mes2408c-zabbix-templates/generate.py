#!/usr/bin/env python3
"""Генератор YAML-шаблонов Zabbix (6.0 и 7.4) для Eltex MES2408C."""
import uuid
import sys

NS = uuid.UUID("6f1c2c4e-7a1b-4c55-9a3e-2b7a1e0d0c01")


def uid(name):
    h = list(uuid.uuid5(NS, name).hex)
    h[12] = "4"
    h[16] = "8"
    return "".join(h)


def q(s):
    return '"' + str(s).replace("\\", "\\\\").replace('"', '\\"') + '"'


def item(ind, name, key, oid, version, value_type="UNSIGNED", units=None, delay="1m",
         pre=None, desc=None, history="7d", trends=None, valuemap=None, extra=None):
    p = " " * ind
    L = [f"{p}- uuid: {uid(version + key)}",
         f"{p}  name: {q(name)}",
         f"{p}  type: SNMP_AGENT",
         f"{p}  snmp_oid: {q(oid)}",
         f"{p}  key: {q(key)}",
         f"{p}  delay: {delay}",
         f"{p}  history: {history}"]
    if trends is not None:
        L.append(f"{p}  trends: {trends}")
    if value_type != "UNSIGNED":
        L.append(f"{p}  value_type: {value_type}")
    if value_type in ("CHAR", "TEXT"):
        L.append(f"{p}  trends: '0'" if trends is None else "")
    if units:
        L.append(f"{p}  units: {q(units)}")
    if desc:
        L.append(f"{p}  description: {q(desc)}")
    if pre:
        L.append(f"{p}  preprocessing:")
        for t, params in pre:
            L.append(f"{p}    - type: {t}")
            L.append(f"{p}      parameters:")
            for x in params:
                L.append(f"{p}        - {q(x)}")
    if valuemap:
        L.append(f"{p}  valuemap:")
        L.append(f"{p}    name: {q(valuemap)}")
    if extra:
        L += [p + "  " + e for e in extra]
    L.append(f"{p}  tags:")
    L.append(f"{p}    - tag: component")
    L.append(f"{p}      value: {q(extra_tag(key))}")
    return [l for l in L if l != ""]


def extra_tag(key):
    for k, v in (("if", "network"), ("sfp", "sfp"), ("psu", "power"), ("temp", "temperature"), ("icmp", "network")):
        if key.startswith(k):
            return v
    return "system"


def trigger(ind, name, expr, prio, desc=None, version="", recovery=None):
    p = " " * ind
    L = [f"{p}- uuid: {uid(version + name)}",
         f"{p}  expression: {q(expr)}",
         f"{p}  name: {q(name)}",
         f"{p}  priority: {prio}"]
    if desc:
        L.append(f"{p}  description: {q(desc)}")
    return L


def valuemaps(ver):
    def vm(name, pairs):
        L = [f"    - uuid: {uid(ver + 'vm' + name)}", f"      name: {q(name)}", "      mappings:"]
        for v, n in pairs:
            L += [f"        - value: {q(v)}", f"          newvalue: {q(n)}"]
        return L
    L = ["  valuemaps:"]
    L += vm("IF-MIB::ifOperStatus", [(1, "up (connected)"), (2, "down (disconnected)"), (3, "testing"), (4, "unknown"),
                                      (5, "dormant"), (6, "notPresent"), (7, "lowerLayerDown")])
    L += vm("IF-MIB::ifAdminStatus", [(1, "enabled (up)"), (2, "disabled (down)"), (3, "testing")])
    L += vm("Eltex::PowerSupplyState", [(1, "normal"), (2, "warning"), (3, "critical"), (4, "shutdown"),
                                         (5, "notPresent"), (6, "notFunctioning")])
    return L


def build(ver):
    # ver: "6.0" или "7.4"
    t = f"Template Eltex MES2408C SNMP"
    bits = [("MULTIPLIER", ["8"]), ("CHANGE_PER_SECOND", [""])]
    out = ["zabbix_export:", f"  version: {q(ver)}", "  template_groups:",
           f"    - uuid: {uid(ver + 'group')}", "      name: Templates/Network devices", "  templates:",
           f"    - uuid: {uid(ver + 'tpl')}", f"      template: {q(t)}",
           f"      name: {q(t)}",
           "      description: |",
           "        Мониторинг коммутатора Eltex MES2408C по SNMP (v2c).",
           "        Ping, порты (up/down, скорость, трафик), SFP, блоки питания, температура.",
           "        Макросы: {$SNMP_COMMUNITY}, {$TEMP_WARN}, {$TEMP_CRIT}, {$ICMP_LOSS_WARN}, {$ICMP_RESPONSE_TIME_WARN}.",
           "      groups:", "        - name: Templates/Network devices"]

    # ---- обычные элементы
    items = []
    items += [ "      - uuid: " + uid(ver + "icmpping"),
        "        name: 'ICMP ping'", "        type: SIMPLE", "        key: icmpping", "        history: 7d",
        "        valuemap:", "          name: 'Service state'", "        tags:", "          - tag: component",
        "            value: network"]
    items = [x[2:] if False else x for x in items]
    items2 = []
    items2 += ["      - uuid: " + uid(ver + "icmppingloss"), "        name: 'ICMP loss'", "        type: SIMPLE",
               "        key: icmppingloss", "        value_type: FLOAT", "        units: '%'", "        history: 7d",
               "        tags:", "          - tag: component", "            value: network"]
    items2 += ["      - uuid: " + uid(ver + "icmppingsec"), "        name: 'ICMP response time'", "        type: SIMPLE",
               "        key: icmppingsec", "        value_type: FLOAT", "        units: s", "        history: 7d",
               "        tags:", "          - tag: component", "            value: network"]
    items2 += item(6, "Model / description", "system.descr", "1.3.6.1.2.1.1.1.0", ver, "TEXT", delay="1h", history="30d")
    items2 += item(6, "Uptime", "system.uptime", "1.3.6.1.2.1.1.3.0", ver, units="uptime", delay="1m",
                   pre=[("MULTIPLIER", ["0.01"])])
    # температура (RADLAN rlPhdUnitEnvParamTempSensorValue, unit 1)
    items2 += item(6, "Temperature", "temp.sensor", "1.3.6.1.4.1.89.53.15.1.10.1", ver, units="°C", delay="1m")
    out += ["      items:"] + items + items2

    # ---- LLD
    out += ["      discovery_rules:"]
    # порты
    out += [f"      - uuid: {uid(ver + 'lld_if')}", "        name: 'Network interfaces discovery'", "        type: SNMP_AGENT",
            "        snmp_oid: 'discovery[{#IFDESCR},1.3.6.1.2.1.2.2.1.2,{#IFNAME},1.3.6.1.2.1.31.1.1.1.1,{#IFALIAS},1.3.6.1.2.1.31.1.1.1.18,{#IFTYPE},1.3.6.1.2.1.2.2.1.3]'",
            "        key: if.discovery", "        delay: 1h", "        filter:", "          conditions:",
            "            - macro: '{#IFTYPE}'", "              value: '^6$'", "              formulaid: A",
            "        item_prototypes:"]
    ip = []
    ip += item(10, "Port {#IFNAME}: Operational status (up/down, connected)", "if.oper[{#SNMPINDEX}]",
               "1.3.6.1.2.1.2.2.1.8.{#SNMPINDEX}", ver, valuemap="IF-MIB::ifOperStatus", delay="1m")
    ip += item(10, "Port {#IFNAME}: Admin status", "if.admin[{#SNMPINDEX}]",
               "1.3.6.1.2.1.2.2.1.7.{#SNMPINDEX}", ver, valuemap="IF-MIB::ifAdminStatus", delay="5m")
    ip += item(10, "Port {#IFNAME}: Bandwidth (negotiated speed)", "if.speed[{#SNMPINDEX}]",
               "1.3.6.1.2.1.31.1.1.1.15.{#SNMPINDEX}", ver, units="bps", delay="5m",
               pre=[("MULTIPLIER", ["1000000"])])
    ip += item(10, "Port {#IFNAME}: Inbound traffic", "if.in[{#SNMPINDEX}]",
               "1.3.6.1.2.1.31.1.1.1.6.{#SNMPINDEX}", ver, units="bps", delay="1m",
               pre=[("CHANGE_PER_SECOND", [""]), ("MULTIPLIER", ["8"])])
    ip += item(10, "Port {#IFNAME}: Outbound traffic", "if.out[{#SNMPINDEX}]",
               "1.3.6.1.2.1.31.1.1.1.10.{#SNMPINDEX}", ver, units="bps", delay="1m",
               pre=[("CHANGE_PER_SECOND", [""]), ("MULTIPLIER", ["8"])])
    ip += item(10, "Port {#IFNAME}: Inbound errors", "if.inerr[{#SNMPINDEX}]",
               "1.3.6.1.2.1.2.2.1.14.{#SNMPINDEX}", ver, units="pps", delay="1m",
               pre=[("CHANGE_PER_SECOND", [""])])
    ip += item(10, "Port {#IFNAME}: Outbound errors", "if.outerr[{#SNMPINDEX}]",
               "1.3.6.1.2.1.2.2.1.20.{#SNMPINDEX}", ver, units="pps", delay="1m",
               pre=[("CHANGE_PER_SECOND", [""])])
    ip += item(10, "Port {#IFNAME}: Alias", "if.alias[{#SNMPINDEX}]", "1.3.6.1.2.1.31.1.1.1.18.{#SNMPINDEX}", ver,
               "CHAR", delay="1h", history="30d")
    out += ip
    out += ["        trigger_prototypes:"]
    out += trigger(10, "Port {#IFNAME}: Link is down", "last(/Template Eltex MES2408C SNMP/if.oper[{#SNMPINDEX}])=2 and last(/Template Eltex MES2408C SNMP/if.admin[{#SNMPINDEX}])=1", "AVERAGE", version=ver)
    # SFP
    out += [f"      - uuid: {uid(ver + 'lld_sfp')}", "        name: 'SFP modules discovery'", "        type: SNMP_AGENT",
            "        snmp_oid: 'discovery[{#SFPNAME},1.3.6.1.2.1.47.1.1.1.1.7,{#SFPCLASS},1.3.6.1.2.1.47.1.1.1.1.5]'",
            "        key: sfp.discovery", "        delay: 1h",
            "        description: 'Порты ENTITY-MIB класса port(10); у портов с вставленным SFP заполнено entPhysicalModelName/SerialNum.'",
            "        filter:", "          conditions:", "            - macro: '{#SFPCLASS}'", "              value: '^10$'",
            "              formulaid: A", "        item_prototypes:"]
    out += item(10, "SFP {#SFPNAME}: Module model", "sfp.model[{#SNMPINDEX}]", "1.3.6.1.2.1.47.1.1.1.1.13.{#SNMPINDEX}", ver, "CHAR", delay="1h", history="30d")
    out += item(10, "SFP {#SFPNAME}: Vendor", "sfp.vendor[{#SNMPINDEX}]", "1.3.6.1.2.1.47.1.1.1.1.12.{#SNMPINDEX}", ver, "CHAR", delay="1h", history="30d")
    out += item(10, "SFP {#SFPNAME}: Serial number", "sfp.serial[{#SNMPINDEX}]", "1.3.6.1.2.1.47.1.1.1.1.11.{#SNMPINDEX}", ver, "CHAR", delay="1h", history="30d")
    out += item(10, "SFP {#SFPNAME}: Description (type)", "sfp.descr[{#SNMPINDEX}]", "1.3.6.1.2.1.47.1.1.1.1.2.{#SNMPINDEX}", ver, "CHAR", delay="1h", history="30d")
    # PSU
    out += [f"      - uuid: {uid(ver + 'lld_psu')}", "        name: 'Power supply discovery'", "        type: SNMP_AGENT",
            "        snmp_oid: 'discovery[{#PSUNAME},1.3.6.1.4.1.89.83.1.2.1.2]'", "        key: psu.discovery",
            "        delay: 1h", "        item_prototypes:"]
    out += item(10, "PSU {#PSUNAME}: State", "psu.state[{#SNMPINDEX}]", "1.3.6.1.4.1.89.83.1.2.1.3.{#SNMPINDEX}", ver,
                valuemap="Eltex::PowerSupplyState", delay="1m")
    out += ["        trigger_prototypes:"]
    out += trigger(10, "PSU {#PSUNAME}: Not normal", "last(/Template Eltex MES2408C SNMP/psu.state[{#SNMPINDEX}])<>1 and last(/Template Eltex MES2408C SNMP/psu.state[{#SNMPINDEX}])<>5", "HIGH", version=ver)

    # триггеры
    out += ["      macros:",
            "        - macro: '{$SNMP_COMMUNITY}'", "          value: public",
            "        - macro: '{$TEMP_WARN}'", "          value: '60'",
            "        - macro: '{$TEMP_CRIT}'", "          value: '75'",
            "        - macro: '{$ICMP_LOSS_WARN}'", "          value: '20'",
            "        - macro: '{$ICMP_RESPONSE_TIME_WARN}'", "          value: '0.15'"]
    out_t = ["      triggers:"]
    out_t += trigger(8, "Eltex MES2408C: Unavailable by ICMP ping", "max(/Template Eltex MES2408C SNMP/icmpping,#3)=0", "HIGH", version=ver)
    out_t += trigger(8, "Eltex MES2408C: High ICMP loss", "min(/Template Eltex MES2408C SNMP/icmppingloss,5m)>{$ICMP_LOSS_WARN}", "WARNING", version=ver)
    out_t += trigger(8, "Eltex MES2408C: High ICMP response time", "avg(/Template Eltex MES2408C SNMP/icmppingsec,5m)>{$ICMP_RESPONSE_TIME_WARN}", "WARNING", version=ver)
    out_t += trigger(8, "Eltex MES2408C: High temperature (warning)", "min(/Template Eltex MES2408C SNMP/temp.sensor,5m)>{$TEMP_WARN}", "WARNING", version=ver)
    out_t += trigger(8, "Eltex MES2408C: High temperature (critical)", "min(/Template Eltex MES2408C SNMP/temp.sensor,5m)>{$TEMP_CRIT}", "HIGH", version=ver)
    out_t += trigger(8, "Eltex MES2408C: Device restarted", "last(/Template Eltex MES2408C SNMP/system.uptime)<10m", "INFO", version=ver)
    # триггеры должны идти перед macros, поэтому вставляем
    idx = out.index("      macros:")
    out[idx:idx] = out_t
    out += valuemaps(ver)
    # valuemap Service state нужен для icmpping
    out += [f"    - uuid: {uid(ver + 'vmservice')}", "      name: 'Service state'", "      mappings:",
            "        - value: '0'", "          newvalue: Down", "        - value: '1'", "          newvalue: Up"]
    return "\n".join(out) + "\n"


if __name__ == "__main__":
    for v, f in (("6.0", "zabbix_6.0/template_eltex_mes2408c_snmp.yaml"), ("7.4", "zabbix_7.4/template_eltex_mes2408c_snmp.yaml")):
        import os
        os.makedirs(os.path.dirname(f), exist_ok=True)
        open(f, "w", encoding="utf-8").write(build(v))
        print("written", f)
