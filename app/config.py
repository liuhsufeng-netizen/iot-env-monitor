import os


class BaseConfig:
    SQLALCHEMY_DATABASE_URI = os.getenv("DATABASE_URL", "sqlite:///monitor.db")
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    TEMPERATURE_THRESHOLD = float(os.getenv("TEMPERATURE_THRESHOLD", "27.0"))
    AC_COMMAND_COOLDOWN_SECONDS = int(os.getenv("AC_COMMAND_COOLDOWN_SECONDS", "300"))
    DEFAULT_AREAS = os.getenv("DEFAULT_AREAS", "Zone_A,Zone_B,Zone_C,Zone_D")


class DevelopmentConfig(BaseConfig):
    DEBUG = True


class ProductionConfig(BaseConfig):
    DEBUG = False


CONFIG_MAP = {
    "development": DevelopmentConfig,
    "production": ProductionConfig,
}
