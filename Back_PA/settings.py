import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = 'django-insecure-a^c2u@j^8rj9r)q9w23cc77&a6-oyw#u$*a*oine5vovw!9*x('

DEBUG = True

ALLOWED_HOSTS = []

# Application definition
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'dashboard',
    'rest_framework',
    'rest_framework.authtoken',  # Pour l'authentification par token
    'corsheaders',  # Pour permettre les requêtes cross-origin
]

MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware',  # Pour les requêtes cross-origin
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

# Ajouter ces configurations CORS
CORS_ALLOW_ALL_ORIGINS = True  # En développement seulement
# En production, utilisez plutôt:
# CORS_ALLOWED_ORIGINS = [
#     "http://localhost:3000",
#     "https://yourdomain.com",
# ]

# Configuration de REST Framework
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework.authentication.TokenAuthentication',
        'rest_framework.authentication.SessionAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
    ],
}

ROOT_URLCONF = 'Back_PA.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [
            os.path.join(BASE_DIR, 'templates'),
            os.path.join(BASE_DIR, 'dashboard', 'templates'),
        ],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'Back_PA.wsgi.application'

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

LANGUAGE_CODE = 'fr'
TIME_ZONE = 'Europe/Paris'
USE_I18N = True
USE_L10N = True
USE_TZ = True

LANGUAGES = [
    ('fr', 'Français'),
    ('en', 'English'),
    ('es', 'Español'),
    ('de', 'Deutsch'),
]

LOCALE_PATHS = [os.path.join(BASE_DIR, 'locale')]

# Static files
STATIC_URL = '/static/'

# Définir le répertoire pour collecter les fichiers statiques
STATIC_ROOT = os.path.join(BASE_DIR, 'static_collected')

# Spécifier les répertoires de fichiers statiques supplémentaires (dashboard/static)
STATICFILES_DIRS = [
    os.path.join(BASE_DIR, 'dashboard', 'static'),  # Chemin vers les fichiers statiques de dashboard
]

# Media files
MEDIA_URL = '/media/'
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Définir votre modèle utilisateur personnalisé
AUTH_USER_MODEL = 'dashboard.User'

# Login & Redirection
LOGIN_URL = '/admin/login/'  # redirection si non connecté
LOGIN_REDIRECT_URL = '/dashboard/'  # redirection après login
