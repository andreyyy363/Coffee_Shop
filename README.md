# ☕ Coffee Shop E-Commerce Platform

A comprehensive Django-based e-commerce platform for specialty coffee beans with advanced features including recommendations, discounts, inventory forecasting, and order management.

![Django](https://img.shields.io/badge/Django-5.x-darkgreen.svg)
![Python](https://img.shields.io/badge/Python-3.9+-blue.svg)
![Bootstrap](https://img.shields.io/badge/Bootstrap-5.3.2-purple.svg)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-Database-blue.svg)
![License](https://img.shields.io/badge/License-MIT-green.svg)

## ✨ Features

- **Product Management**: Browse and filter coffee products by type, origin, roast level, and weight
- **Advanced Recommendations**: Hybrid recommendation system using Content-Based, Collaborative Filtering, and Popularity-Based algorithms
- **Discount System**: Manager-configurable promo codes, bulk discounts, and customer-specific offers
- **Order Management**: Complete order lifecycle with status tracking, order history, and customer support
- **Shopping Cart**: Session-based cart with product customization (bean type, weight)
- **Review System**: Product reviews and ratings with moderation
- **Analytics**: 
  - Sales forecasting with trend analysis
  - Inventory forecasting with stock predictions
  - Customer behavior analytics
  - Revenue tracking
- **User Accounts**: Registration, profile management, wishlist/favorites, discount tracking
- **Search & Filters**: Full-text search with advanced filtering by multiple criteria
- **Multi-language Support**: Phone input with country-specific formatting (20+ countries)
- **Manager Dashboard**: Comprehensive tools for product, order, discount, and analytics management
- **Admin Panel**: Django admin interface with custom configurations

## 📸 Screenshots

<details>
<summary><strong>Click here to see all screenshots</strong></summary>

### User Interface

| | |
|---|---|
| **Homepage** | ![Homepage](screenshots/homepage.png) |
| **Product Catalog** | ![Product Catalog](screenshots/product_catalog.png) |
| **Product Details** | ![Product Detail](screenshots/product_detail.png) |
| **Product Search** | ![Product Search](screenshots/product_search.png) |
| **Shopping Cart & Checkout** | ![Cart Checkout](screenshots/cart_checkout.png) |

### User Account & Settings

| | |
|---|---|
| **Login** | ![Login](screenshots/login.png) |
| **Registration** | ![Registration](screenshots/registration.png) |
| **Account Settings** | ![Account Settings](screenshots/account_settings.png) |
| **Favorites** | ![Favorites](screenshots/favorite.png) |
| **Contacts** | ![Contacts](screenshots/contacts.png) |

### Manager Dashboard

| | |
|---|---|
| **Manage Products** | ![Manager Products](screenshots/manage_products.png) |
| **Add Product** | ![Add Product](screenshots/add_product.png) |
| **Manage Countries** | ![Manage Countries](screenshots/manage_countries.png) |
| **Manage Roast Levels** | ![Manage Roast Levels](screenshots/manage_roast_levels.png) |
| **Manage Weights** | ![Manage Weights](screenshots/manage_weights.png) |

### Order Management

| | |
|---|---|
| **Manage Orders** | ![Manage Orders](screenshots/manage_orders.png) |
| **Order Information** | ![Order Info](screenshots/manage_order_info.png) |
| **Contact Messages** | ![Contact Messages](screenshots/manage_contact_message.png) |

### Discounts & Reviews

| | |
|---|---|
| **Manage Promo Codes** | ![Promo Codes](screenshots/manage_promo_codes.png) |
| **Discount Settings** | ![Discount Settings](screenshots/discount_settings.png) |
| **Manage Reviews** | ![Reviews](screenshots/manage_reviews.png) |

### Recommendations & Analytics

| | |
|---|---|
| **Recommendation Settings** | ![Recommendations](screenshots/recommendation_settings.png) |
| **Sales Forecasting 1** | ![Sales Forecast 1](screenshots/sales_forecasting_1.png) |
| **Sales Forecasting 2** | ![Sales Forecast 2](screenshots/sales_forecasting_2.png) |
| **Inventory Forecasting 1** | ![Inventory Forecast 1](screenshots/inventory_forecasting_1.png) |
| **Inventory Forecasting 2** | ![Inventory Forecast 2](screenshots/inventory_forecasting_2.png) |

</details>

## 🛠️ Tech Stack

- **Backend**: Django 5.x
- **Frontend**: Bootstrap 5.3.2 + Bootstrap Icons, Custom JavaScript
- **Database**: PostgreSQL (production) / SQLite (development)
- **ORM**: Django ORM
- **Forms**: Django Crispy Forms with Crispy Bootstrap 5
- **Filtering**: django-filter
- **Image Processing**: Pillow
- **Environment Management**: python-dotenv

## 📁 Project Structure

```
CofeeShop/
├── manage.py                    # Django management script
├── requirements.txt             # Python dependencies
├── .env.example                 # Environment variables template
├── Dockerfile                   # Docker image configuration
├── docker-compose.yml           # Docker Compose setup
├── accounts/                    # User accounts & authentication
│   ├── models.py               # Custom User model with phone & birth date
│   ├── views.py                # Login, registration, profile management
│   ├── forms.py                # Account forms with validation
│   ├── admin.py                # Django admin configuration
│   ├── urls.py
│   ├── migrations/
│   └── templates/accounts/
├── products/                    # Coffee products catalog
│   ├── models.py               # Product, BeanType, Country, Weight models
│   ├── views.py                # Product list, detail, manager views
│   ├── forms.py                # Product CRUD forms
│   ├── filters.py              # Product filtering logic
│   ├── admin.py
│   ├── urls.py
│   ├── management/commands/    # Custom management commands
│   ├── migrations/
│   └── templates/products/
├── orders/                      # Shopping cart & orders
│   ├── models.py               # Cart, CartItem, Order, OrderItem models
│   ├── views.py                # Cart, checkout, order management
│   ├── forms.py                # Checkout & order update forms
│   ├── context_processors.py   # Cart context for templates
│   ├── templatetags/           # Custom template filters
│   ├── admin.py
│   ├── urls.py
│   ├── migrations/
│   └── templates/orders/
├── reviews/                     # Product reviews & ratings
│   ├── models.py               # Review model with moderation
│   ├── views.py                # Review CRUD operations
│   ├── forms.py                # Review form
│   ├── admin.py
│   ├── urls.py
│   ├── migrations/
│   └── templates/reviews/
├── discounts/                   # Promo codes & discount management
│   ├── models.py               # PromoCode, BulkDiscount, CustomerDiscount models
│   ├── services.py             # Discount calculation logic
│   ├── views.py                # Manager discount management
│   ├── admin.py
│   ├── urls.py
│   ├── migrations/
│   └── templates/discounts/
├── recommendations/             # Product recommendation engine
│   ├── models.py               # UserInteraction, RecommendationSettings
│   ├── services.py             # Hybrid recommendation algorithm
│   ├── views.py                # Recommendation management
│   ├── management/commands/    # Background tasks
│   ├── admin.py
│   ├── urls.py
│   ├── migrations/
│   └── templates/recommendations/
├── analytics/                   # Sales & inventory forecasting
│   ├── services.py             # Forecast calculation logic
│   ├── inventory_service.py    # Inventory analytics
│   ├── views.py                # Analytics dashboards
│   ├── urls.py
│   └── templates/analytics/
├── coffeeshop/                  # Project settings
│   ├── settings.py             # Django configuration
│   ├── urls.py                 # Main URL router
│   ├── wsgi.py                 # WSGI application
│   ├── asgi.py                 # ASGI application
│   ├── views.py                # Global views (home, contacts)
│   ├── models.py               # Global models
│   └── migrations/
├── static/                      # Static files (CSS, JS, images)
│   ├── css/
│   ├── js/
│   └── img/
├── staticfiles/                 # Collected static files (production)
├── templates/                   # HTML templates
│   ├── base.html               # Main template with navigation
│   ├── home.html               # Homepage
│   ├── contacts.html           # Contact form page
│   ├── accounts/               # Account templates
│   ├── products/               # Product templates
│   ├── orders/                 # Order templates
│   ├── reviews/                # Review templates
│   ├── discounts/              # Discount templates
│   └── analytics/              # Analytics templates
├── media/                       # User uploaded files (product images)
│   └── products/
└── logs/                        # Application logs (auto-created)
```

## 🚀 Getting Started

### Prerequisites

- Python 3.9+
- PostgreSQL 12+ installed locally
- pip & virtualenv

### Local Installation

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd CofeeShop
   ```

2. **Create virtual environment**
   ```bash
   python -m venv .venv
   
   # Windows
   .venv\Scripts\activate
   
   # Linux/macOS
   source .venv/bin/activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure environment**
   ```bash
   cp .env.example .env
   ```
   Edit `.env` with your PostgreSQL credentials:
   ```
   SECRET_KEY=your-secret-key-here
   DEBUG=True
   POSTGRES_DB=coffeeshop
   POSTGRES_USER=coffeeshop_user
   POSTGRES_PASSWORD=coffeeshop_password
   DB_HOST=127.0.0.1
   DB_PORT=5432
   ```

5. **Create PostgreSQL database**
   ```bash
   # Windows (psql or pgAdmin)
   CREATE DATABASE coffeeshop OWNER coffeeshop_user;
   
   # Linux/macOS (psql)
   psql -U postgres
   CREATE DATABASE coffeeshop OWNER coffeeshop_user;
   ```

6. **Run migrations**
   ```bash
   python manage.py migrate
   ```

7. **Create superuser**
   ```bash
   python manage.py createsuperuser
   ```

8. **Collect static files**
   ```bash
   python manage.py collectstatic --noinput
   ```

9. **Load initial data (optional)**
   ```bash
   python manage.py loaddata initial_data
   ```

10. **Run development server**
    ```bash
    python manage.py runserver
    ```
    
    Visit: http://localhost:8000

### 🐳 Docker Installation (Database Only)

Docker Compose runs **PostgreSQL database and Adminer** (database UI) in containers, while the Django application runs locally on your machine.

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd CofeeShop
   ```

2. **Configure environment**
   ```bash
   cp .env.example .env
   ```
   The `.env` file already contains the correct PostgreSQL configuration.

3. **Start Docker services (PostgreSQL + Adminer)**
   ```bash
   docker-compose up -d
   ```
   
   This will start:
   - **PostgreSQL**: Running on `localhost:5432`
   - **Adminer**: Database UI available at http://localhost:8081

4. **Install Python dependencies**
   ```bash
   python -m venv .venv
   
   # Windows
   .venv\Scripts\activate
   
   # Linux/macOS
   source .venv/bin/activate
   
   pip install -r requirements.txt
   ```

5. **Run migrations**
   ```bash
   python manage.py migrate
   ```

6. **Create superuser**
   ```bash
   python manage.py createsuperuser
   ```

7. **Collect static files**
   ```bash
   python manage.py collectstatic --noinput
   ```

8. **Run Django development server**
   ```bash
   python manage.py runserver
   ```
   
   The application will be available at http://localhost:8000

9. **Access services**
   - **Django App**: http://localhost:8000
   - **Django Admin**: http://localhost:8000/admin
   - **Adminer** (Database UI): http://localhost:8081
     - Server: `db`
     - Username: `coffeeshop_user`
     - Password: `coffeeshop_password`
     - Database: `coffeeshop`

10. **Stop Docker containers**
    ```bash
    docker-compose down
    ```
    
    To also remove the database volume:
    ```bash
    docker-compose down -v
    ```

## 🔧 Configuration

Key settings can be customized in `.env`:

| Setting                | Default              | Description                           |
|------------------------|----------------------|---------------------------------------|
| `SECRET_KEY`           | (required)           | Django secret key for security        |
| `DEBUG`                | True                 | Debug mode for development            |
| `POSTGRES_DB`          | coffeeshop           | PostgreSQL database name              |
| `POSTGRES_USER`        | coffeeshop_user      | PostgreSQL username                   |
| `POSTGRES_PASSWORD`    | coffeeshop_password  | PostgreSQL password                   |
| `DB_HOST`              | 127.0.0.1            | Database host (localhost or container name) |
| `DB_PORT`              | 5432                 | Database port                         |
| `EMAIL_HOST`           | smtp.gmail.com       | Email SMTP server (for production)    |
| `EMAIL_PORT`           | 587                  | Email SMTP port                       |
| `EMAIL_USE_TLS`        | True                 | Use TLS for email                     |
| `EMAIL_HOST_USER`      | (optional)           | Email account username                |
| `EMAIL_HOST_PASSWORD`  | (optional)           | Email account password                |
| `DEFAULT_FROM_EMAIL`   | noreply@kavasoul.com | Default sender email address          |

## ✉️ Email Configuration

The application supports multiple email backends for different environments.

### Development (Console Backend)

For development, emails are printed to the console instead of being sent:

```env
EMAIL_BACKEND=django.core.mail.backends.console.EmailBackend
```

All emails (contact messages, order confirmations, notifications) will appear in your terminal.

### Production (Gmail SMTP)

To send emails via Gmail in production:

1. **Enable 2-Factor Authentication** on your Google Account
2. **Generate App Password**:
   - Go to [Google Account Settings](https://myaccount.google.com/apppasswords)
   - Select "Mail" and "Windows Computer" (or your device)
   - Copy the generated 16-character password

3. **Update `.env` file**:
   ```env
   EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
   EMAIL_HOST=smtp.gmail.com
   EMAIL_PORT=587
   EMAIL_USE_TLS=True
   EMAIL_HOST_USER=your-email@gmail.com
   EMAIL_HOST_PASSWORD=xxxx-xxxx-xxxx-xxxx
   DEFAULT_FROM_EMAIL=KAVASOUL <noreply@kavasoul.com>
   ```

4. **Test email sending**:
   ```bash
   python manage.py shell
   >>> from django.core.mail import send_mail
   >>> send_mail('Test Subject', 'Test Message', 'from@gmail.com', ['to@example.com'])
   1  # Returns 1 if successful
   ```

### Other Email Providers

You can also use other SMTP providers (SendGrid, AWS SES, Mailgun, etc.) by updating `EMAIL_HOST` and `EMAIL_PORT` accordingly.

## 📋 Usage

### For Customers

1. **Browse Products**: Navigate to the product catalog with filtering by type, origin, roast level, and weight
2. **View Details**: Check product details, reviews, and recommendations
3. **Add to Cart**: Customize product options (bean type, weight) and add to shopping cart
4. **Checkout**: Complete purchase with shipping and billing information
5. **Track Orders**: View order history and current status
6. **Leave Reviews**: Rate and review products you've purchased
7. **Manage Account**: Update profile, view discounts, manage favorites
8. **Apply Promos**: Use promo codes for discounts at checkout

### For Managers

1. **Manage Products**: Create, edit, activate/deactivate products
2. **Search Orders**: Search orders by number, customer name, or email
3. **Track Orders**: View order details, update status, manage customer communication
4. **Manage Reviews**: Moderate product reviews and manage ratings
5. **Configure Discounts**: Set up promo codes, bulk discounts, customer-specific offers
6. **Manage Recommendations**: Adjust hybrid algorithm weights (CBF, CF, Popularity)
7. **View Analytics**: 
   - Sales forecasting with trend predictions
   - Inventory forecasting with stock levels
   - Revenue and customer analytics
8. **Manage Customers**: View customer discounts and purchase history
9. **Contact Messages**: Handle customer inquiries

### For Administrators

- Access Django admin panel at `/admin`
- Manage users, permissions, and system settings
- Direct database access through Django ORM


## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- [Django](https://www.djangoproject.com/) - Web framework
- [Bootstrap](https://getbootstrap.com/) - CSS framework
- [Bootstrap Icons](https://icons.getbootstrap.com/) - Icon library
- [django-crispy-forms](https://github.com/django-crispy-forms/django-crispy-forms) - Form rendering
- [django-filter](https://github.com/carltongibson/django-filter) - Advanced filtering
- [Pillow](https://github.com/python-pillow/Pillow) - Image processing
- [PostgreSQL](https://www.postgresql.org/) - Database

