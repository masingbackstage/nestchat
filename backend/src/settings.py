import os
from datetime import timedelta
from pathlib import Path

import environ
from django.core.exceptions import ImproperlyConfigured

BASE_DIR = Path(__file__).resolve().parent.parent

env = environ.Env()

ENV = env("ENV", default="development")
DEBUG = ENV == "development"


def env_list(name, default=None):
    default = [] if default is None else default
    return [value for value in env.list(name, default=default) if value]


SECRET_KEY = env("DJANGO_SECRET_KEY", default=None)
if not SECRET_KEY:
    if DEBUG:
        SECRET_KEY = "unsafe-secret-key-for-nestchat"
    else:
        raise ImproperlyConfigured("DJANGO_SECRET_KEY must be set when ENV is production.")

ALLOWED_HOSTS = env_list(
    "DJANGO_ALLOWED_HOSTS",
    default=["localhost", "127.0.0.1", "0.0.0.0", "testserver"] if DEBUG else [],
)
if not ALLOWED_HOSTS and not DEBUG:
    raise ImproperlyConfigured("DJANGO_ALLOWED_HOSTS must be set when ENV is production.")

INSTALLED_APPS = [
    "daphne",
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.sites",
    "rest_framework",
    "rest_framework_simplejwt",
    "rest_framework_simplejwt.token_blacklist",
    "dj_rest_auth",
    "dj_rest_auth.registration",
    "allauth",
    "allauth.account",
    "allauth.socialaccount",
    "django_filters",
    "corsheaders",
    "drf_spectacular",
    "django_celery_beat",
    "src.apps.user",
    "src.apps.profile",
    "src.apps.server",
    "src.apps.chat",
    "src.apps.dm",
    "src.apps.friends",
    "src.apps.gateway",
]
if DEBUG:
    INSTALLED_APPS.append("debug_toolbar")

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "allauth.account.middleware.AccountMiddleware",
]
if DEBUG:
    MIDDLEWARE.insert(4, "debug_toolbar.middleware.DebugToolbarMiddleware")

ROOT_URLCONF = "src.urls"
WSGI_APPLICATION = "src.wsgi.application"
ASGI_APPLICATION = "src.asgi.application"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

AUTH_USER_MODEL = "user.CustomUser"
SITE_ID = 1

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [os.path.join(BASE_DIR.parent, "templates")],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

DATABASES = {
    "default": env.db(
        "DATABASE_URL", default="postgres://nestchat_user:supersecretpassword@db:5432/nestchat_db"
    )
}

REDIS_URL = env("REDIS_URL", default="redis://redis:6379/0")

CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.redis.RedisCache",
        "LOCATION": env("CACHE_URL", default="redis://redis:6379/1"),
    }
}

CHANNEL_LAYERS = {
    "default": {
        "BACKEND": "channels_redis.core.RedisChannelLayer",
        "CONFIG": {
            "hosts": [REDIS_URL],
        },
    },
}

CELERY_BROKER_URL = env("CELERY_BROKER_URL", default="amqp://guest:guest@rabbitmq:5672//")
CELERY_ACCEPT_CONTENT = ["json"]
CELERY_TASK_SERIALIZER = "json"

STATIC_URL = "/static/"
STATIC_ROOT = "/backend/staticfiles"

MEDIA_ROOT = "/backend/media"
CORS_ALLOWED_ORIGINS = env_list(
    "CORS_ALLOWED_ORIGINS",
    default=["http://localhost:5173", "http://127.0.0.1:5173"] if DEBUG else [],
)
CSRF_TRUSTED_ORIGINS = env_list("CSRF_TRUSTED_ORIGINS", default=[])

USE_S3_MEDIA = env.bool("USE_S3_MEDIA", default=False)
AWS_STORAGE_BUCKET_NAME = env("AWS_STORAGE_BUCKET_NAME", default="")
AWS_S3_REGION_NAME = env("AWS_S3_REGION_NAME", default="")
AWS_S3_ENDPOINT_URL = env("AWS_S3_ENDPOINT_URL", default="")
AWS_S3_CUSTOM_DOMAIN = env("AWS_S3_CUSTOM_DOMAIN", default="")
AWS_ACCESS_KEY_ID = env("AWS_ACCESS_KEY_ID", default="")
AWS_SECRET_ACCESS_KEY = env("AWS_SECRET_ACCESS_KEY", default="")
AWS_REQUEST_CHECKSUM_CALCULATION = env("AWS_REQUEST_CHECKSUM_CALCULATION", default="when_required")
AWS_RESPONSE_CHECKSUM_VALIDATION = env("AWS_RESPONSE_CHECKSUM_VALIDATION", default="when_required")
AWS_DEFAULT_ACL = None
AWS_QUERYSTRING_AUTH = False
AWS_S3_FILE_OVERWRITE = False
AWS_S3_SIGNATURE_VERSION = env("AWS_S3_SIGNATURE_VERSION", default="s3v4")
AWS_S3_ADDRESSING_STYLE = env("AWS_S3_ADDRESSING_STYLE", default="path")

