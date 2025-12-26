from app.core.logging import logger


class DomainException(Exception):
    log_level = "warning"

    def __init__(self, message: str | None = None):
        self.message = message or self.__class__.__name__
        self._log()
        super().__init__(self.message)

    def _log(self):
        if self.log_level == "error":
            logger.error(self.message)
        else:
            logger.warning(self.message)
