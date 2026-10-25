# Eltex MES2408C — Zabbix templates

Шаблоны мониторинга коммутатора Eltex MES2408C по SNMP:

- `zabbix_6.0/template_eltex_mes2408c_snmp.yaml` — Zabbix 6.0
- `zabbix_7.4/template_eltex_mes2408c_snmp.yaml` — Zabbix 7.4
- `generate.py` — генератор обоих файлов (единый источник, различается только версия экспорта)

## Что мониторится
1. Пинг: `icmpping`, потери, время отклика + триггеры.
2. Порты (LLD): oper-статус up/down (connected/disconnected), скорость порта (ifHighSpeed), входящий/исходящий трафик (ifHCInOctets/ifHCOutOctets, бит/с), триггер на падение линка (только для admin up).
3. SFP-модули (LLD): производитель, тип, серийный номер.
4. Блоки питания: основной и резервный (normal/warning/critical/…), триггеры.
5. Температура + пороговые триггеры (`{$TEMP.WARN}`, `{$TEMP.CRIT}`).

## Использование
Импорт: Data collection → Templates → Import. Добавить на хост SNMP-интерфейс (v2c/v3) и привязать шаблон.

## Важно: проверить вендорские OID
Стандартные OID (IF-MIB) универсальны. OID PSU/температуры (rlPhdUnitEnvParam*, 1.3.6.1.4.1.89.53.15.1) и SFP
(eltPhdTransceiverInfoTable, 1.3.6.1.4.1.35265.1.23.53.1.1.1) вынесены в макросы `{$OID.*}`; они составлены без доступа
к устройству и не проверены на реальном MES2408C. Сверьте через `snmpwalk` и при необходимости поправьте макросы на хосте.