if USE_S3_MEDIA:
    missing_storage_vars = [
        name
        for name, value in (
            ("AWS_STORAGE_BUCKET_NAME", AWS_STORAGE_BUCKET_NAME),
            ("AWS_S3_REGION_NAME", AWS_S3_REGION_NAME),
            ("AWS_S3_ENDPOINT_URL", AWS_S3_ENDPOINT_URL),
            ("AWS_ACCESS_KEY_ID", AWS_ACCESS_KEY_ID),
            ("AWS_SECRET_ACCESS_KEY", AWS_SECRET_ACCESS_KEY),
        )
        if not value
    ]
    if missing_storage_vars:
        raise ImproperlyConfigured(
            "Missing S3 media configuration: " + ", ".join(missing_storage_vars)
        )

    # S3-compatible providers like OCI Object Storage can reject the newer
    # boto3 default checksum behavior introduced in 1.36+, so we keep the
    # pre-1.36 request/response behavior unless the environment overrides it.
    os.environ.setdefault("AWS_REQUEST_CHECKSUM_CALCULATION", AWS_REQUEST_CHECKSUM_CALCULATION)
    os.environ.setdefault("AWS_RESPONSE_CHECKSUM_VALIDATION", AWS_RESPONSE_CHECKSUM_VALIDATION)

    STORAGES = {
        "default": {
            "BACKEND": "storages.backends.s3.S3Storage",
            "OPTIONS": {
                "bucket_name": AWS_STORAGE_BUCKET_NAME,
                "region_name": AWS_S3_REGION_NAME,
                "endpoint_url": AWS_S3_ENDPOINT_URL,
                "default_acl": AWS_DEFAULT_ACL,
                "querystring_auth": AWS_QUERYSTRING_AUTH,
                "file_overwrite": AWS_S3_FILE_OVERWRITE,
                "custom_domain": AWS_S3_CUSTOM_DOMAIN or None,
            },
        },
        "staticfiles": {
            "BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage",
        },
    }
    if AWS_S3_CUSTOM_DOMAIN:
        MEDIA_URL = f"https://{AWS_S3_CUSTOM_DOMAIN.rstrip('/')}/"
    else:
        MEDIA_URL = f"{AWS_S3_ENDPOINT_URL.rstrip('/')}/{AWS_STORAGE_BUCKET_NAME.rstrip('/')}/"
else:
    MEDIA_URL = "/media/"

REST_FRAMEWORK = {
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    "DEFAULT_AUTHENTICATION_CLASSES": (
        "rest_framework_simplejwt.authentication.JWTAuthentication",
        "rest_framework.authentication.SessionAuthentication",
    ),
    "DEFAULT_PERMISSION_CLASSES": ("rest_framework.permissions.IsAuthenticated",),
    "DEFAULT_FILTER_BACKENDS": ("django_filters.rest_framework.DjangoFilterBackend",),
    "DEFAULT_RENDERER_CLASSES": (
        "djangorestframework_camel_case.render.CamelCaseJSONRenderer",
        "rest_framework.renderers.JSONRenderer",
    ),
    "DEFAULT_PARSER_CLASSES": (
        "djangorestframework_camel_case.parser.CamelCaseJSONParser",
        "djangorestframework_camel_case.parser.CamelCaseMultiPartParser",
        "djangorestframework_camel_case.parser.CamelCaseFormParser",
    ),
    "DEFAULT_THROTTLE_CLASSES": (
        "rest_framework.throttling.AnonRateThrottle",
        "rest_framework.throttling.UserRateThrottle",
        "rest_framework.throttling.ScopedRateThrottle",
    ),
    "DEFAULT_THROTTLE_RATES": {
        "anon": env("DRF_THROTTLE_ANON", default="120/min"),
        "user": env("DRF_THROTTLE_USER", default="600/min"),
        "dj_rest_auth": env("DRF_THROTTLE_AUTH", default="60/min"),
        "chat_reads": env("DRF_THROTTLE_CHAT_READS", default="120/min"),
        "chat_writes": env("DRF_THROTTLE_CHAT_WRITES", default="120/min"),
        "user_search": env("DRF_THROTTLE_USER_SEARCH", default="60/min"),
    },
}

