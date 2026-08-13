from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file="../.env")

    camera_mode: str = "real"            # "mock" или "real"
    zmq_camera_address: str = "tcp://192.168.30.170:5555"

settings = Settings()