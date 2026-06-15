"""English display-name and institution-role enrichment helpers."""
from __future__ import annotations

import datetime as dt
from typing import Any


REVIEW_DATE = "2026-06-15"

ROLE_FIELDS = {
    "originator": "originator_en",
    "financial_advisor": "financial_advisor_en",
    "abs_plan_manager": "abs_plan_manager_en",
    "fund_manager": "fund_manager_en",
}

ROLE_LABELS = {
    "originator": "Sponsor / originator",
    "financial_advisor": "Financial advisor",
    "abs_plan_manager": "ABS / special-plan manager",
    "fund_manager": "Fund manager",
}

INSTITUTION_EN = {
    "中国国际金融股份有限公司": "CICC",
    "中国国际金融股份有限公司上海分公司": "CICC Shanghai Branch",
    "中信证券股份有限公司": "CITIC Securities",
    "中信建投证券股份有限公司": "CSC Financial",
    "国泰海通证券股份有限公司": "Guotai Haitong Securities",
    "上海国泰海通证券资产管理有限公司": "Guotai Haitong Securities Asset Management",
    "华泰联合证券有限责任公司": "Huatai United Securities",
    "华泰证券股份有限公司": "Huatai Securities",
    "招商证券股份有限公司": "China Merchants Securities",
    "中航证券有限公司": "AVIC Securities",
    "第一创业证券股份有限公司": "First Capital Securities",
    "平安证券股份有限公司": "Ping An Securities",
    "申万宏源证券有限公司": "Shenwan Hongyuan Securities",
    "国金证券股份有限公司": "Sinolink Securities",
    "东吴证券股份有限公司": "Soochow Securities",
    "浙商证券股份有限公司": "Zheshang Securities",
    "华夏基金管理有限公司": "Huaxia Fund Management",
    "中金基金管理有限公司": "CICC Fund Management",
    "中信建投基金管理有限公司": "CSC Fund Management",
    "华安基金管理有限公司": "Hua An Fund Management",
    "博时基金管理有限公司": "Bosera Asset Management",
    "易方达基金管理有限公司": "E Fund Management",
    "嘉实基金管理有限公司": "Harvest Fund Management",
    "鹏华基金管理有限公司": "Penghua Fund Management",
    "富国基金管理有限公司": "Fullgoal Fund Management",
    "广发基金管理有限公司": "GF Fund Management",
    "银华基金管理股份有限公司": "Yinhua Fund Management",
    "汇添富基金管理股份有限公司": "China Universal Asset Management",
    "南方基金管理股份有限公司": "China Southern Asset Management",
    "中银基金管理有限公司": "BOC Fund Management",
    "招商基金管理有限公司": "China Merchants Fund Management",
    "华泰证券(上海)资产管理有限公司": "Huatai Securities (Shanghai) Asset Management",
    "华泰证券（上海）资产管理有限公司": "Huatai Securities (Shanghai) Asset Management",
    "上海东方证券资产管理有限公司": "Orient Securities Asset Management",
    "中银资产管理有限公司": "BOC Asset Management",
    "南方资本管理有限公司": "China Southern Capital Management",
    "易方达资产管理有限公司": "E Fund Asset Management",
    "汇添富资本管理有限公司": "China Universal Capital Management",
    "北京市昌平保障房建设投资管理有限公司": "Beijing Changping Affordable Housing Investment Management",
    "CAPITALAND MALL ASIA LIMITED": "CapitaLand Mall Asia",
    "PCCLF HOLDING PTE. LTD.": "PCCLF Holding",
}

BRAND_PREFIXES = [
    ("中信建投", "CSC"),
    ("国泰海通", "Guotai Haitong"),
    ("红土创新", "Hongtu Innovation"),
    ("招商基金", "China Merchants Fund"),
    ("华夏基金", "Huaxia Fund"),
    ("东方红", "Orient Securities Asset Management"),
    ("创金合信", "First Seafront"),
    ("汇添富", "China Universal"),
    ("易方达", "E Fund"),
    ("嘉实", "Harvest"),
    ("华夏", "Huaxia"),
    ("中金", "CICC"),
    ("中航", "AVIC"),
    ("华泰", "Huatai"),
    ("平安", "Ping An"),
    ("华安", "Hua An"),
    ("浙商", "Zheshang"),
    ("富国", "Fullgoal"),
    ("东吴", "Soochow"),
    ("博时", "Bosera"),
    ("鹏华", "Penghua"),
    ("国金", "Sinolink"),
    ("银华", "Yinhua"),
    ("招商", "China Merchants"),
    ("广发", "GF"),
    ("工银", "ICBC"),
    ("建信", "CCB Principal"),
    ("南方", "China Southern"),
    ("中银", "BOC"),
]

