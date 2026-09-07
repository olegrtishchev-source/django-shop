from django.contrib import admin

from orders.models import Order, OrderItem, Payment


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0


class PaymentInline(admin.StackedInline):
    model = Payment
    extra = 0


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ('id', 'full_name', 'status', 'delivery_type', 'payment_type', 'total_cost', 'created_at')
    list_filter = ('status', 'delivery_type', 'payment_type')
    search_fields = ('full_name', 'email', 'phone')
    inlines = [OrderItemInline, PaymentInline]
