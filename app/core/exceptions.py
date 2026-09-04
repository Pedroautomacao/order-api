from app.core.logging import logger


class DomainException(Exception):
    """Erro de regra de negócio.

    O handler global registrado em ``app.main`` traduz para HTTP usando
    ``status_code``. Sem ele toda subclasse não capturada virava 500.
    """

    log_level = "warning"
    status_code = 400

    def __init__(self, message: str | None = None):
        self.message = message or self.__class__.__name__
        self._log()
        super().__init__(self.message)

    def _log(self):
        if self.log_level == "error":
            logger.error(self.message)
        else:
            logger.warning(self.message)
