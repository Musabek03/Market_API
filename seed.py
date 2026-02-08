import os
import django
import random
from faker import Faker
from django.utils.text import slugify

# 1. DJANGO ORTALIǴIN OYATIW
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'CONFIG.settings') 
django.setup()

from core.models import Category, Product, CustomUser

fake = Faker()

def run_seed():
    print("--- PROCESS BASLANDI ---")
    
    # --------------------------
    # 1. KATEGORIYALAR
    # --------------------------
    print("1. Kategoriyalar jaratılıp atır...")
    main_cats = ["Elektronika", "Kiyimler", "Úy buyımları", "Kitaplar"]
    sub_cats = {
        "Elektronika": ["Smartfonlar", "Noutbuklar", "Televizorlar", "Aksessuarlar"],
        "Kiyimler": ["Erler kiyimi", "Hayallar kiyimi", "Ayaq kiyimler"],
        "Úy buyımları": ["Mebel", "Aswıl úy", "Dekor"],
        "Kitaplar": ["Kórkem ádebiyat", "Biznes", "IT sabaqlıqları"]
    }

    created_cats = []

    for main in main_cats:
        parent, _ = Category.objects.get_or_create(
            name=main, 
            defaults={'slug': slugify(main)}
        )
        
        for sub in sub_cats.get(main, []):
            slug = slugify(sub) + "-" + str(random.randint(1, 1000))
            child, _ = Category.objects.get_or_create(
                name=sub,
                parent=parent,
                defaults={'slug': slug}
            )
            created_cats.append(child)
    
    print("✅ Kategoriyalar tayın.")

    # --------------------------
    # 2. ÓNIMLER (PRODUCTS)
    # --------------------------
    print("2. Ónimler jaratılıp atır...")
    
    if Product.objects.count() < 50:
        for _ in range(50):
            name = fake.sentence(nb_words=3).replace(".", "")
            category = random.choice(created_cats)
            price = random.randint(10000, 5000000)
            
            discount = None
            if random.choice([True, False, False]): 
                discount = price * 0.8 

            Product.objects.create(
                category=category,
                name=name,
                slug=slugify(name) + "-" + str(random.randint(1, 100000)),
                description=fake.text(),
                price=price,
                discount_price=discount,
                stock=random.randint(5, 100),
                image=None 
            )
        print("✅ 50 dana jańa ónim qosıldı.")
    else:
        print("ℹ️ Ónimler jetkilikli, qosılmadı.")

    # --------------------------
    # 3. USERLER (CUSTOM USER)
    # --------------------------
    print("3. Userler jaratılıp atır...")
    
    users_to_create = 5
    created_count = 0
    
    while created_count < users_to_create:
        try:
            # Unikal telefon nomer jaratiw
            operator = random.choice(["90", "91", "93", "94", "99", "88", "33"])
            number = f"{random.randint(1000000, 9999999)}"
            phone = f"+998{operator}{number}"

            if CustomUser.objects.filter(phone_number=phone).exists():
                continue 

            user = CustomUser.objects.create_user(
                username=phone,
                phone_number=phone,
                password="123", 
                first_name=fake.first_name(),
                last_name=fake.last_name(),
                Address=fake.address()
                # role="client"  <--- BUL JERDI OSHIRDIK, endi modelde joq
            )
            print(f"   -> User jaratıldı: {phone} (Password: 123)")
            created_count += 1

        except Exception as e:
            print(f"❌ Qátelik boldı: {e}")
            # Eger baza (migraciya) qáte bolsa, sonsızda toqtaydı
            break 

    print("✅ Awmetli! Barlıq maǵlıwmatlar toltırıldı.")

if __name__ == '__main__':
    run_seed()