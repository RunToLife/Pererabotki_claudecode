#!/usr/bin/env python3
"""Генератор шаблонов Zabbix для Eltex MES2408C (версии 6.0 и 7.4)."""
import uuid, os, sys

NS = uuid.UUID("6f1c2d4e-0000-4000-8000-00000000e17e")
def u(name):
    return uuid.uuid5(NS, name).hex

TPL = "Eltex MES2408C SNMP"
GROUP = "Templates/Network devices"

def item(name, key, oid=None, vtype="FLOAT", units="", delay="1m", ptype="SNMP_AGENT",
         preproc=None, descr="", indent=8, valuemap=None, history=None, tags=None):
    p = " " * indent
    l = [f"{p}- uuid: {u(TPL+key)}", f"{p}  name: '{name}'", f"{p}  type: {ptype}",
         f"{p}  snmp_oid: '{oid}'" if oid else None, f"{p}  key: '{key}'", f"{p}  delay: {delay}"]
    if history: l.append(f"{p}  history: {history}")
    if vtype != "FLOAT": l.append(f"{p}  value_type: {vtype}")
    if vtype == "CHAR" or vtype == "TEXT": l.append(f"{p}  trends: '0'")
    if units: l.append(f"{p}  units: '{units}'")
    if descr: l.append(f"{p}  description: '{descr}'")
    if valuemap: l += [f"{p}  valuemap:", f"{p}    name: '{valuemap}'"]
    if preproc:
        l.append(f"{p}  preprocessing:")
        for t, params in preproc:
            l += [f"{p}    - type: {t}", f"{p}      parameters:"] + [f"{p}        - '{x}'" for x in params]
    if tags:
        l.append(f"{p}  tags:")
        for k, v in tags: l += [f"{p}    - tag: {k}", f"{p}      value: '{v}'"]
    return "\n".join(x for x in l if x)

def trigger(name, expr, prio, indent=8, descr="", rec=None, dep=None):
    p = " " * indent
    l = [f"{p}- uuid: {u(TPL+name)}", f"{p}  expression: '{expr}'"]
    if rec:
        l += [f"{p}  recovery_mode: RECOVERY_EXPRESSION", f"{p}  recovery_expression: '{rec}'"]
    l += [f"{p}  name: '{name}'", f"{p}  priority: {prio}"]
    if descr: l.append(f"{p}  description: '{descr}'")
    return "\n".join(l)

def lld(name, key, oid, filt_macro_val, items, triggers, descr=""):
    # filter: исключаем служебные интерфейсы по регулярному выражению в макросе
    s = [f"    - uuid: {u(TPL+key)}", f"      name: '{name}'", "      type: SNMP_AGENT",
         f"      snmp_oid: '{oid}'", f"      key: '{key}'", "      delay: 1h"]
    if descr: s.append(f"      description: '{descr}'")
    if filt_macro_val:
        m, = filt_macro_val
        s += ["      filter:", "        evaltype: AND_OR", "        conditions:",
              f"          - macro: '{m[0]}'", f"            value: '{m[1]}'", "            formulaid: A"]
    s.append("      item_prototypes:")
    s += items
    if triggers:
        s.append("      trigger_prototypes:")
        s += triggers
    return "\n".join(("    " + x) if x else x for x in "\n".join(s).split("\n"))

