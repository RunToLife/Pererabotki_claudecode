# Eltex MES2408C — шаблоны Zabbix

Шаблоны мониторинга коммутатора Eltex MES2408C по SNMP v2c:

- `zabbix_6.0/template_eltex_mes2408c_snmp.yaml` — Zabbix 6.0
- `zabbix_7.4/template_eltex_mes2408c_snmp.yaml` — Zabbix 7.4
- `generate.py` — генератор обоих файлов (`python3 generate.py`)

## Что мониторится
1. **Пинг** — icmpping, потери, время отклика + триггеры.
2. **Порты** (LLD по IF-MIB, только ethernet): up/down (connected/disconnected), admin-статус, полоса (ifHighSpeed), входящий/исходящий трафик (бит/с), ошибки, alias; триггер на падение линка.
3. **SFP-модули** (LLD по ENTITY-MIB): модель, вендор, серийный номер, описание.
4. **Блоки питания** (LLD по RADLAN rlEnvMonSupplyStatusTable, 1.3.6.1.4.1.89.83.1.2): состояние + триггер.
5. **Температура** (rlPhdUnitEnvParamTempSensorValue, 1.3.6.1.4.1.89.53.15.1.10.1): триггеры warning/critical.

Макросы: `{$SNMP_COMMUNITY}`, `{$TEMP_WARN}`, `{$TEMP_CRIT}`, `{$ICMP_LOSS_WARN}`, `{$ICMP_RESPONSE_TIME_WARN}`.

## Важно
Шаблоны не проверялись на реальном устройстве/сервере Zabbix. OIDs блоков питания, температуры и SFP (ENTITY-MIB) нужно проверить через `snmpwalk` на конкретной прошивке и при необходимости поправить в `generate.py`.
Эта папка предназначена для переноса в отдельный репозиторий (создать его автоматически не удалось: нет прав у интеграции).
