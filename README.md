##  Proektti Iske Tusiriw (Instrukciya)

### Kompuyterinizde Docker ornatilgan boliwi kerek

**Repozitoriyani juklep aliw:**
```bash
git clone https://github.com/Musabek03/Market_API.git
cd Market_API 

```
### env.example fayli tiykarinda .env faylin jaratiw kerek.
```
SECRET_KEY=Super-secret-key
DEBUG=True
ALLOWED_HOSTS=*

Database sazlamalari

POSTGRES_DB=dukan_db
POSTGRES_USER=dukan_user
POSTGRES_PASSWORD=dukan_password
DB_HOST=db
DB_PORT=5432
```
### Dockerdi iske tusiriw
```docker-compose up --build```

### Migraciyalardi qollaw ham admin jaratiw
```
docker-compose exec web python manage.py migrate

docker-compose exec web python manage.py createsuperuser
```
## API Endpointler (Swagger)

### Server iske tuskennen keyin, API hujjetlerin tomendegi siltemeler arqali koriwiniz mumkin:

Schema faylin juklep aliw(Postman ushin):  http://127.0.0.1/api/schema/

Swagger UI (Interaktiv): http://127.0.0.1/api/schema/swagger-ui/

Redoc: http://127.0.0.1/api/schema/redoc/


#### Tiykargi Endpointler Dizimi:

Metod	URL	Tusindirme

POST    /api/auth/telegram  dizimnen otiw ham login qiliw

GET    /api/products/	Barliq onimlerdi koriw (Filter, Search bar)

GET    /api/categories/ Categoriyalar dizimin koriw

GET    /api/products/{id}/	Aniq bir onim haqqinda magliwmat

POST    /api/cart/add/	Sebetke onim qosiw

GET    /api/cart/my_cart/	Oz sebetinizdi koriw(Total_price ham cart-items idlari)

GET    /cart-items/ Cart-itemslerdi koriw

POST    /api/orders/checkout/	Buyirtpa beriw (Order jaratiw)

GET	   /api/orders/	Buyirtpalar tariyxin koriw

POST    /api/orders/{id}/pay/ Order statusin "tolendi"ge ozgertiw

GET    /api/reviews/  Qaldirilgan pikirlerdi koriw

POST	/api/reviews/	Satip alingan onimge pikir qaldiriw

GET    /api/profile/  User ozi haqqinda magliwmatlardi koriwi

PATCH    /api/profile/  User ozi haqqindagi magliwmatlardi ozgertiwi



#### 👤 Avtor:
#### Maxambetjaliev Musabek

GitHub: [Musabek03](https://github.com/Musabek03)


