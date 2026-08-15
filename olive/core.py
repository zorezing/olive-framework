class Olive:
    """Main Olive Framework application."""

    VERSION = "0.1.0"

    def __init__(self):
        self.name = "Olive Framework"

    def status(self):
        return {
            "name": self.name,
            "version": self.VERSION,
            "status": "ready",
        }
