"""Service layer package for Dress 2 Decor."""

from app.services.order_service import (
    get_order_by_number,
    get_orders_by_customer_email,
    get_orders_by_status,
    get_recent_orders,
    update_order_status,
    get_order_stats,
)
from app.services.vendor_service import (
    get_vendor_by_id,
    get_vendor_by_email,
    get_vendor_products,
    get_vendor_orders,
    get_vendor_commission_summary,
    get_all_vendors,
    get_vendor_stats,
)
from app.services.meeting_service import (
    get_available_slots,
    schedule_meeting,
    get_meetings_by_date,
    get_upcoming_meetings,
    cancel_meeting,
    get_meeting_stats,
)
from app.services.product_service import (
    get_product_by_id,
    search_products,
    get_products_by_category,
    get_all_products,
    get_product_stats,
)
from app.services.analytics_service import (
    get_dashboard_stats,
    get_revenue_by_month,
    get_top_products,
    get_top_vendors,
)
from app.services.activity_service import (
    log_activity,
    get_recent_activities,
    get_activities_by_agent,
)
