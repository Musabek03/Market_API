from django.db import models
from django.contrib.auth.models import AbstractUser

class CustomUser(AbstractUser):
    CHOICES = [("admin","Admin"), ("client","Client")] 

    role = models.CharField(max_length=15, choices=CHOICES,default="client", verbose_name="role")
    phone_number = models.IntegerField(unique=True, verbose_name="Telfon nomeri")
    Address = models.CharField(max_length=100, blank=True,null=True, verbose_name="User Adresi")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    groups = models.ManyToManyField(
        "auth.Group",
        related_name="customuser_set",
        blank=True,
        verbose_name="groups",
    )

    user_permissions = models.ManyToManyField(
        "auth.Permission",
        related_name="customuser_set",
        blank=True,
        verbose_name="user permissions",
    )

    def __str__(self):
        return self.username

class Category(models.Model):
    name = models.CharField(max_length=50,verbose_name="Kategoriya ati")
    slug = models.SlugField(unique=True,verbose_name="URL slugi")
    parent = models.ForeignKey('self', on_delete=models.CASCADE, null=True,blank=True, related_name='child',verbose_name="Ata Kategoriya")

    def __str__(self):
        return self.name


class Product(models.Model):
    category = models.ForeignKey(Category,on_delete=models.CASCADE, related_name='products', verbose_name="Kategoriya")
    name = models.CharField(max_length=60, verbose_name="Produkt ati")
    slug = models.URLField(unique=True)
    description = models.TextField(blank=True, verbose_name="Toliq magliwmat")
    price = models.DecimalField(max_digits=12, decimal_places=2, verbose_name="Produkt bahasi")
    discount_price = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Shegirmeli baha")
    image = models.ImageField(upload_to='products/', blank=True,null=True,verbose_name="Produkt suwreti")
    stock = models.IntegerField(default=0,verbose_name="Produkt sani")
    is_active = models.BooleanField(default=True, verbose_name="Satiwda barma")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name


class Cart(models.Model):
    user = models.OneToOneField(CustomUser,on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user.username} sebeti"
    
    @property
    def total_price(self):
        car_items = self.items.all()
        total = 0
        for item in car_items:
            total += item.get.total.price
        return total


class CartItem(models.Model):
    cart = models.ForeignKey(Cart, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product,on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(default=1)

    def __str__(self):
        return f"{self.product.name} li {self.quantity} dana product bar"
    
    def get_total_price(self):
        return self.product.price*self.quantity
    

class Order(models.Model):

    CHOICES = [("kutilmekte", "Kutilmekte"), ("tolendi", "Tolendi"), ("jiberildi", "Jiberildi"),("biykar_etildi","Biykar_etildi")]

    user = models.ForeignKey(CustomUser,on_delete=models.CASCADE, related_name='orders')
    total_price = models.DecimalField(max_digits=12, decimal_places=2)
    status = models.CharField(max_length=60, choices=CHOICES, default='kutilmekte')
    address = models.TextField(max_length=400, verbose_name="Jetkerip beriw adresi")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user.username} din {self.id} buytirtpasi"

class OrderItem(models.Model):
    order = models.ForeignKey(Order, related_name='orderitems',on_delete=models.CASCADE)
    product = models.ForeignKey(Product, on_delete=models.SET_NULL, null=True)
    quantity = models.PositiveIntegerField(default=1)
    price = models.DecimalField(max_digits=12, decimal_places=2, verbose_name="Satilgan bahasi")

    def __str__(self):
        return f"{self.order.id}"
    




    
