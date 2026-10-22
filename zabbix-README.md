# Шаблоны Zabbix для Eltex MES2408C

- `zabbix-6.0/template_eltex_mes2408c.yaml` — для Zabbix 6.0
- `zabbix-7.4/template_eltex_mes2408c.yaml` — для Zabbix 7.4
- `gen.py` — генератор обоих файлов (`python3 gen.py`)

Импорт: Data collection → Templates → Import. Макрос `{$SNMP_COMMUNITY}`, на хосте нужен SNMP-интерфейс (v2c).

Что мониторится: ICMP ping (+время ответа), порты (up/down, connected/disconnected, скорость/полоса, входящий и исходящий трафик в bps, ошибки), SFP-модули (модель, серийный номер через ENTITY-MIB), блоки питания (основной/резервный, Eltex rlPhdUnitEnvParamTable), температура (пороги `{$TEMP.WARN}`/`{$TEMP.CRIT}`).

ВАЖНО: OID питания/температуры (1.3.6.1.4.1.89.53.15.1.*) и фильтр SFP по ENTITY-MIB не проверены на реальном устройстве — сверьте через `snmpwalk` и при необходимости поправьте.