NAME_TERMS = [
    ("盐田港", "Yan Tian Port"),
    ("首钢绿能", "Shougang Green Energy"),
    ("张江产业园", "Zhangjiang Industrial Park"),
    ("沪杭甬", "Shanghai-Hangzhou-Ningbo"),
    ("首创水务", "Capital Water"),
    ("苏园产业", "Suzhou Industrial Park"),
    ("普洛斯", "GLP"),
    ("蛇口产园", "Shekou Industrial Park"),
    ("广州广河", "Guangzhou Guanghe Expressway"),
    ("中关村", "Zhongguancun"),
    ("越秀高速", "Yuexiu Expressway"),
    ("中国交建", "China Communications Construction"),
    ("中国铁建", "China Railway Construction"),
    ("深圳能源", "Shenzhen Energy"),
    ("深圳安居", "Shenzhen Anju"),
    ("厦门安居", "Xiamen Anju"),
    ("北京保障房", "Beijing Affordable Housing"),
    ("合肥高新", "Hefei High-Tech"),
    ("临港创新产业园", "Lingang Innovation Industrial Park"),
    ("东久新经济", "D&J New Economy"),
    ("江苏交控", "Jiangsu Communications Holding"),
    ("安徽交控", "Anhui Transportation Holding"),
    ("华润有巢", "China Resources Youchao"),
    ("和达高科", "Heda High-Tech"),
    ("京东仓储", "JD Warehousing"),
    ("国家电投新能源", "SPIC New Energy"),
    ("京能国际能源", "Jingneng International Energy"),
    ("湖北科投光谷", "Hubei Science & Technology Investment Optics Valley"),
    ("山东高速", "Shandong Hi-Speed"),
    ("城投宽庭保租房", "Chengtou Kuan Ting Rental Housing"),
    ("金茂消费", "Jinmao Consumer Infrastructure"),
    ("物美消费", "Wumart Consumer Infrastructure"),
    ("华润消费", "China Resources Consumer Infrastructure"),
    ("深高速", "Shenzhen Expressway"),
    ("中国电建清洁能源", "PowerChina Clean Energy"),
    ("印力消费", "InCity Consumer Infrastructure"),
    ("河北高速", "Hebei Expressway"),
    ("特变电工新能源", "TBEA New Energy"),
    ("深国际", "Shenzhen International"),
    ("百联消费", "Bailian Consumer Infrastructure"),
    ("明阳智能新能源", "Mingyang Smart Energy"),
    ("首创奥莱", "Capital Outlets"),
    ("津开产园", "Tianjin Development Industrial Park"),
    ("广开产园", "Guangzhou Development Industrial Park"),
    ("大悦城消费", "Joy City Consumer Infrastructure"),
    ("宝湾物流", "Blogis Logistics"),
    ("蛇口租赁住房", "Shekou Rental Housing"),
    ("高速公路", "Expressway"),
    ("联东科创", "Liando Sci-Tech Innovation"),
    ("南京交通", "Nanjing Transportation"),
    ("绍兴原水水利", "Shaoxing Raw Water"),
    ("南京建邺", "Nanjing Jianye"),
    ("蒙能清洁能源", "Mengneng Clean Energy"),
    ("重庆两江", "Chongqing Liangjiang"),
    ("成都高投产业园", "Chengdu Gaotou Industrial Park"),
    ("宁波交投", "Ningbo Communications Investment"),
    ("外高桥", "Waigaoqiao"),
    ("易商仓储物流", "ESR Warehousing Logistics"),
    ("科创", "Sci-Tech Innovation"),
    ("华威市场", "Huawei Market"),
    ("济南能源供热", "Jinan Energy Heating"),
    ("金隅智造工场", "BBMG Intelligent Manufacturing"),
    ("九州通医药", "Jointown Pharmaceutical"),
    ("上海地产租赁住房", "Shanghai Real Estate Rental Housing"),
    ("顺丰物流", "SF Logistics"),
    ("苏州恒泰租赁住房", "Suzhou Hengtai Rental Housing"),
    ("亦庄产业园", "Yizhuang Industrial Park"),
    ("中国绿发商业", "China Green Development Commercial"),
    ("中外运仓储物流", "Sinotrans Warehousing Logistics"),
    ("华电清洁能源", "Huadian Clean Energy"),
    ("首农", "Shounong"),
    ("润泽科技数据中心", "Range Technology Data Center"),
    ("万国数据中心", "GDS Data Center"),
    ("唯品会奥莱", "Vipshop Outlets"),
    ("凯德消费", "CapitaLand Consumer Infrastructure"),
    ("中海消费", "China Overseas Consumer Infrastructure"),
    ("沈阳国际软件园", "Shenyang International Software Park"),
    ("安博仓储", "AMB Warehousing"),
    ("中核清洁能源", "CNNC Clean Energy"),
    ("隧道股份高速公路", "Tunnel Engineering Expressway"),
    ("北京昌保租赁住房", "Beijing Changbao Rental Housing"),
    ("广西北投高速", "Guangxi Beitou Expressway"),
    ("中核汇能新能源", "CNNC Huineng New Energy"),
    ("唯品会商业", "Vipshop Commercial"),
    ("上海地产商业", "Shanghai Real Estate Commercial"),
    ("砂之船商业", "Sasseur Commercial"),
    ("商业", "Commercial"),
    ("消费", "Consumer Infrastructure"),
    ("物流", "Logistics"),
    ("仓储", "Warehousing"),
    ("新能源", "New Energy"),
    ("清洁能源", "Clean Energy"),
    ("产业园", "Industrial Park"),
    ("租赁住房", "Rental Housing"),
]