REST_AUTH = {
    "USE_JWT": True,
    "JWT_AUTH_HTTPONLY": False,
    "USER_DETAILS_SERIALIZER": "src.apps.user.serializers.CustomUserSerializer",
    "LOGIN_SERIALIZER": "dj_rest_auth.serializers.LoginSerializer",
    "REGISTER_SERIALIZER": "src.apps.user.serializers.CustomRegisterSerializer",
    "TOKEN_MODEL": None,
}

REST_SESSION_LOGIN = False

SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=60),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=7),
    "USER_ID_FIELD": "uuid",
    "USER_ID_CLAIM": "user_uuid",
    "ROTATE_REFRESH_TOKENS": True,
    "BLACKLIST_AFTER_ROTATION": True,
}

GATEWAY_RATE_LIMIT_WINDOW_SECONDS = env.int("GATEWAY_RATE_LIMIT_WINDOW_SECONDS", default=60)
GATEWAY_RECEIVE_RATE_LIMIT_PER_MINUTE = env.int(
    "GATEWAY_RECEIVE_RATE_LIMIT_PER_MINUTE", default=240
)
GATEWAY_SEND_MESSAGE_RATE_LIMIT_PER_MINUTE = env.int(
    "GATEWAY_SEND_MESSAGE_RATE_LIMIT_PER_MINUTE", default=60
)


ACCOUNT_LOGIN_METHODS = {"email"}
ACCOUNT_SIGNUP_FIELDS = []
ACCOUNT_UNIQUE_EMAIL = True
ACCOUNT_EMAIL_VERIFICATION = "optional"
EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"
ACCOUNT_USER_MODEL_USERNAME_FIELD = None
ACCOUNT_USERNAME_REQUIRED = False

SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
USE_X_FORWARDED_HOST = True
SECURE_SSL_REDIRECT = env.bool("DJANGO_SECURE_SSL_REDIRECT", default=not DEBUG)
SESSION_COOKIE_SECURE = env.bool("SESSION_COOKIE_SECURE", default=not DEBUG)
CSRF_COOKIE_SECURE = env.bool("CSRF_COOKIE_SECURE", default=not DEBUG)
SECURE_HSTS_SECONDS = env.int("SECURE_HSTS_SECONDS", default=31536000 if not DEBUG else 0)
SECURE_HSTS_INCLUDE_SUBDOMAINS = env.bool("SECURE_HSTS_INCLUDE_SUBDOMAINS", default=not DEBUG)
SECURE_HSTS_PRELOAD = env.bool("SECURE_HSTS_PRELOAD", default=not DEBUG)

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
        "OPTIONS": {"min_length": 10},
    },
    {
        "NAME": "django.contrib.auth.password_validation.CommonPasswordValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.NumericPasswordValidator",
    },
    {
        "NAME": "src.apps.user.validators.PasswordComplexityValidator",
    },
]

LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

LIVEKIT_URL = env("LIVEKIT_URL", default="")
LIVEKIT_PUBLIC_URL = env("LIVEKIT_PUBLIC_URL", default="")
LIVEKIT_API_KEY = env("LIVEKIT_API_KEY", default="")
LIVEKIT_API_SECRET = env("LIVEKIT_API_SECRET", default="")
LIVEKIT_TOKEN_TTL_SECONDS = env.int("LIVEKIT_TOKEN_TTL_SECONDS", default=600)



if ENV == "production":
    missing_livekit = [
        name
        for name, value in (
            ("LIVEKIT_URL", LIVEKIT_URL),
            ("LIVEKIT_API_KEY", LIVEKIT_API_KEY),
            ("LIVEKIT_API_SECRET", LIVEKIT_API_SECRET),
        )
        if not value
    ]
    if missing_livekit:
        raise ImproperlyConfigured("Missing LiveKit configuration: " + ", ".join(missing_livekit))

SPECTACULAR_SETTINGS = {
    "TITLE": "NestChat API",
    "DESCRIPTION": "API dla NestChat",
    "VERSION": "1.0.0",
    "SERVE_INCLUDE_SCHEMA": False,
}
