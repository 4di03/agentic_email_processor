"""DB Layer interfaces and implementations"""
from abc import ABC, abstractmethod
from typing import Any
import json

class DB(ABC):
    """
    Base key-value DB interface
    """

    @abstractmethod
    def connect(self, **kwargs) -> None:
        pass

    @abstractmethod
    def disconnect(self) -> None:
        """Should be idempotent, works even if not connected"""
        pass

    @abstractmethod
    def put(self, key: str, value: Any) -> None:
        pass

    @abstractmethod
    def get(self, key: str) -> Any:
        pass

    @abstractmethod
    def delete(self, key: str) -> None:
        pass

    
    def __del__(self):
        self.disconnect()

from logger import logged_class
@logged_class
class FileDB(DB):
    """
    Simple log-based append-only file-based key-value DB implementation.
    Stores all values in a single file.
    """

    def __init__(self, filename: str):
        self.filename = filename
        self.store = {}

    def _load_state(self) -> None:
        """ Loads the log from file and reconstructs the in-memory store """
        try:
            with open(self.filename, 'r') as f:
                store_data = f.read()
        except FileNotFoundError:
            store_data = ""

        for event in store_data.splitlines():
            action, key, value = self._parse_log_line(event)
            if action == "PUT":
                self.store[key] = value
            elif action == "DELETE" and key in self.store:
                del self.store[key]


    def connect(self, **kwargs) -> None:
        try:
            with open(self.filename, 'r') as f:
                self.store = json.load(f)
        except FileNotFoundError:
            self.store = {}


    def disconnect(self) -> None:
        with open(self.filename, 'w') as f:
            import json
            json.dump(self.store, f)

    def _escape(self, s: str) -> str:
        """
        we use space and newline as delimiters, so escape them
        """
        return (
            s
            .replace("\\", "\\\\")   # escape backslash FIRST
            .replace(" ", "\\s")     # escape space
            .replace("\n", "\\n")    # escape newline
        )
    def _unescape(self, s: str) -> str:
        return (
            s
            .replace("\\n", "\n")    # unescape newline FIRST
            .replace("\\s", " ")      # unescape space
            .replace("\\\\", "\\")    # unescape backslash
        )

    def put(self, key: str, value: Any) -> None:
        # Append the PUT operation to the log file
        with open(self.filename, 'a') as f:
            f.write(f"PUT {self._escape(key)} {self._escape(value)}\n")

        self.store[key] = value


    def delete(self, key: str) -> None:
        if key in self.store:
            # Append the DELETE operation to the log file
            with open(self.filename, 'a') as f:
                f.write(f"DELETE {self._escape(key)}\n")
            del self.store[key]


    def _parse_log_line(self, line: str) -> tuple[str, str, Any | None]:
        """
        Parses a log line into (action, key, value)
        """
        parts = line.split(" ")
        action = parts[0]
        
        if action == "DELETE":
            if len(parts) != 2:
                raise ValueError(f"Invalid DELETE log line: {line}")

            return action, self._unescape(parts[1]), None
        
        if action == "PUT":
            if len(parts) != 3:
                raise ValueError(f"Invalid PUT log line: {line}")
            return action, self._unescape(parts[1]), self._unescape(parts[2])
        

    def get(self, key: str) -> Any:
        return self.store.get(key)




