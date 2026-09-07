from django.contrib import admin

from catalog.models import Category, Product, ProductImage, Review, Sale, ShopSettings, Specification, Tag


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('title', 'parent')
    list_filter = ('parent',)
    search_fields = ('title',)


@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    list_display = ('name',)
    search_fields = ('name',)


class ProductImageInline(admin.TabularInline):
    model = ProductImage
    extra = 1


class SpecificationInline(admin.TabularInline):
    model = Specification
    extra = 1


class SaleInline(admin.StackedInline):
    model = Sale
    extra = 0


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ('title', 'category', 'price', 'count', 'rating', 'is_limited', 'is_banner', 'is_deleted')
    list_filter = ('category', 'is_deleted', 'is_limited', 'is_banner', 'free_delivery')
    search_fields = ('title', 'description')
    filter_horizontal = ('tags',)
    readonly_fields = ('rating',)
    inlines = [ProductImageInline, SpecificationInline, SaleInline]
    actions = ['mark_as_deleted', 'restore']

    def get_queryset(self, request):
        # Показываем в админке все товары, включая помеченные удалёнными —
        # иначе их нельзя будет восстановить через действие "restore".
        return Product.all_objects.all()

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


@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ('product', 'author', 'rate', 'date')
    list_filter = ('rate',)
    search_fields = ('author', 'email', 'text')


@admin.register(ShopSettings)
class ShopSettingsAdmin(admin.ModelAdmin):
    list_display = ('standard_delivery_cost', 'free_delivery_threshold', 'express_delivery_cost')

    def has_add_permission(self, request):
        # Настройки — синглтон: запись можно только редактировать.
        return not ShopSettings.objects.exists()

    def has_delete_permission(self, request, obj=None):
        return False
