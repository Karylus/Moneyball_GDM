import pytest
import os
import sys
from unittest.mock import patch, MagicMock
from dotenv import load_dotenv, find_dotenv

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

ARCHIVO_ENV_PRUEBA = ".env.test"

@pytest.fixture(scope="function")
def crear_archivo_env_prueba():
    contenido_env = """
    QWEN_API_KEY="test_qwen_api_key_123"
    GEMINI_API_KEY="test_gemini_api_key_456"
    OPENAI_API_KEY="test_openai_api_key_789"
    DEFAULT_MODEL_NAME="qwen-turbo"
    """
    with open(ARCHIVO_ENV_PRUEBA, "w") as f:
        f.write(contenido_env)
    yield ARCHIVO_ENV_PRUEBA
    if os.path.exists(ARCHIVO_ENV_PRUEBA):
        os.remove(ARCHIVO_ENV_PRUEBA)

class TestConfiguracionEntorno:
    def test_cargar_claves_api_desde_env(self, crear_archivo_env_prueba):
        cargado = load_dotenv(find_dotenv(ARCHIVO_ENV_PRUEBA, usecwd=True), override=True)
        assert cargado, f"No se pudo cargar el archivo {ARCHIVO_ENV_PRUEBA}"

        qwen_api_key = os.getenv("QWEN_API_KEY")
        gemini_api_key = os.getenv("GEMINI_API_KEY")
        openai_api_key = os.getenv("OPENAI_API_KEY")
        modelo_por_defecto = os.getenv("DEFAULT_MODEL_NAME")

        assert qwen_api_key == "test_qwen_api_key_123"
        assert gemini_api_key == "test_gemini_api_key_456"
        assert openai_api_key == "test_openai_api_key_789"
        assert modelo_por_defecto == "qwen-turbo"

        @patch.dict(os.environ, {
            "QWEN_API_KEY": "test_qwen_api_key_123",
            "DEFAULT_MODEL_NAME": "qwen-turbo"
        })
        def simular_configuracion_agente():
            api_key = os.getenv("QWEN_API_KEY")
            modelo = os.getenv("DEFAULT_MODEL_NAME")
            if not api_key:
                raise ValueError("QWEN_API_KEY no encontrada en el entorno.")
            if not modelo:
                raise ValueError("DEFAULT_MODEL_NAME no encontrado en el entorno.")
            return {"api_key_usada": api_key, "modelo_usado": modelo}

        config = simular_configuracion_agente()
        assert config["api_key_usada"] == "test_qwen_api_key_123"
        assert config["modelo_usado"] == "qwen-turbo"

    def test_archivo_env_inexistente(self):
        if os.path.exists(ARCHIVO_ENV_PRUEBA):
            os.remove(ARCHIVO_ENV_PRUEBA)

        cargado = load_dotenv(find_dotenv(".env.nonexistent", usecwd=True, raise_error_if_not_found=False), override=True)
        assert not cargado, "Se cargó un archivo .env inexistente, lo cual no debería ocurrir."

        with patch.dict(os.environ, {}, clear=True):
            qwen_api_key = os.getenv("QWEN_API_KEY_MISSING_TEST")
            modelo_por_defecto = os.getenv("DEFAULT_MODEL_NAME_MISSING_TEST")
            assert qwen_api_key is None
            assert modelo_por_defecto is None

    @patch.dict(os.environ, {"SPECIFIC_MODEL_API_KEY": "specific_key_from_os_env"})
    def test_precedencia_variable_entorno(self, crear_archivo_env_prueba):
        os.environ["TEST_PRECEDENCE_VAR"] = "os_env_value"
        contenido_env = "TEST_PRECEDENCE_VAR=\"dotenv_value\"\n"
        with open(ARCHIVO_ENV_PRUEBA, "w") as f:
            f.write(contenido_env)

        load_dotenv(find_dotenv(ARCHIVO_ENV_PRUEBA, usecwd=True), override=False)
        assert os.getenv("TEST_PRECEDENCE_VAR") == "os_env_value"

        load_dotenv(find_dotenv(ARCHIVO_ENV_PRUEBA, usecwd=True), override=True)
        assert os.getenv("TEST_PRECEDENCE_VAR") == "dotenv_value"

        del os.environ["TEST_PRECEDENCE_VAR"]