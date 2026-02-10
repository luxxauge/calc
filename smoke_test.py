from __future__ import annotations
from sqlalchemy import inspect
from elektrocalc.settings import DB_URL
from elektrocalc.db.session import make_engine

def main():
    eng = make_engine(DB_URL, echo=False)
    insp = inspect(eng)
    tables = set(insp.get_table_names())
    required = {
    'core_config_version','core_article','core_position_template','core_template_material_line','core_variant_default','core_rule_param','core_text_block',
    'item','item_price','import_batch',
    'lv_document','lv_position','lv_position_match',
    'calc_estimate','calc_estimate_line','calc_extra_line',
    'labor_task','labor_rule',
    'variant_profile','variant_rule',
    'rate_card','rate_card_line',
    'param_rule',
    'prj_project','prj_project_inputs','prj_variant_policy',
    'prj_plan','prj_plan_asset','prj_plan_room','prj_plan_point','prj_plan_route',
    'prj_calc_run','prj_calc_run_position','prj_calc_run_qty','prj_calc_run_material','prj_compliance_finding',
}
    missing = required - tables
    if missing:
        raise SystemExit(f"Missing tables: {sorted(missing)}")
    print("OK: required tables exist:", sorted(required))

if __name__ == "__main__":
    main()
