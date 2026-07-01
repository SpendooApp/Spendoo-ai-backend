from abc import ABC, abstractmethod
import uuid
from sqlalchemy.orm import Session

class BaseTool(ABC):
    @property
    @abstractmethod
    def schema(self) -> dict:
        """
        Returns the tool definition schema expected by the LLM (JSON format).
        Must include 'type', 'function', 'name', 'description', and 'parameters'.
        """
        pass
        
    @abstractmethod
    def execute(self, db: Session, user_id: uuid.UUID, **kwargs) -> str:
        """
        Executes the tool's underlying service logic.
        
        :param db: The active database session.
        :param user_id: The UUID of the authenticated user.
        :param kwargs: The arguments extracted by the LLM (e.g. start_date, granularity).
        :return: A string representation of the result (often JSON dumped from Pydantic).
        """
        pass