def english_institution(value: Any) -> str | None:
    if value in (None, ""):
        return None
    text = str(value).strip()
    if not text:
        return None
    if text in INSTITUTION_EN:
        return INSTITUTION_EN[text]
    if text.isascii():
        return text
    for suffix in ("股份有限公司", "有限责任公司", "有限公司", "管理有限公司", "管理股份有限公司"):
        if text.endswith(suffix):
            text = text[: -len(suffix)]
            break
    return text


def english_reit_name(value: Any) -> str | None:
    if value in (None, ""):
        return None
    text = str(value).replace("REIT", "").strip()
    brand = None
    for cn, en in BRAND_PREFIXES:
        if text.startswith(cn):
            brand = en
            text = text[len(cn) :]
            break
    terms: list[str] = []
    for cn, en in NAME_TERMS:
        if cn in text:
            terms.append(en)
            text = text.replace(cn, "")
    if not terms and text:
        terms.append(text)
    parts = [part for part in [brand, " ".join(dict.fromkeys(terms)).strip()] if part]
    return f"{' '.join(parts)} REIT" if parts else None


def translation_entry(record: dict[str, Any], existing: dict[str, Any] | None = None) -> dict[str, Any]:
    existing = existing or {}
    generated = {
        "name_cn": record.get("name_cn"),
        "name_en": english_reit_name(record.get("name_cn")),
        "originator": record.get("originator"),
        "originator_en": english_institution(record.get("originator")),
        "fund_manager": record.get("fund_manager"),
        "fund_manager_en": english_institution(record.get("fund_manager")),
        "abs_plan_manager": record.get("abs_plan_manager"),
        "abs_plan_manager_en": english_institution(record.get("abs_plan_manager")),
        "financial_advisor": record.get("financial_advisor"),
        "financial_advisor_en": english_institution(record.get("financial_advisor")),
        "translation_source": "rules",
        "translation_confidence": "medium",
        "last_reviewed": REVIEW_DATE,
        "review_notes": "Rule-based draft; review against official English disclosures before production use.",
    }
    merged = dict(generated)
    for key, value in existing.items():
        if value not in (None, ""):
            merged[key] = value
    if not merged.get("name_en"):
        merged["translation_source"] = "missing"
        merged["translation_confidence"] = "low"
    return merged


def build_translation_artifact(
    records: list[dict[str, Any]],
    existing: dict[str, Any] | None = None,
) -> dict[str, Any]:
    existing = existing or {}
    items = {
        record["symbol"]: translation_entry(record, existing.get(record["symbol"]))
        for record in records
    }
    covered = sum(1 for item in items.values() if item.get("name_en"))
    return {
        "build_time": dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat(),
        "schema_v": 1,
        "status": "ok" if covered else "missing",
        "last_reviewed": REVIEW_DATE,
        "review_required": True,
        "translation_prompt": "See README plan notes or user-provided translation prompt for manual review rules.",
        "coverage": {
            "total_records": len(records),
            "records_with_name_en": covered,
            "coverage_pct": round((covered / float(len(records) or 1)) * 100, 1),
        },
        "items": items,
    }


def apply_translations(records: list[dict[str, Any]], translations: dict[str, Any]) -> None:
    items = translations.get("items") or translations
    for record in records:
        entry = items.get(record["symbol"], {})
        for key in (
            "name_en",
            "originator_en",
            "fund_manager_en",
            "abs_plan_manager_en",
            "financial_advisor_en",
            "translation_source",
            "translation_confidence",
        ):
            record[key] = entry.get(key)


def build_institution_roles(records: list[dict[str, Any]]) -> dict[str, Any]:
    items: list[dict[str, Any]] = []
    for record in records:
        for role, en_key in ROLE_FIELDS.items():
            name_cn = record.get(role)
            if not name_cn:
                continue
            items.append(
                {
                    "symbol": record["symbol"],
                    "role": role,
                    "role_label": ROLE_LABELS[role],
                    "name_cn": name_cn,
                    "name_en": record.get(en_key) or english_institution(name_cn),
                    "source_url": None,
                    "source_asof": record.get("source_asof"),
                    "confidence": "medium",
                    "source": "workbook_seed",
                }
            )
    return {
        "build_time": dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat(),
        "schema_v": 1,
        "status": "ok" if items else "missing",
        "source": "workbook_seed",
        "coverage": {
            "total_records": len(records),
            "roles_parsed": len(items),
            "records_with_roles": len({item["symbol"] for item in items}),
            "coverage_pct": round((len({item["symbol"] for item in items}) / float(len(records) or 1)) * 100, 1),
        },
        "items": items,
    }
