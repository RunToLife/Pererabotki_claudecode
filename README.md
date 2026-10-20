# Pererabotki_claudecode
Есть устройство Eltex MES2408C, которое должно мониториться через Zabbix 7.4 и Zabbix 6.0. Необходимо создать дополнительный репозиторий, где будут лежать шаблоны мониторинга этого устройства для каждой из версий ZAbbix
в Мониторинг должне входить :
  1. Пинг
  2. Состояние портов ( полоса пропускания, up/down, connected/disconected, скорость входящего и исходящего потока данных)
  3. Какие SFP модули вставленны
  4. Состояние блоков питания
  5. Состояние темпиратуры


## Шаблоны

- `zabbix_6.0/template_eltex_mes2408c_snmp.yaml` — для Zabbix 6.0
- `zabbix_7.4/template_eltex_mes2408c_snmp.yaml` — для Zabbix 7.4
- `gen.py` — генератор обоих файлов (`python3 gen.py`)

Состав: ICMP ping; порты (up/down, connected/disconnected, скорость, входящий/исходящий трафик; LLD по ethernet-портам); SFP (модель, производитель, серийный номер через ENTITY-MIB); блоки питания (Radlan rlEnvMonSupplyStatus); температура (Radlan rlPhdUnitEnvParam). Макросы: `{$TEMP_WARN}`, `{$TEMP_CRIT}`. SNMP-OID для SFP/PSU/температуры нужно проверить на реальном устройстве (snmpwalk) и при необходимости поправить в `gen.py`.
