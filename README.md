# Eltex MES2408C — шаблоны Zabbix

Шаблоны мониторинга коммутатора **Eltex MES2408C** (SNMP + ICMP) для Zabbix **6.0 LTS** и **7.4**.

| Версия Zabbix | Файл |
|---|---|
| 6.0 | `zabbix_6.0/template_eltex_mes2408c_snmp.yaml` |
| 7.4 | `zabbix_7.4/template_eltex_mes2408c_snmp.yaml` |

## Что мониторится
1. **Ping** — `icmpping`, время ответа, потери; триггеры недоступности.
2. **Порты** (LLD по ifType=6) — up/down (connected/disconnected), admin status, скорость порта (ifHighSpeed), входящий/исходящий трафик в бит/с (ifHCInOctets/ifHCOutOctets), ошибки; триггер «Link down» (admin up, oper down).
3. **SFP-модули** (LLD) — тип, производитель, part number, серийный номер.
4. **Блоки питания** — основной и резервный (1 normal … 6 notFunctioning), триггеры.
5. **Температура** — значение и триггеры по `{$TEMP_WARN}` (60) / `{$TEMP_CRIT}` (75).

## Использование
1. Импортируйте файл нужной версии: *Data collection → Templates → Import*.
2. Создайте хост с **SNMP-интерфейсом** (v2c/v3) и привяжите шаблон `Eltex MES2408C SNMP`.
3. Макросы шаблона: `{$ICMP_LOSS_WARN}`, `{$ICMP_RESPONSE_TIME_WARN}`, `{$TEMP_WARN}`, `{$TEMP_CRIT}`, `{$NET.IF.IFNAME.MATCHES}`, `{$NET.IF.IFNAME.NOT_MATCHES}`.

## ⚠ Требует проверки на реальном устройстве
Шаблоны собраны по документации/MIB, без доступа к железу и к Zabbix для тестового импорта.
Стандартные OID (IF-MIB, SNMPv2-MIB) надёжны. Фирменные OID нужно сверить `snmpwalk`-ом на вашей прошивке и при необходимости поправить в `tools/generate.py`:

- Питание и температура (RADLAN `rlPhdUnitEnvParamTable`): `snmpwalk -v2c -c <community> <ip> 1.3.6.1.4.1.89.53.15.1`
- SFP (Eltex PHD MIB): `snmpwalk -v2c -c <community> <ip> 1.3.6.1.4.1.35265.1.23.53`

## Генерация
Файлы создаются `python3 tools/generate.py` (нужен PyYAML); правьте генератор, а не YAML.
