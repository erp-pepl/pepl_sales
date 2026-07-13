from pepl_sales.patches.v1_0.add_cycle1_custom_fields import (
    execute as create_cycle1_custom_fields,
)


def after_install():
    create_cycle1_custom_fields()