def build(ver):
    I = lambda *a, **k: item(*a, indent=10, **k)
    T = lambda *a, **k: trigger(*a, indent=10, **k)
    # ---- Порты (IF-MIB) ----
    port_items = [
        I("Port {#IFNAME}: Operational status", "ifOperStatus[{#SNMPINDEX}]", "1.3.6.1.2.1.2.2.1.8.{#SNMPINDEX}", "UNSIGNED", valuemap="IF-MIB::ifOperStatus", descr="up(1)=connected, down(2)=disconnected", tags=[("component","network"),("interface","{#IFNAME}")]),
        I("Port {#IFNAME}: Admin status", "ifAdminStatus[{#SNMPINDEX}]", "1.3.6.1.2.1.2.2.1.7.{#SNMPINDEX}", "UNSIGNED", valuemap="IF-MIB::ifAdminStatus", tags=[("component","network"),("interface","{#IFNAME}")]),
        I("Port {#IFNAME}: Speed (bandwidth)", "ifHighSpeed[{#SNMPINDEX}]", "1.3.6.1.2.1.31.1.1.1.15.{#SNMPINDEX}", "UNSIGNED", units="bps", preproc=[("MULTIPLIER",["1000000"])], descr="Согласованная скорость порта (ifHighSpeed, Мбит/с -> бит/с)", tags=[("component","network"),("interface","{#IFNAME}")]),
        I("Port {#IFNAME}: Bits received", "net.if.in[{#SNMPINDEX}]", "1.3.6.1.2.1.31.1.1.1.6.{#SNMPINDEX}", "UNSIGNED", units="bps", preproc=[("CHANGE_PER_SECOND",[]),("MULTIPLIER",["8"])], descr="Скорость входящего потока (ifHCInOctets)", tags=[("component","network"),("interface","{#IFNAME}")]),
        I("Port {#IFNAME}: Bits sent", "net.if.out[{#SNMPINDEX}]", "1.3.6.1.2.1.31.1.1.1.10.{#SNMPINDEX}", "UNSIGNED", units="bps", preproc=[("CHANGE_PER_SECOND",[]),("MULTIPLIER",["8"])], descr="Скорость исходящего потока (ifHCOutOctets)", tags=[("component","network"),("interface","{#IFNAME}")]),
        I("Port {#IFNAME}: Inbound errors", "net.if.in.errors[{#SNMPINDEX}]", "1.3.6.1.2.1.2.2.1.14.{#SNMPINDEX}", "UNSIGNED", units="eps", preproc=[("CHANGE_PER_SECOND",[])], tags=[("component","network"),("interface","{#IFNAME}")]),
        I("Port {#IFNAME}: Outbound errors", "net.if.out.errors[{#SNMPINDEX}]", "1.3.6.1.2.1.2.2.1.20.{#SNMPINDEX}", "UNSIGNED", units="eps", preproc=[("CHANGE_PER_SECOND",[])], tags=[("component","network"),("interface","{#IFNAME}")]),
    ]
    port_trig = [T("Port {#IFNAME}: Link down", "last(/%s/ifOperStatus[{#SNMPINDEX}])=2 and last(/%s/ifAdminStatus[{#SNMPINDEX}])=1" % (TPL, TPL), "WARNING", descr="Порт включён администратором, но линка нет (disconnected)", rec="last(/%s/ifOperStatus[{#SNMPINDEX}])<>2" % TPL)]
    ports = lld("Network interfaces discovery", "net.if.discovery", "discovery[{#IFNAME},1.3.6.1.2.1.31.1.1.1.1,{#IFALIAS},1.3.6.1.2.1.31.1.1.1.18]",
                [("{#IFNAME}", "{$IF.NAME.MATCHES}")], port_items, port_trig,
                "Порты коммутатора (IF-MIB). Фильтр по имени задаётся макросом {$IF.NAME.MATCHES}")
    # ---- SFP (ENTITY-MIB: модули в entPhysicalTable) ----
    sfp_items = [
        I("SFP {#SFPNAME}: Description", "sfp.descr[{#SNMPINDEX}]", "1.3.6.1.2.1.47.1.1.1.1.2.{#SNMPINDEX}", "CHAR", delay="1h", tags=[("component","sfp")]),
        I("SFP {#SFPNAME}: Model", "sfp.model[{#SNMPINDEX}]", "1.3.6.1.2.1.47.1.1.1.1.13.{#SNMPINDEX}", "CHAR", delay="1h", tags=[("component","sfp")]),
        I("SFP {#SFPNAME}: Vendor", "sfp.vendor[{#SNMPINDEX}]", "1.3.6.1.2.1.47.1.1.1.1.12.{#SNMPINDEX}", "CHAR", delay="1h", tags=[("component","sfp")]),
        I("SFP {#SFPNAME}: Serial number", "sfp.serial[{#SNMPINDEX}]", "1.3.6.1.2.1.47.1.1.1.1.11.{#SNMPINDEX}", "CHAR", delay="1h", tags=[("component","sfp")]),
    ]
    sfp = lld("SFP modules discovery", "sfp.discovery", "discovery[{#SFPNAME},1.3.6.1.2.1.47.1.1.1.1.7,{#SFPDESCR},1.3.6.1.2.1.47.1.1.1.1.2]",
              [("{#SFPDESCR}", "{$SFP.DESCR.MATCHES}")], sfp_items, [],
              "Обнаружение вставленных SFP-модулей по ENTITY-MIB (entPhysicalTable). Фильтр по описанию: {$SFP.DESCR.MATCHES}")
    # ---- Блоки питания (RADLAN-HWENVIROMENT) ----
    psu_items = [
        I("PSU {#PSUDESCR}: Status", "psu.status[{#SNMPINDEX}]", "1.3.6.1.4.1.89.83.1.2.1.3.{#SNMPINDEX}", "UNSIGNED", valuemap="RADLAN-HWENVIROMENT::RlEnvMonState", descr="1 normal, 2 warning, 3 critical, 4 shutdown, 5 notPresent, 6 notFunctioning", tags=[("component","power-supply")]),
    ]
    psu_trig = [T("PSU {#PSUDESCR}: Failure", "last(/%s/psu.status[{#SNMPINDEX}])=2 or last(/%s/psu.status[{#SNMPINDEX}])=3 or last(/%s/psu.status[{#SNMPINDEX}])=4 or last(/%s/psu.status[{#SNMPINDEX}])=6" % ((TPL,)*4), "HIGH", rec="last(/%s/psu.status[{#SNMPINDEX}])=1 or last(/%s/psu.status[{#SNMPINDEX}])=5" % (TPL, TPL))]
    psu = lld("Power supply discovery", "psu.discovery", "discovery[{#PSUDESCR},1.3.6.1.4.1.89.83.1.2.1.2]", None, psu_items, psu_trig,
              "Блоки питания (rlEnvMonSupplyStatusTable)")
    # ---- Температура ----
    temp_item = item("Temperature", "sensor.temp", "1.3.6.1.4.1.89.53.15.1.10.1", units="°C", indent=8, descr="rlPhdUnitEnvParamTempSensorValue", tags=[("component","temperature")])
    temp_item2 = item("Temperature sensor status", "sensor.temp.status", "1.3.6.1.4.1.89.53.15.1.9.1", "UNSIGNED", indent=8, valuemap="RADLAN-HWENVIROMENT::RlEnvMonState", descr="1 normal, 2 warning, 3 critical, 4 shutdown, 5 notPresent, 6 notFunctioning", tags=[("component","temperature")])
    ping = [
        item("ICMP ping", "icmpping", None, "UNSIGNED", ptype="SIMPLE", indent=8, valuemap="Service state", tags=[("component","network")]),
        item("ICMP loss", "icmppingloss", None, "FLOAT", ptype="SIMPLE", units="%", indent=8, tags=[("component","network")]),
        item("ICMP response time", "icmppingsec", None, "FLOAT", ptype="SIMPLE", units="s", indent=8, tags=[("component","network")]),
    ]
    sysi = [
        item("System description", "system.descr", "1.3.6.1.2.1.1.1.0", "CHAR", delay="1h", indent=8),
        item("System uptime", "system.uptime", "1.3.6.1.2.1.1.3.0", units="uptime", preproc=[("MULTIPLIER",["0.01"])], indent=8),
    ]
    triggers = [
        trigger("Eltex MES2408C: Unavailable by ICMP ping", "max(/%s/icmpping,#3)=0" % TPL, "HIGH", descr="Нет ответа на ping 3 проверки подряд", rec="min(/%s/icmpping,#2)=1" % TPL),
        trigger("Eltex MES2408C: High ICMP ping loss", "min(/%s/icmppingloss,5m)>{$ICMP.LOSS.WARN} and min(/%s/icmppingloss,5m)<100" % (TPL, TPL), "WARNING"),
        trigger("Eltex MES2408C: High temperature", "last(/%s/sensor.temp)>{$TEMP.CRIT}" % TPL, "HIGH", rec="last(/%s/sensor.temp)<{$TEMP.CRIT}-5" % TPL),
        trigger("Eltex MES2408C: Warning temperature", "last(/%s/sensor.temp)>{$TEMP.WARN}" % TPL, "WARNING", rec="last(/%s/sensor.temp)<{$TEMP.WARN}-5" % TPL),
        trigger("Eltex MES2408C: Temperature sensor in abnormal state", "last(/%s/sensor.temp.status)>1 and last(/%s/sensor.temp.status)<>5" % (TPL, TPL), "AVERAGE"),
    ]
    macros = [("{$IF.NAME.MATCHES}", "^(gi|te|fa)", "Имена портов для обнаружения"),
              ("{$SFP.DESCR.MATCHES}", "(?i)sfp|transceiver", "Описания SFP-модулей для обнаружения"),
              ("{$SNMP.TIMEOUT}", "5m", "Таймаут SNMP-доступности"),
              ("{$ICMP.LOSS.WARN}", "20", "Порог потерь ping, %"),
              ("{$TEMP.WARN}", "55", "Температура WARNING, °C"),
              ("{$TEMP.CRIT}", "70", "Температура HIGH, °C")]
    out = [f"zabbix_export:\n  version: '{ver}'"]
    if ver == "6.0": out.append(f"  date: '2026-10-23T00:00:00Z'")
    out += ["  groups:", f"    - uuid: {u('group')}", f"      name: '{GROUP}'",
            "  templates:", f"    - uuid: {u('tpl')}", f"      template: '{TPL}'",
            f"      name: '{TPL}'",
            "      description: 'Мониторинг Eltex MES2408C по SNMP: ping, порты, SFP, блоки питания, температура. Требуется SNMP-интерфейс на хосте.'",
            "      groups:", f"        - name: '{GROUP}'", "      items:"]
    out += ping + sysi + [temp_item, temp_item2]
    out += ["      discovery_rules:", ports, sfp, psu]
    out.append("      triggers:"); out += triggers
    out.append("      macros:")
    for m, v, d in macros: out += [f"        - macro: '{m}'", f"          value: '{v}'", f"          description: '{d}'"]
    out += ["  value_maps:",
            f"    - uuid: {u('vm1')}", "      name: 'IF-MIB::ifOperStatus'", "      mappings:"]
    for v, n in [(1,"up"),(2,"down"),(3,"testing"),(4,"unknown"),(5,"dormant"),(6,"notPresent"),(7,"lowerLayerDown")]:
        out += [f"        - value: '{v}'", f"          newvalue: '{n}'"]
    out += [f"    - uuid: {u('vm2')}", "      name: 'IF-MIB::ifAdminStatus'", "      mappings:"]
    for v, n in [(1,"up"),(2,"down"),(3,"testing")]:
        out += [f"        - value: '{v}'", f"          newvalue: '{n}'"]
    out += [f"    - uuid: {u('vm3')}", "      name: 'RADLAN-HWENVIROMENT::RlEnvMonState'", "      mappings:"]
    for v, n in [(1,"normal"),(2,"warning"),(3,"critical"),(4,"shutdown"),(5,"notPresent"),(6,"notFunctioning")]:
        out += [f"        - value: '{v}'", f"          newvalue: '{n}'"]
    out += [f"    - uuid: {u('vm4')}", "      name: 'Service state'", "      mappings:",
            "        - value: '0'", "          newvalue: Down", "        - value: '1'", "          newvalue: Up"]
    return "\n".join(out) + "\n"

if __name__ == "__main__":
    root = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "templates")
    for ver in ("6.0", "7.4"):
        d = os.path.join(root, f"zabbix-{ver}"); os.makedirs(d, exist_ok=True)
        open(os.path.join(d, "template_eltex_mes2408c_snmp.yaml"), "w", encoding="utf-8").write(build(ver))
