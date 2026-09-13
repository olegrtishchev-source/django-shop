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
    list_display = (
        'id', 'full_name', 'status', 'delivery_type', 'payment_type', 'total_cost', 'created_at', 'is_deleted',
    )
    list_filter = ('status', 'delivery_type', 'payment_type', 'is_deleted')
    search_fields = ('full_name', 'email', 'phone')
    inlines = [OrderItemInline, PaymentInline]
    actions = ['mark_as_deleted', 'restore']

    def get_queryset(self, request):
        return Order.all_objects.all()

    def delete_model(self, request, obj):
        obj.is_deleted = True
        obj.save(update_fields=['is_deleted'])

    def delete_queryset(self, request, queryset):
        queryset.update(is_deleted=True)

    @admin.action(description='Пометить как удалённые')
    def mark_as_deleted(self, request, queryset):
        queryset.update(is_deleted=True)

    @admin.action(description='Восстановить')
    def restore(self, request, queryset):
        queryset.update(is_deleted=False)
