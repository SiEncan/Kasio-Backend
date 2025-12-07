from rest_framework import serializers
from .models import Category, Product, Transaction, TransactionItem, User

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'first_name', 'last_name', 'username', 'email', 'role', 'phone']

class CreateUserSerializer(serializers.Serializer):
    first_name = serializers.CharField()
    last_name = serializers.CharField()
    username = serializers.CharField()
    email = serializers.EmailField()
    role = serializers.CharField(default="cashier")
    phone = serializers.CharField(required=False, allow_blank=True)
    password = serializers.CharField()

class CategorySerializer(serializers.ModelSerializer):
  class Meta:
        model = Category
        fields = '__all__'

class ProductSerializer(serializers.ModelSerializer):
    category_name = serializers.CharField(source='category.name', read_only=True)
    
    class Meta:
        model = Product
        fields = '__all__'

class TransactionItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = TransactionItem
        fields = ['product', 'product_name', 'quantity', 'price', 'subtotal', 'notes']

class TransactionSerializer(serializers.ModelSerializer):
    items = TransactionItemSerializer(many=True)
    cashier_name = serializers.CharField(source='cashier.username', read_only=True)
    
    class Meta:
        model = Transaction
        fields = '__all__'
        read_only_fields = ['transaction_number', 'cashier']
    
    def create(self, validated_data):
        items_data = validated_data.pop('items')
        cashier = self.context['request'].user
        # transaction = Transaction.objects.create(**validated_data)
        
        transaction_subtotal = 0
        for item_data in items_data:
            product = Product.objects.get(id=item_data['product'].id)
            quantity = item_data.get('quantity', 1)
            price = product.price
            transaction_subtotal += price * quantity

        validated_data['subtotal'] = transaction_subtotal
        validated_data['total'] = transaction_subtotal + validated_data.get('tax', 0) - validated_data.get('discount', 0)
        change = validated_data['paid_amount'] - validated_data['total']
        validated_data['change_amount'] = change if change > 0 else 0

        transaction = Transaction.objects.create(cashier=cashier,**validated_data)

        for item_data in items_data:
            product = Product.objects.get(id=item_data['product'].id)
            quantity = item_data.get('quantity', 1)
            price = product.price
            subtotal = price * quantity

            TransactionItem.objects.create(
                transaction=transaction,
                product=product,
                product_name=product.name,
                quantity=quantity,
                price=price,
                subtotal=subtotal,
                notes=item_data.get('notes', '')
            )

            # Update stock
            product.stock -= quantity
            product.save()
        
        return transaction
    
    def update(self, instance, validated_data):
        items_data = validated_data.pop('items', None)
        
        # Update field biasa
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        
        if items_data is not None:
            # Kembalikan stock item lama
            for item in instance.items.all():
                product = item.product
                product.stock += item.quantity
                product.save()
            instance.items.all().delete()
            
            # Tambahkan item baru & kurangi stock
            transaction_subtotal = 0
            for item_data in items_data:
                product = Product.objects.get(id=item_data['product'].id)
                quantity = item_data.get('quantity', 1)
                subtotal = product.price * quantity
                transaction_subtotal += subtotal

                TransactionItem.objects.create(
                    transaction=instance,
                    product=product,
                    product_name=product.name,
                    quantity=quantity,
                    price=product.price,
                    subtotal=subtotal,
                    notes=item_data.get('notes', '')
                )

                product.stock -= quantity
                product.save()
            
            instance.subtotal = transaction_subtotal
            instance.total = transaction_subtotal + instance.tax - instance.discount
            instance.change_amount = max(0, instance.paid_amount - instance.total)
        
        instance.save()
        return instance