import os
import sys
from pathlib import Path

import django


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'kdemo.settings')
django.setup()

from baby.models import VaccineDefinition  # noqa: E402


DATA = [
    {
        'vaccine_key': 'hepb_1',
        'name': '乙肝疫苗',
        'dose_index': 1,
        'dose_total': 3,
        'fee_type': VaccineDefinition.FeeType.FREE,
        'months_offset': 0.0,
        'days_offset': 0,
        'description': '预防乙型病毒性肝炎'
    },
    {
        'vaccine_key': 'bcg_1',
        'name': '卡介苗',
        'dose_index': 1,
        'dose_total': 1,
        'fee_type': VaccineDefinition.FeeType.FREE,
        'months_offset': 0.0,
        'days_offset': 0,
        'description': '预防儿童结核性脑膜炎、粟粒性结核'
    },
    {
        'vaccine_key': 'hepb_2',
        'name': '乙肝疫苗',
        'dose_index': 2,
        'dose_total': 3,
        'fee_type': VaccineDefinition.FeeType.FREE,
        'months_offset': 1.0,
        'days_offset': 0,
        'description': '预防乙型病毒性肝炎'
    },
    {
        'vaccine_key': 'pcv13_1',
        'name': '13价肺炎球菌多糖结合疫苗',
        'dose_index': 1,
        'dose_total': 4,
        'fee_type': VaccineDefinition.FeeType.PAID,
        'months_offset': 1.5,
        'days_offset': 0,
        'price_min': 600,
        'price_max': 800,
        'description': '预防由13种肺炎球菌血清型引起的侵袭性疾病（包括菌血症性肺炎、脑膜炎、败血症和菌血症）'
    },
    {
        'vaccine_key': 'dpt_1',
        'name': '百白破疫苗',
        'dose_index': 1,
        'dose_total': 5,
        'fee_type': VaccineDefinition.FeeType.FREE,
        'months_offset': 2.0,
        'days_offset': 0,
        'description': '预防百日咳、白喉、破伤风'
    },
    {
        'vaccine_key': 'ipv_1',
        'name': '脊灰灭活疫苗',
        'dose_index': 1,
        'dose_total': 2,
        'fee_type': VaccineDefinition.FeeType.FREE,
        'months_offset': 2.0,
        'days_offset': 0,
        'description': '预防由脊髓灰质炎病毒1型、2型和3型导致的脊髓灰质炎（小儿麻痹症）'
    },
    {
        'vaccine_key': 'pentavalent_1',
        'name': '五联疫苗',
        'dose_index': 1,
        'dose_total': 4,
        'fee_type': VaccineDefinition.FeeType.PAID,
        'months_offset': 2.0,
        'days_offset': 0,
        'price_min': 600,
        'price_max': 800,
        'description': '预防白喉、破伤风、百日咳、脊髓灰质炎和b型流感嗜血杆菌感染'
    },
    {
        'vaccine_key': 'ipv_2',
        'name': '脊灰灭活疫苗',
        'dose_index': 2,
        'dose_total': 2,
        'fee_type': VaccineDefinition.FeeType.FREE,
        'months_offset': 3.0,
        'days_offset': 0,
        'description': '预防由脊髓灰质炎病毒1型、2型和3型导致的脊髓灰质炎（小儿麻痹症）'
    },
    {
        'vaccine_key': 'opv_1',
        'name': '脊灰减毒疫苗',
        'dose_index': 1,
        'dose_total': 2,
        'fee_type': VaccineDefinition.FeeType.FREE,
        'months_offset': 4.0,
        'days_offset': 0,
        'description': '预防脊髓灰质炎I型和III型病毒导致的脊髓灰质炎（小儿麻痹症）'
    },
    {
        'vaccine_key': 'dpt_2',
        'name': '百白破疫苗',
        'dose_index': 2,
        'dose_total': 5,
        'fee_type': VaccineDefinition.FeeType.FREE,
        'months_offset': 4.0,
        'days_offset': 0,
        'description': '预防百日咳、白喉、破伤风'
    },
    {
        'vaccine_key': 'dpt_3',
        'name': '百白破疫苗',
        'dose_index': 3,
        'dose_total': 5,
        'fee_type': VaccineDefinition.FeeType.FREE,
        'months_offset': 6.0,
        'days_offset': 0,
        'description': '预防百日咳、白喉、破伤风'
    },
    {
        'vaccine_key': 'hepb_3',
        'name': '乙肝疫苗',
        'dose_index': 3,
        'dose_total': 3,
        'fee_type': VaccineDefinition.FeeType.FREE,
        'months_offset': 6.0,
        'days_offset': 0,
        'description': '预防乙型病毒性肝炎'
    },
    {
        'vaccine_key': 'mening_a_1',
        'name': 'A群流脑多糖疫苗',
        'dose_index': 1,
        'dose_total': 2,
        'fee_type': VaccineDefinition.FeeType.FREE,
        'months_offset': 6.0,
        'days_offset': 0,
        'description': '预防A群脑膜炎球菌引起的流行性脑脊髓膜炎'
    },
    {
        'vaccine_key': 'flu_1',
        'name': '流感疫苗',
        'dose_index': 1,
        'dose_total': 2,
        'fee_type': VaccineDefinition.FeeType.PAID,
        'months_offset': 6.0,
        'days_offset': 0,
        'price_min': 60,
        'price_max': 150,
        'description': '每年秋季接种，预防流行性感冒'
    },
    {
        'vaccine_key': 'ev71_1',
        'name': '手足口病疫苗',
        'dose_index': 1,
        'dose_total': 2,
        'fee_type': VaccineDefinition.FeeType.PAID,
        'months_offset': 7.0,
        'days_offset': 0,
        'price_min': 200,
        'price_max': 200,
        'description': '预防EV71感染所致的手足口病'
    },
    {
        'vaccine_key': 'flu_2',
        'name': '流感疫苗',
        'dose_index': 2,
        'dose_total': 2,
        'fee_type': VaccineDefinition.FeeType.PAID,
        'months_offset': 7.0,
        'days_offset': 0,
        'price_min': 60,
        'price_max': 150,
        'description': '每年秋季接种，预防流行性感冒'
    },
    {
        'vaccine_key': 'je_inactivated_1',
        'name': '乙脑灭活疫苗',
        'dose_index': 1,
        'dose_total': 4,
        'fee_type': VaccineDefinition.FeeType.PAID,
        'months_offset': 8.0,
        'days_offset': 0,
        'price_min': 70,
        'price_max': 100,
        'description': '预防流行性乙型脑炎'
    },
    {
        'vaccine_key': 'mmr_1',
        'name': '麻腮风疫苗',
        'dose_index': 1,
        'dose_total': 2,
        'fee_type': VaccineDefinition.FeeType.FREE,
        'months_offset': 8.0,
        'days_offset': 0,
        'description': '预防麻疹、流行性腮腺炎、风疹等三种急性呼吸道传染病'
    },
    {
        'vaccine_key': 'je_live_1',
        'name': '乙脑减毒活疫苗',
        'dose_index': 1,
        'dose_total': 2,
        'fee_type': VaccineDefinition.FeeType.FREE,
        'months_offset': 8.0,
        'days_offset': 0,
        'description': '预防流行性乙型脑炎'
    },
    {
        'vaccine_key': 'mening_a_2',
        'name': 'A群流脑多糖疫苗',
        'dose_index': 2,
        'dose_total': 2,
        'fee_type': VaccineDefinition.FeeType.FREE,
        'months_offset': 9.0,
        'days_offset': 0,
        'description': '预防A群脑膜炎球菌引起的流行性脑脊髓膜炎'
    },
    {
        'vaccine_key': 'varicella_1',
        'name': '水痘疫苗',
        'dose_index': 1,
        'dose_total': 2,
        'fee_type': VaccineDefinition.FeeType.PAID,
        'months_offset': 12.0,
        'days_offset': 0,
        'price_min': 150,
        'price_max': 150,
        'description': '预防水痘'
    },
    {
        'vaccine_key': 'mmr_2',
        'name': '麻腮风疫苗',
        'dose_index': 2,
        'dose_total': 2,
        'fee_type': VaccineDefinition.FeeType.FREE,
        'months_offset': 18.0,
        'days_offset': 0,
        'description': '预防麻疹、流行性腮腺炎、风疹等三种急性呼吸道传染病'
    },
    {
        'vaccine_key': 'dpt_4',
        'name': '百白破疫苗',
        'dose_index': 4,
        'dose_total': 5,
        'fee_type': VaccineDefinition.FeeType.FREE,
        'months_offset': 18.0,
        'days_offset': 0,
        'description': '预防百日咳、白喉、破伤风'
    },
]


def run():
    for item in DATA:
        VaccineDefinition.objects.update_or_create(
            vaccine_key=item['vaccine_key'],
            defaults={
                'name': item['name'],
                'dose_index': item.get('dose_index', 1),
                'dose_total': item.get('dose_total', 1),
                'fee_type': item.get('fee_type', VaccineDefinition.FeeType.FREE),
                'description': item.get('description'),
                'months_offset': item.get('months_offset', 0.0),
                'days_offset': item.get('days_offset', 0),
                'price_min': item.get('price_min'),
                'price_max': item.get('price_max'),
                'is_active': True
            }
        )


if __name__ == '__main__':
    run()
