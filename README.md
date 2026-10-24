# Pererabotki_claudecode
Есть устройство Eltex MES2408C, которое должно мониториться через Zabbix 7.4 и Zabbix 6.0. Необходимо создать дополнительный репозиторий, где будут лежать шаблоны мониторинга этого устройства для каждой из версий ZAbbix
в Мониторинг должне входить :
  1. Пинг
  2. Состояние портов ( полоса пропускания, up/down, connected/disconected, скорость входящего и исходящего потока данных)
  3. Какие SFP модули вставленны
  4. Состояние блоков питания
  5. Состояние темпиратуры

---

## Содержимое / Contents

| Каталог | Версия Zabbix | Шаблон |
|---|---|---|
| `zabbix-6.0/` | 6.0 LTS | `template_eltex_mes2408c_snmp.yaml` |
| `zabbix-7.4/` | 7.4 | `template_eltex_mes2408c_snmp.yaml` |
| `tools/generate.py` | — | генератор обоих шаблонов (`python3 tools/generate.py`) |

Импорт: *Data collection → Templates → Import* (в 6.0: *Configuration → Templates → Import*). Затем привяжите шаблон к хосту с SNMP-интерфейсом (v2c/v3) и при необходимости поправьте макросы.

### Что мониторится
1. **Пинг** — `icmpping`, `icmppingloss`, `icmppingsec` + триггеры; uptime по SNMP.
2. **Порты** (LLD по IF-MIB, только ifType=6): oper/admin статус (up/down, connected/disconnected — триггер «link down» при admin up), согласованная скорость порта (ifHighSpeed, «полоса»), входящий/исходящий трафик в бит/с (ifHCInOctets/ifHCOutOctets), ошибки in/out.
3. **SFP-модули** (LLD по ENTITY-MIB): описание, модель, производитель, серийный номер; модуль появляется в discovery только когда вставлен (фильтр — макрос `{$SFP.DESCR.MATCHES}`).
4. **Блоки питания** — основной и резервный (`rlPhdUnitEnvParamMainPSStatus` / `RedundantPSStatus`, 1.3.6.1.4.1.89.53.15.1.2/.3) + триггеры.
5. **Температура** — `rlPhdUnitEnvParamTempSensorValue` (…15.1.10) и статус датчика (…15.1.9), пороги `{$TEMP_WARN}` / `{$TEMP_CRIT}`.

### Важно
Шаблоны сгенерированы без доступа к реальному устройству. Eltex-специфичные OID (питание, температура, SFP через ENTITY-MIB) нужно проверить `snmpwalk` на вашей прошивке и при необходимости поправить в `tools/generate.py`. Отдельный GitHub-репозиторий не создавался (доступ ограничен этим репозиторием) — каталог можно перенести в новый репозиторий как есть.
