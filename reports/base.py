import io
from abc import ABC, abstractmethod
import pandas as pd

class ReportGenerator(ABC):

    @abstractmethod
    def build_dataframe(self, **kwargs) -> pd.DataFrame:
        ...

    @abstractmethod
    def to_excel(self, **kwargs) -> io.BytesIO:
        ...
