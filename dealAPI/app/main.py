from .api import router
from .core.logging import setup_logging
from .core.setup import create_application

# Initialize logging first
logger = setup_logging()
logger.info("Starting MealSteals Deal API application")

app = create_application(router=router)
