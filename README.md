## Скрипт для конвертации объектов SEAF TA в объекты DrawIO 

 - seaf2drawio.py  - скрипт для конвертации yaml объектов метамодели SEAF в объекты DrawIO для автоматизации процесса 
                     формирования диаграммы технической архитектуры ( схема Р41 )
 - drawio2seaf.py - скрипт для извлечения метаданных из объектов Draw IO ( схема Р41 ) и трансформации их в метамодель SEAF (v. 1.30 и выше)

### Для начала работы необходимо 

 1. Наличие Python версии 3.9 и выше
 2. Установить следующие пакеты : 
     ###### pip install N2G
     ###### pip install pyaml
     ###### pip install deepmerge
 
### Конфигурация работы скрипта  *****seaf2drawio*.py****
  Конфигурация скрипта осуществляется путем изменения переменных в файле config.yaml
  
| Переменная           | Назначение                                                                                    |
|----------------------|-----------------------------------------------------------------------------------------------|
| ***data_yaml_file*** | Файл описания объектов SEAF <br/>(default: .data/example/test_seaf_ta_P41_v0.9.yaml)          |
| ***drawio_pattern*** | Шаблон Draw IO  файла используемый для постраения диаграммы.<br/>(default: .data/base.drawio) | 
| ***output_file***    | Файл Draw IO диаграммы сформированной скриптом.<br/>(default: .result/Sample_graph.drawio)    |

###### * Если переменные в файле не заполнены, то по умолчанию используются default значения.
###### * Еслм вместо входного шаблона Draw IO (.data/base.drawio) использовать файл с ранее сформированной скриптом диаграммы Р41,то скрипт не изменит ранее сделанную разметку объектов, а только обноовит данные существующих объектов и дополнит новыми объектами из yaml файла.

#### Переменные конфигурации скрипта можно установить в командной строке в следующем виде:

###### usage: seaf2drawio.py [-h] [-s SRC] [-d DST] [-p PATTERN]

###### Параметры командной строки.

###### options:
######  -h, --help            show this help message and exit
######  -s SRC, --src SRC     файл данных SEAF
######  -d DST, --dst DST     путь и имя файла вывода результатов
######  -p PATTERN, --pattern PATTERN шаблон drawio

###### Прм исполнениии скрипта в операционной системе Windows рекомендуется использовать ключ *****python -X utf8*****  
###### при запуске скрипта из командной строки, либо переменную окружения *****set PYTHONUTF8=1*****

#### Переменные командной строки имеют приоритет перед переменными файла конфигурации.

### Порядок описания объекто SEAF для корректной работы скрипта

###### Описание объектов необходимо осуществлять в следующей последовательности, сначало создается родительский (parent) объект, затем дочерние (child) ссылающийся на родителя
    -*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-
    |- Регион                                   - seaf.ta.services.dc_region
    |  |- Зона доступности                      - seaf.ta.services.dc_az
    |  |  |- Офис/ЦОД                           - seaf.ta.services.office / seaf.ta.services.dc
    |  |  |  |- Зоны безопасности               - seaf.ta.services.network_segment (type : см. модель SEAF)
    |  |  |  |  |- Сети                         - seaf.ta.services.network (type: 'LAN')
    |  |  |  |  |- Провыйдеры услуг связи (ISP) - seaf.ta.services.network (type: 'WAN')
    |  |  |  |  |- Сетевые устройства           - seaf.ta.components.network (type : см. модель SEAF)
    |  |  |  |  |- Сервисы КБ                   - seaf.ta.services.kb (type : см. модель SEAF)
    |  |  |  |  |- Сервисы ТА                   - seaf.ta.services.compute_service/seaf.ta.services.cluster/etc (type : см. модель SEAF)

######  * Типы зон безопасности и сетевых устройст описываются в модели SEAF, описание объектов можно посмотреть в файле примере (.data/example/test_seaf_ta_P41_v0.5.yaml)

###### * Связывание объектов осуществляется через атрибут ***network_connection*** объекта описания сетевого устройства ***seaf.ta.components.network***

##### * Внимание ! На диаграмме "Main Schema" объекты ISP  перекрывают друг друга, необходимо это учитывать

### Конфигурация работы скрипта  *****drawio2seaf.py*****

Конфигурация скрипта осуществляется путем изменения переменных в файле config.yaml
  
| Переменная          | Назначение                                                                                                                  |
|---------------------|-----------------------------------------------------------------------------------------------------------------------------|
| ***drawio_file***   | Файл файл содержащий диаграмму Р41 ранее сформированную скриптом seaf2drawio.py <br/>(default: .result/Sample_graph.drawio) |
| ***schema_file***   | Файл содержит схему объектов SEAF <br/>(default: .data/seaf_schema.yaml)                                                    | 
| ***output_file***   | Файл yaml содержащий объекты в формате SEAF <br/>(default: .result/seaf.yaml)                                               |

#### Переменные конфигурации скрипта можно установить в командной строке в следующем виде:

###### usage: drawio2seaf.py [-h] [-s SRC] [-d DST] [-p PATTERN]

### Возможные сценарии использования скриптов

##### 1. Создание диаграммы DrawIO (Р41) из yaml файла SEAF (seaf2drawio.py)
##### 2. Дополнение объектов, изменение данных ранее созданной диаграммы (Р41) данными из yaml файла SEAF (seaf2drawio.py)
######   при этом ранее сделанная разметка, позиционирование объектов DrawIO не меняется, обновляются данные и добавляются новые объекты 
##### 3. Редактирование ранее созданной с помощью скрипта (seaf2drawio.py) диаграммы, добавление новых объектов с последующей трансформацией данных с помощью скрипта (drawio2seaf.py) в yaml формат SEAF
##### 4. Создание диаграммы с чистого листа используя шаблоны объектов DrawIO из библиотеки (Избранное_Р41.xml) последующей трансформацией данных в yaml формат SEAF
