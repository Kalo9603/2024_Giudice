from . import log as l
from .config import Cache as ch, Index as ix
import csv
import os
import sqlite3
import json
from typing import Dict, List, Set, Optional, Tuple, Any, Union
from multiprocessing import Lock

l.run()


""" Classe che gestisce i file CSV. """
class CSVManager:
    
    @staticmethod
    def getHeader(filename):
        
        if filename == ch.CSV.EXPORT:
            return ["IDArtista1", "Artista1", "IDArtista2", "Artista2", "SampleRatio", "JaccardRatio"]
        elif filename == ch.CSV.LASTS:
            return ["PrID", "LastAr", "Analyzed"]
        elif filename == ch.CSV.POPULARITY:
            return ["ID", "Nome", "Ascoltatori", "Ascolti", "Popolarità", "PopolaritàLog"]
        elif filename == ch.CSV.POP_ZINDEX:
            return ["ID", "Nome", "Ascoltatori", "Ascolti", "Popolarità", "PopolaritàLog", "ZIndex"]
    
    @staticmethod
    def init(filename):
        
        fields = CSVManager.getHeader(filename)
            
        os.makedirs(os.path.dirname(filename), exist_ok=True)

        if not os.path.isfile(filename):
            with open(filename, 'w', newline='', encoding='utf-8') as file:
                writer = csv.DictWriter(file, fieldnames=fields)
                writer.writeheader()

 
    @staticmethod
    def readRow(filename, callback, **kwargs):
        
        try:
            CSVManager.init(filename)
            with open(filename, mode='r', encoding='utf-8') as file:
                reader = csv.DictReader(file, **kwargs)

                for row in reader:
                    callback(row)

        except FileNotFoundError:
            l.logging.error(f"Il file '{filename}' non è stato trovato.")
        except Exception as e:
            l.logging.error(f"Errore durante la lettura del file '{filename}': {str(e)}")

     
    @staticmethod
    def writeRow(filename, row, fieldnames):
        
        try:
            CSVManager.init(filename)
            header = False
            try:
                with open(filename, 'r', encoding='utf-8') as f:
                    if not f.readline():
                        header = True
            except FileNotFoundError:
                header = True

            with open(filename, 'a', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                if header:
                    writer.writeheader()
                writer.writerow(row)
                f.flush()

        except Exception as e:
            l.logging.error(f"Errore durante la scrittura nel file {filename}: {str(e)}")
    

    @staticmethod
    def find(filename, fields, data):

        found = []
        
        if len(fields) != len(data):
                raise ValueError("Il numero di campi e valori deve essere lo stesso")

        with open(filename, mode='r', newline='', encoding='utf-8') as file:
            reader = csv.DictReader(file)
            
            for row in reader:
                match = True
                for field, value in zip(fields, data):
                    if row[field] != value:
                        match = False
                        break
                if match:
                    found.append(row)
                    
        return found if found else None
    

    @staticmethod
    def get(filename, ar1, ar2):
        
        if filename == ch.CSV.EXPORT:
            fields = ["ID1", "ID2"]
            data = [ar1, ar2]
            
            result = CSVManager.find(filename, fields, data)
            
            if len(result) == 1:
                return {
                    "sample": float(result[0]["sRatio"]),
                    "jaccard": float(result[0]["jRatio"])
                }
            return None
    

    @staticmethod
    def length(filename):
        try:
            size = 0
            with open(filename, mode='r', newline='', encoding='utf-8') as file:
                reader = csv.DictReader(file)
                for row in reader:
                    size += 1
                return size
        
        except FileNotFoundError:
            return False
        except Exception as e:
            l.logging.error(f"Errore durante la verifica nel file '{filename}': {str(e)}")
            return False


    @staticmethod
    def exists(filename, ar1: int, ar2: int):
        
        if filename == ch.CSV.EXPORT:
            try:
                CSVManager.init(filename)
                
                f1, f2 = "IDArtista1", "IDArtista2"
                
                with open(filename, mode='r', newline='', encoding='utf-8') as file:
                    reader = csv.DictReader(file)
                    for row in reader:
                        if (row[f1] == str(ar1) and row[f2] == str(ar2)) or \
                        (row[f1] == str(ar2) and row[f2] == str(ar1)):
                            return True
                    return False
            
            except FileNotFoundError:
                return False
            except Exception as e:
                l.logging.error(f"Errore durante la verifica nel file '{filename}': {str(e)}")
                return False


    @staticmethod
    def cut(filename, sValue = None, jValue = None):
        
        if filename == ch.CSV.EXPORT:
            try:
                CSVManager.init(filename)
                
                with open(filename, mode='r', newline='', encoding='utf-8') as file:
                    reader = csv.DictReader(file)
                    rows = list(reader)
                    
                sample = sValue if sValue is not None else ix.Threshold.SAMPLE
                jaccard = jValue if jValue is not None else ix.Threshold.JACCARD
                
                fRows = [
                    row for row in rows 
                    if float(row["SampleRatio"]) >= sample and float(row["JaccardRatio"]) >= jaccard
                ]

                with open(filename, mode='w', newline='', encoding='utf-8') as file:
                    writer = csv.DictWriter(file, fieldnames=reader.fieldnames)
                    writer.writeheader()
                    writer.writerows(fRows)

            except Exception as e:
                l.logging.error(f"Errore durante il filtraggio delle righe in '{filename}': {str(e)}")
    

    @staticmethod
    def removeDuplicates(filename):
        
        if filename == ch.CSV.EXPORT:
            try:
                CSVManager.init(filename)
                seen = set()
                rows = []
                
                with open(filename, mode='r', newline='', encoding='utf-8') as file:
                    reader = csv.DictReader(file)
                    fieldnames = reader.fieldnames
                    
                    for row in reader:
                        pair = tuple(sorted((row["IDArtista1"], row["IDArtista2"])))
                        if pair not in seen:
                            seen.add(pair)
                            rows.append(row)
                
                with open(filename, mode='w', newline='', encoding='utf-8') as file:
                    writer = csv.DictWriter(file, fieldnames=fieldnames)
                    writer.writeheader()
                    writer.writerows(rows)
                
            except Exception as e:
                l.logging.error(f"Errore durante la rimozione dei duplicati in '{filename}': {str(e)}")  
    

    @staticmethod
    def removeColumn(filename, col: str):
        
        try:
            CSVManager.init(filename)
            
            with open(filename, mode='r', newline='', encoding='utf-8') as file:
                reader = csv.DictReader(file)
                if col not in reader.fieldnames:
                    return False
                
                newFields = [field for field in reader.fieldnames if field != col]
                rows = [ {key: row[key] for key in newFields} for row in reader ]

            with open(filename, mode='w', newline='', encoding='utf-8') as file:
                writer = csv.DictWriter(file, fieldnames=newFields)
                writer.writeheader()
                writer.writerows(rows)
            
            return True

        except Exception as e:
            l.logging.error(f"Errore durante la rimozione della colonna '{col}' dal file '{filename}': {str(e)}")
        return False
    

    @staticmethod
    def loadColumn(filename, name):
        
        try:
            CSVManager.init(filename)
            
            values = []
            with open(filename, mode='r', encoding='utf-8') as file:
                reader = csv.DictReader(file)
                for row in reader:
                    if name in row:
                        values.append(row[name])
            return values
        except Exception as e:
            l.logging.error(f"Errore durante il caricamento della colonna '{name}' da '{filename}': {str(e)}")
            return []
    

    @staticmethod
    def sort(filename, cols):
        try:
            CSVManager.init(filename)

            with open(filename, mode='r', newline='', encoding='utf-8') as file:
                reader = csv.DictReader(file)
                rows = list(reader)

            keys = list(cols.keys())
            orders = [cols[col] for col in keys]
            rows.sort(key=lambda row: tuple(row[col] for col in keys), reverse=not all(orders))

            with open(f"{filename}_sorted.csv", mode='w', newline='', encoding='utf-8') as file:
                writer = csv.DictWriter(file, fieldnames=reader.fieldnames)
                writer.writeheader()
                writer.writerows(rows)

            print(f"File ordinato salvato in: {filename}_sorted.csv")
        except Exception as e:
            print(f"Errore durante l'ordinamento del CSV: {e}")
            

    @staticmethod
    def update(filename, kField: str, kValue: Any, data: dict):
        
        fields = CSVManager.getHeader(filename)
        CSVManager.init(filename)
            
        with open(filename, "r", newline="", encoding="utf-8") as f:
                rows = list(csv.DictReader(f))
                fieldnames = rows[0].keys() if rows else fields

        found = False
        for row in rows:
            if row.get(kField) == str(kValue):
                row.update({k: str(v) for k, v in data.items()})
                found = True
                break

        if not found:
            nRow = {field: "" for field in fieldnames}
            nRow[kField] = str(kValue)
            nRow.update({k: str(v) for k, v in data.items()})
            rows.append(nRow)

        with open(filename, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)
            
    def getLastID(file):
        try:
            with open(file, "r", encoding="utf-8") as f:
                lines = f.readlines()
                if len(lines) <= 1:
                    return None
                last_line = lines[-1].strip().split(",")
                return last_line[0]
        except Exception as e:
            l.logging.error(f"Errore nella lettura dell'ultima riga: {str(e)}")
            return None


""" Classe che gestisce le tabelle di cache. """     
class CacheManager:
    
    def __init__(self, path: str, name: str, fields: Dict[str, str], primaryKeys: List[str], indexes: Optional[List[str]] = None):
        
            self.path = path
            self.name = name
            self.fields = fields
            self.primaryKeys = primaryKeys
            self.indexes = indexes
            
            self.buffer = [] 
            self.batchSize = 1000
            
            for key in primaryKeys:
                if key not in fields:
                    raise ValueError(f"La chiave primaria '{key}' non è presente nei campi definiti.")
            
            self._initialize()

    def _initialize(self):
        
        with sqlite3.connect(self.path) as conn:
            
            cursor = conn.cursor()
            cursor.execute("PRAGMA synchronous = OFF;")
            cursor.execute("PRAGMA journal_mode = WAL;")
            
            fields = ", ".join([f"{name} {type}" for name, type in self.fields.items()])
            prKeys = ", ".join(self.primaryKeys)
            
            cursor.execute(
                f"""
                CREATE TABLE IF NOT EXISTS {self.name} (
                    {fields},
                    PRIMARY KEY ({prKeys})
                )
                """
            )
            conn.commit()
            
            if self.indexes:
                self.index(f"{'_'.join(self.indexes)}_ix", self.indexes)
                
            cursor.execute(f"CREATE INDEX IF NOT EXISTS idx_{self.name} ON {self.name} ({prKeys})")
            conn.commit()
    
    def write(self, **values: Any) -> bool:
        
        self.buffer.append(tuple(values.values()))
        if len(self.buffer) >= self.batchSize:
            self._flush()
        return True
    
    def _flush(self):
        
        if not self.buffer:
            return

        keys = ", ".join(self.fields.keys())
        placeholders = ", ".join(["?" for _ in self.fields])

        with sqlite3.connect(self.path) as conn:
            cursor = conn.cursor()
            cursor.executemany(
                f"""
                INSERT OR IGNORE INTO {self.name} ({keys})
                VALUES ({placeholders})
                """,
                self.buffer
            )
            conn.commit()
        self.buffer = []

    def verify(self, condition: str, params: Tuple[Any, ...]) -> bool:
        
        with sqlite3.connect(self.path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                f"""
                SELECT 1 FROM {self.name} WHERE {condition}
                """,
                params
            )
            return cursor.fetchone() is not None
    
    def get(self, fields: List[str], condition: str, params: Tuple[Any, ...], asSet=False) -> Optional[Union[Tuple[Any, ...], Set[Any]]]:
        
        fieldsList = ", ".join(fields)

        with sqlite3.connect(self.path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                f"""
                SELECT {fieldsList} FROM {self.name} WHERE {condition}
                """,
                params
            )
            result = cursor.fetchone()
            if result:
                if asSet:
                    try:
                        ls = json.loads(result[0])
                        return set(ls)
                    except json.JSONDecodeError as e:
                        print(f"Errore di decodifica del JSON: {e}")
                        return set()
                else:
                    return result
                
    def count(self, condition: Optional[str] = None, params: Tuple[Any, ...] = ()) -> int:
        
        query = f"SELECT COUNT(*) FROM {self.name}"
        if condition:
            query += f" WHERE {condition}"

        with sqlite3.connect(self.path) as conn:
            cursor = conn.cursor()
            cursor.execute(query, params)
            return cursor.fetchone()[0]
        
    def delete(self, condition: str, params: Tuple[Any, ...], all: bool = False) -> bool:
        
        query = f"DELETE FROM {self.name}"
        
        if not all:
            query += f" WHERE {condition}"

        try:
            lock = Lock()
            with lock:
                with sqlite3.connect(self.path) as conn:
                    cursor = conn.cursor()
                    cursor.execute(query, params)
                    conn.commit()
                    return cursor.rowcount > 0
                
        except sqlite3.Error as e:
            print(f"Database error: {e}")
            return False

    def drop(self) -> bool:

        try:
            with sqlite3.connect(self.path) as conn:
                cursor = conn.cursor()
                cursor.execute(f"DROP TABLE IF EXISTS {self.name}")
                conn.commit()
                return True
        except sqlite3.Error as e:
            print(f"Database error: {e}")
            return False

    def index(self, name: str, fields: List[str], unique: bool = False):
        
        inType = "UNIQUE" if unique else ""
        fieldsStr = ", ".join(fields)

        with sqlite3.connect(self.path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                f"CREATE {inType} INDEX IF NOT EXISTS {name} ON {self.name} ({fieldsStr})"
            )
            conn.commit()