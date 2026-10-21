#!/usr/bin/env python3
"""Генератор шаблонов Zabbix для Eltex MES2408C (версии 6.0 и 7.4).

Запуск: python3 tools/generate.py   (нужен PyYAML)
UUID детерминированы (uuid5), поэтому повторная генерация даёт тот же файл.
"""
import uuid
from pathlib import Path
import yaml

NS = uuid.UUID("6f1c1d0e-0b5e-4b8e-9a43-0e17e1a2b3c4")
ROOT = Path(__file__).resolve().parent.parent
TPL = "Eltex MES2408C SNMP"


def u(name):
    # UUIDv5 -> hex; Zabbix требует версию 4 в формате, поэтому подменяем nibble версии
    h = uuid.uuid5(NS, name).hex
    return h[:12] + "4" + h[13:16] + "8" + h[17:]


def tag(t, v):
    return {"tag": t, "value": v}


def snmp_item(name, key, oid, delay="1m", vt="FLOAT", units=None, valuemap=None,
              preprocessing=None, tags=None, descr=None, proto=False):
    d = {"uuid": u(("p:" if proto else "i:") + key), "name": name,
         "type": "SNMP_AGENT", "snmp_oid": oid, "key": key, "delay": delay,
         "history": "7d", "trends": "365d" if vt in ("FLOAT", "UNSIGNED") else "0"}
    if vt != "FLOAT":
        d["value_type"] = vt
    if vt == "TEXT" or vt == "CHAR":
        d["trends"] = "0"
    if units:
        d["units"] = units
    if valuemap:
        d["valuemap"] = {"name": valuemap}
    if preprocessing:
        d["preprocessing"] = preprocessing
    if descr:
        d["description"] = descr
    d["tags"] = tags or []
    return d


def trig(name, expr, prio="WARNING", rec=None, descr=None, proto=False, dep=None):
    d = {"uuid": u(("tp:" if proto else "t:") + name), "expression": expr, "name": name,
         "priority": prio}
    if rec:
        d["recovery_mode"] = "RECOVERY_EXPRESSION"
        d["recovery_expression"] = rec
    if descr:
        d["description"] = descr
    return d


def vmap(name, mapping):
    return {"uuid": u("vm:" + name), "name": name,
            "mappings": [{"value": str(k), "newvalue": v} for k, v in mapping.items()]}


def build(version):
    v7 = version == "7.4"
    L = lambda k: f"/{TPL}/{k}"

    valuemaps = [
        vmap("Eltex ICMP ping", {0: "Down", 1: "Up"}),
        vmap("Eltex ifOperStatus", {1: "up (connected)", 2: "down (disconnected)", 3: "testing",
                                    4: "unknown", 5: "dormant", 6: "notPresent",
                                    7: "lowerLayerDown"}),
        vmap("Eltex ifAdminStatus", {1: "up", 2: "down", 3: "testing"}),
        vmap("Eltex env state", {1: "normal", 2: "warning", 3: "critical", 4: "shutdown",
                                 5: "notPresent", 6: "notFunctioning"}),
    ]

    items = [
        {"uuid": u("i:icmpping"), "name": "ICMP ping", "type": "SIMPLE", "key": "icmpping",
         "delay": "30s", "history": "7d", "trends": "365d", "valuemap": {"name": "Eltex ICMP ping"},
         "tags": [tag("component", "network")]},
        {"uuid": u("i:icmppingsec"), "name": "ICMP response time", "type": "SIMPLE",
         "key": "icmppingsec", "delay": "30s", "history": "7d", "trends": "365d", "units": "s",
         "value_type": "FLOAT", "tags": [tag("component", "network")]},
        {"uuid": u("i:icmppingloss"), "name": "ICMP loss", "type": "SIMPLE",
         "key": "icmppingloss", "delay": "30s", "history": "7d", "trends": "365d", "units": "%",
         "tags": [tag("component", "network")]},
        snmp_item("System description", "system.descr", "1.3.6.1.2.1.1.1.0", "1h", "TEXT",
                  preprocessing=[{"type": "DISCARD_UNCHANGED_HEARTBEAT", "parameters": ["1d"]}],
                  tags=[tag("component", "system")]),
        snmp_item("System name", "system.name", "1.3.6.1.2.1.1.5.0", "1h", "TEXT",
                  preprocessing=[{"type": "DISCARD_UNCHANGED_HEARTBEAT", "parameters": ["1d"]}],
                  tags=[tag("component", "system")]),
        snmp_item("Uptime", "system.uptime", "1.3.6.1.2.1.1.3.0", "1m", "FLOAT", units="uptime",
                  preprocessing=[{"type": "MULTIPLIER", "parameters": ["0.01"]}],
                  tags=[tag("component", "system")]),
    ]

    triggers = [
        trig("Eltex MES2408C: недоступен по ICMP", f"max({L('icmpping')},#3)=0", "HIGH",
             descr="Устройство не отвечает на ping."),
        trig("Eltex MES2408C: потери ICMP выше {$ICMP_LOSS_WARN}%",
             f"min({L('icmppingloss')},5m)>{{$ICMP_LOSS_WARN}} and "
             f"min({L('icmppingloss')},5m)<100", "WARNING"),
        trig("Eltex MES2408C: время ответа ICMP выше {$ICMP_RESPONSE_TIME_WARN}",
             f"avg({L('icmppingsec')},5m)>{{$ICMP_RESPONSE_TIME_WARN}}", "WARNING"),
        trig("Eltex MES2408C: устройство перезагружалось (uptime < 10m)",
             f"last({L('system.uptime')})<10m", "INFO",
             descr="Uptime меньше 10 минут."),
    ]

    # ---------- Порты ----------
    port_oids = ("discovery[{#IFDESCR},1.3.6.1.2.1.2.2.1.2,{#IFTYPE},1.3.6.1.2.1.2.2.1.3,"
                 "{#IFALIAS},1.3.6.1.2.1.31.1.1.1.18]")
    bps = lambda: [{"type": "CHANGE_PER_SECOND", "parameters": [""]},
                   {"type": "MULTIPLIER", "parameters": ["8"]}]
    pt = [tag("component", "network"), tag("interface", "{#IFDESCR}")]
    port_items = [
        snmp_item("Port {#IFDESCR}: Operational status (up/down)",
                  "net.if.status[ifOperStatus.{#SNMPINDEX}]",
                  "1.3.6.1.2.1.2.2.1.8.{#SNMPINDEX}", "1m", "UNSIGNED",
                  valuemap="Eltex ifOperStatus", tags=pt + [tag("metric", "status")],
                  descr="up = connected, down = disconnected", proto=True),
        snmp_item("Port {#IFDESCR}: Admin status", "net.if.admin[ifAdminStatus.{#SNMPINDEX}]",
                  "1.3.6.1.2.1.2.2.1.7.{#SNMPINDEX}", "5m", "UNSIGNED",
                  valuemap="Eltex ifAdminStatus", tags=pt + [tag("metric", "status")], proto=True),
        snmp_item("Port {#IFDESCR}: Speed (bandwidth)", "net.if.speed[ifHighSpeed.{#SNMPINDEX}]",
                  "1.3.6.1.2.1.31.1.1.1.15.{#SNMPINDEX}", "5m", "UNSIGNED", units="bps",
                  preprocessing=[{"type": "MULTIPLIER", "parameters": ["1000000"]}],
                  tags=pt + [tag("metric", "speed")],
                  descr="Согласованная скорость порта (ifHighSpeed, Мбит/с -> бит/с).", proto=True),
        snmp_item("Port {#IFDESCR}: Bits received", "net.if.in[ifHCInOctets.{#SNMPINDEX}]",
                  "1.3.6.1.2.1.31.1.1.1.6.{#SNMPINDEX}", "1m", "FLOAT", units="bps",
                  preprocessing=bps(), tags=pt + [tag("metric", "traffic")], proto=True),
        snmp_item("Port {#IFDESCR}: Bits sent", "net.if.out[ifHCOutOctets.{#SNMPINDEX}]",
                  "1.3.6.1.2.1.31.1.1.1.10.{#SNMPINDEX}", "1m", "FLOAT", units="bps",
                  preprocessing=bps(), tags=pt + [tag("metric", "traffic")], proto=True),
        snmp_item("Port {#IFDESCR}: Inbound errors", "net.if.in.errors[ifInErrors.{#SNMPINDEX}]",
                  "1.3.6.1.2.1.2.2.1.14.{#SNMPINDEX}", "1m", "FLOAT", units="pps",
                  preprocessing=[{"type": "CHANGE_PER_SECOND", "parameters": [""]}],
                  tags=pt + [tag("metric", "errors")], proto=True),
        snmp_item("Port {#IFDESCR}: Outbound errors", "net.if.out.errors[ifOutErrors.{#SNMPINDEX}]",
                  "1.3.6.1.2.1.2.2.1.20.{#SNMPINDEX}", "1m", "FLOAT", units="pps",
                  preprocessing=[{"type": "CHANGE_PER_SECOND", "parameters": [""]}],
                  tags=pt + [tag("metric", "errors")], proto=True),
    ]
    st, ad = "net.if.status[ifOperStatus.{#SNMPINDEX}]", "net.if.admin[ifAdminStatus.{#SNMPINDEX}]"
    port_triggers = [
        trig("Port {#IFDESCR}: Link down (disconnected)",
             f"last({L(st)})=2 and last({L(ad)})=1", "AVERAGE", proto=True,
             descr="Порт включён администратором, но линк отсутствует."),
        trig("Port {#IFDESCR}: Speed changed",
             f"change({L('net.if.speed[ifHighSpeed.{#SNMPINDEX}]')})<>0 and "
             f"last({L(st)})=1", "INFO", proto=True),
    ]
    ports = {"uuid": u("d:ports"), "name": "Network interfaces discovery", "type": "SNMP_AGENT",
             "snmp_oid": port_oids, "key": "net.if.discovery", "delay": "1h",
             "filter": {"evaltype": "AND_OR", "conditions": [
                 {"macro": "{#IFTYPE}", "value": "^6$", "formulaid": "A"},
                 {"macro": "{#IFDESCR}", "value": "{$NET.IF.IFNAME.MATCHES}", "formulaid": "B"},
                 {"macro": "{#IFDESCR}", "value": "{$NET.IF.IFNAME.NOT_MATCHES}",
                  "operator": "NOT_MATCHES_REGEX", "formulaid": "C"}]},
             "description": "Физические Ethernet-порты (ifType=6).",
             "item_prototypes": port_items, "trigger_prototypes": port_triggers}

    # ---------- SFP ----------
    sfp_base = "1.3.6.1.4.1.35265.1.23.53.1.1.1"
    sp = [tag("component", "sfp"), tag("interface", "{#IFDESCR}")]
    sfp_items = []
    for nm, col, k in (("Type", 2, "type"), ("Vendor", 3, "vendor"), ("Part number", 4, "pn"),
                       ("Serial number", 5, "sn")):
        sfp_items.append(snmp_item(f"SFP {{#IFDESCR}}: {nm}", f"sfp.{k}[{{#SNMPINDEX}}]",
                                   f"{sfp_base}.{col}.{{#SNMPINDEX}}", "1h", "CHAR",
                                   preprocessing=[{"type": "DISCARD_UNCHANGED_HEARTBEAT",
                                                   "parameters": ["1d"]}],
                                   tags=sp, proto=True))
    sfp = {"uuid": u("d:sfp"), "name": "SFP modules discovery", "type": "SNMP_AGENT",
           "snmp_oid": f"discovery[{{#SFPTYPE}},{sfp_base}.2,{{#IFDESCR}},1.3.6.1.2.1.2.2.1.2]",
           "key": "sfp.discovery", "delay": "1h",
           "filter": {"evaltype": "AND_OR", "conditions": [
               {"macro": "{#SFPTYPE}", "value": ".+", "formulaid": "A"}]},
           "description": "Вставленные SFP-модули (Eltex PHD MIB, 1.3.6.1.4.1.35265). "
                          "Проверьте OID командой snmpwalk на вашей прошивке, см. README.",
           "item_prototypes": sfp_items}

    # ---------- Питание и температура ----------
    env_oid = "1.3.6.1.4.1.89.53.15.1"
    et = [tag("component", "environment")]
    env_items = [
        snmp_item("Unit {#SNMPINDEX}: Main power supply status", "env.psu.main[{#SNMPINDEX}]",
                  f"{env_oid}.2.{{#SNMPINDEX}}", "1m", "UNSIGNED", valuemap="Eltex env state",
                  tags=et + [tag("metric", "power")], proto=True),
        snmp_item("Unit {#SNMPINDEX}: Redundant power supply status",
                  "env.psu.redundant[{#SNMPINDEX}]", f"{env_oid}.3.{{#SNMPINDEX}}", "1m",
                  "UNSIGNED", valuemap="Eltex env state",
                  tags=et + [tag("metric", "power")], proto=True),
        snmp_item("Unit {#SNMPINDEX}: Temperature", "env.temp[{#SNMPINDEX}]",
                  f"{env_oid}.10.{{#SNMPINDEX}}", "1m", "FLOAT", units="°C",
                  tags=et + [tag("metric", "temperature")], proto=True),
    ]
    pm, pr, tk = ("env.psu.main[{#SNMPINDEX}]", "env.psu.redundant[{#SNMPINDEX}]",
                  "env.temp[{#SNMPINDEX}]")
    env_triggers = [
        trig("Unit {#SNMPINDEX}: Main power supply is not normal",
             f"last({L(pm)})<>1", "HIGH", proto=True,
             descr="1 normal, 2 warning, 3 critical, 4 shutdown, 5 notPresent, 6 notFunctioning."),
        trig("Unit {#SNMPINDEX}: Redundant power supply failure",
             f"last({L(pr)})<>1 and last({L(pr)})<>5", "AVERAGE", proto=True,
             descr="Состояние 5 (notPresent) не считается аварией."),
        trig("Unit {#SNMPINDEX}: Temperature is above {$TEMP_WARN}°C",
             f"min({L(tk)},5m)>{{$TEMP_WARN}}", "WARNING", proto=True,
             rec=f"max({L(tk)},5m)<{{$TEMP_WARN}}-3"),
        trig("Unit {#SNMPINDEX}: Temperature is above {$TEMP_CRIT}°C",
             f"min({L(tk)},5m)>{{$TEMP_CRIT}}", "HIGH", proto=True,
             rec=f"max({L(tk)},5m)<{{$TEMP_CRIT}}-3"),
    ]
    env = {"uuid": u("d:env"), "name": "Power supply and temperature discovery",
           "type": "SNMP_AGENT",
           "snmp_oid": f"discovery[{{#ENVUNIT}},{env_oid}.10]",
           "key": "env.discovery", "delay": "1h",
           "description": "Блоки питания и температура по RADLAN rlPhdUnitEnvParamTable.",
           "item_prototypes": env_items, "trigger_prototypes": env_triggers}

    macros = [
        {"macro": "{$ICMP_LOSS_WARN}", "value": "20", "description": "Порог потерь ICMP, %"},
        {"macro": "{$ICMP_RESPONSE_TIME_WARN}", "value": "0.15",
         "description": "Порог времени ответа, с"},
        {"macro": "{$TEMP_WARN}", "value": "60", "description": "Warning по температуре, °C"},
        {"macro": "{$TEMP_CRIT}", "value": "75", "description": "High по температуре, °C"},
        {"macro": "{$NET.IF.IFNAME.MATCHES}", "value": ".*",
         "description": "Включать порты по имени (regex)"},
        {"macro": "{$NET.IF.IFNAME.NOT_MATCHES}", "value": "^(Null|vlan|loopback|tunnel).*",
         "description": "Исключать порты по имени (regex)"},
    ]

    tpl = {"uuid": u("template"), "template": TPL, "name": TPL,
           "description": "Мониторинг Eltex MES2408C по SNMP + ICMP: ping, порты, SFP, "
                          "блоки питания, температура. Хосту нужен SNMP-интерфейс.",
           "groups": [{"name": "Templates/Network devices"}],
           "items": items, "discovery_rules": [ports, sfp, env],
           "macros": macros, "valuemaps": valuemaps,
           "tags": [tag("vendor", "Eltex"), tag("model", "MES2408C")]}
    export = {"zabbix_export": {"version": version}}
    gkey = "template_groups" if v7 else "groups"
    export["zabbix_export"][gkey] = [{"uuid": u("group"), "name": "Templates/Network devices"}]
    export["zabbix_export"]["templates"] = [tpl]
    export["zabbix_export"]["triggers"] = triggers
    return export


def main():
    for ver in ("6.0", "7.4"):
        out = ROOT / f"zabbix_{ver}" / "template_eltex_mes2408c_snmp.yaml"
        out.parent.mkdir(exist_ok=True)
        out.write_text(yaml.safe_dump(build(ver), allow_unicode=True, sort_keys=False, width=200),
                       encoding="utf-8")
        print("written", out)


if __name__ == "__main__":
    main()
